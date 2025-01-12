# backend/main.py
import json
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET
from pathlib import Path
import os
from pydantic import BaseModel

from utils.txt_parser_2 import (
    Comment, process_comments
)
from utils.xml_builder import create_xml

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://manzoni-comments-aligner.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AlignedComment(BaseModel):
    number: int
    text: str
    comment: str
    start: Optional[int]
    end: Optional[int]
    status: str

class AlignmentResponse(BaseModel):
    aligned: List[AlignedComment]
    error: Optional[str] = None


class TEIMetadata(BaseModel):
    author: str
    editor: str = "Pistelli, Ermenegildo"
    publisher: str = "Sansoni"
    publisherPlace: str = "Firenze"
    publisherYear: str = "1978"


# Configuration
TEI_DIR = Path("data/tei")
TEMP_DIR = "/tmp"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB


def check_data_directories():
    """Verify required data directories exist"""
    if not TEI_DIR.exists():
        raise RuntimeError(f"TEI directory not found: {TEI_DIR}")
    if not os.path.isfile('data/output.json'):
        raise RuntimeError("Edition data file (output.json) not found")

@app.on_event("startup")
async def startup_event():
    """Check data directories on startup"""
    check_data_directories()

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "OK",
        "tei_files": len(list(TEI_DIR.glob("*.xml"))),
        "temp_dir": os.path.exists(TEMP_DIR)
    }

@app.post("/api/align", response_model=AlignmentResponse)
async def align_comments(
    chapter: str,
    author: str,
    comments_file: UploadFile = File(...),
) -> AlignmentResponse:
    print(f"Processing comments for {author} in chapter {chapter}")
    print(f"Comments file: {comments_file.filename}")
    try:
        # Save uploaded comments temporarily
        comments_content = await comments_file.read()
        if len(comments_content) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="File too large (max 10MB)")
        temp_comments_path = os.path.join(TEMP_DIR, f"temp_{author}_{chapter}.txt")
        with open(temp_comments_path, "wb") as f:
            f.write(comments_content)

        # Process the alignment
        chapter_id = chapter.replace('cap', '')
        source = f"cap{chapter_id}"
        comments = process_comments(
            xml_path=str(TEI_DIR / f"{chapter}.xml"),
            comments_path=temp_comments_path,
            source=source,
            tag=f"c{chapter_id}",
            author=author
        )

        # Clean up temporary file
        os.remove(temp_comments_path)

        # Convert comments to response format
        aligned_results = [
            AlignedComment(
                number=comment.number,
                text=comment.line,
                comment=comment.comment,
                start=comment.start,
                end=comment.end,
                status=comment.status
            ) for comment in comments
        ]
        
        print(f"Processed {len(aligned_results)} comments")
        return AlignmentResponse(aligned=aligned_results)

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Chapter file not found: {chapter}.xml")
    except Exception as e:
        if os.path.exists(temp_comments_path):
            os.remove(temp_comments_path)
        raise e
    finally:
        if os.path.exists(temp_comments_path):
            try:
                os.remove(temp_comments_path)
            except:
                pass


@app.get("/api/chapters")
async def list_chapters() -> List[Dict[str, str]]:
    """List available TEI chapters"""
    try:
        chapters = []
        for file in TEI_DIR.glob("*.xml"):
            chapter_id = file.stem  # filename without extension
            chapters.append({
                "id": chapter_id,
                "name": "Introduction" if chapter_id == "intro" else f"Chapter {chapter_id.replace('cap', '')}"
            })
        return sorted(chapters, key=lambda x: (x["id"] != "intro", x["id"]))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chapters/{chapter_id}")
async def get_chapter_content(chapter_id: str) -> Dict[str, str]:
    """Get TEI content for a specific chapter"""
    try:
        file_path = TEI_DIR / f"{chapter_id}.xml"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

class SaveTEIRequest(BaseModel):
    chapter: str
    metadata: TEIMetadata
    aligned_comments: List[AlignedComment]

def load_edition_data() -> Dict:
    with open('data/output.json', 'r', encoding='utf-8') as f:
        editions = json.load(f)
        return {edition['filename']: edition for edition in editions}

@app.post("/api/save-tei")
async def save_tei(request: SaveTEIRequest) -> Dict[str, str]:
    print(f"Saving TEI XML for {request.metadata.author}, {request.metadata.editor} in chapter {request.chapter}")
    try:
        editions = load_edition_data()
        
        edition_data = None
        for ed in editions.values():
            if ed['curator'] == request.metadata.editor:
                edition_data = ed
                break

        print(f"Found edition data: {edition_data['filename'] if edition_data else 'Not found'}")
        
        if not edition_data:
            raise HTTPException(
                status_code=400, 
                detail=f"Edition not found for curator: {request.metadata.editor}"
            )

        chapter_id = request.chapter.replace('cap', '')
        is_intro = 'intro' in request.chapter.lower()
        source = "intro" if is_intro else request.chapter
        tag = "intro" if is_intro else f"c{request.chapter.replace('cap', '')}"
        
        # Get editor's filename for XML IDs
        editor_filename = edition_data['filename']
        
        comments_list = []
        for comment in request.aligned_comments:
            parts = comment.text.split(": ", 1)
            ref_text = parts[0] if len(parts) > 1 else comment.text
            comment_text = parts[1] if len(parts) > 1 else comment.comment

            # Use editor's filename in the XML ID
            note_str = f'''<note xml:id="{editor_filename}_{source}-n{comment.number}" 
                          type="comm" 
                          target="quarantana/{source}.xml#{tag}_{comment.start}"
                          {' targetEnd="quarantana/' + source + '.xml#' + tag + '_' + str(comment.end) + '"' if comment.start != comment.end else ''}>
                          <ref rend="bold">{ref_text}</ref>: {comment_text}
                     </note>'''

            comment_obj = Comment(
                text=note_str,
                number=comment.number,
                source=source,
                tag=tag,
                author=editor_filename,
                start=comment.start,
                end=comment.end,
                status=comment.status
            )
            comments_list.append(comment_obj)

        xml_filename = os.path.join(TEMP_DIR, create_xml(
            source,
            comments_list,
            request.metadata.author,
            edition_data
        ))
        print(f"Generated TEI XML: {xml_filename}")

        # Read content and clean up
        try:
            with open(xml_filename, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            # Clean up temporary file
            os.remove(xml_filename)
            return {"content": xml_content}
        except Exception as e:
            if os.path.exists(xml_filename):
                os.remove(xml_filename)
            raise e
        
    except Exception as e:
        print(f"Error generating TEI XML: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))