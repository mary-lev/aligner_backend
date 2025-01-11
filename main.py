# backend/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET
from pathlib import Path
import os
from pydantic import BaseModel

# Import your existing functions
from utils.txt_parser_2 import (
    Comment, process_comments, create_word_index, 
    find_sequence_in_text, find_best_matching_sequence
)
from utils.xml_builder import create_xml

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define response models
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
TEI_DIR = Path("data/tei")  # Directory with TEI files

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
        temp_comments_path = f"temp_{author}_{chapter}.txt"
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
        print(f"Error processing alignment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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

# Optional: Add endpoint to get chapter content
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

@app.post("/api/save-tei")
async def save_tei(request: SaveTEIRequest) -> Dict[str, str]:
    try:
        # Convert aligned comments back to the format expected by create_xml
        comments_list = []
        chapter_id = request.chapter.replace('cap', '')
        source = f"cap{chapter_id}"
        tag=f"c{chapter_id}"
        
       # In save_tei endpoint
        for comment in request.aligned_comments:
            # Split text into reference and comment parts using the ": " separator
            parts = comment.text.split(": ", 1)  # Split only on first occurrence
            if len(parts) == 2:
                ref_text = parts[0]  # This will be the bold reference
                comment_text = parts[1]
            else:
                ref_text = comment.text
                comment_text = comment.comment

            # Create the note string in TEI XML format
            note_str = f'''<note xml:id="{request.metadata.author}_{source}-n{comment.number}" type="comm" target="quarantana/{source}.xml#{tag}_{comment.start}"{' targetEnd="quarantana/' + source + '.xml#' + tag + '_' + str(comment.end) + '"' if comment.start != comment.end else ''}><ref rend="bold">{ref_text}</ref>: {comment_text}</note>'''

            # Create Comment object with the properly formatted XML string
            comment_obj = Comment(
                text=note_str,  # The full XML string
                number=comment.number,
                source=source,
                tag=f"c{chapter_id}",
                author=request.metadata.author,
                start=comment.start,
                end=comment.end,
                status=comment.status
            )
            comments_list.append(comment_obj)
        # Generate the XML file
        xml_filename = create_xml(
            source,
            comments_list, 
            request.metadata.author,
            editor=request.metadata.editor,
            publisher=request.metadata.publisher,
            publisher_place=request.metadata.publisherPlace,
            publisher_year=request.metadata.publisherYear
        )

        with open(xml_filename, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # Clean up
        # os.remove(xml_filename)
        
        return {"content": xml_content}

    except Exception as e:
        print(f"Error generating TEI XML: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))