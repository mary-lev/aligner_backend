# Manzoni Comments Aligner Backend

This is the backend service for the Manzoni Comments Alignment tool. It provides APIs for aligning comments with TEI/XML text and generating TEI/XML output files.

## Frontend Integration

This backend service works in conjunction with the [Manzoni Comments Aligner Frontend](https://github.com/mary-lev/manzoni_comments_aligner). The frontend provides a user-friendly interface for:
- Uploading comment files
- Visualizing alignments
- Manual alignment corrections
- TEI/XML file generation

You can see the tool in action at: [https://manzoni-comments-aligner.vercel.app](https://manzoni-comments-aligner.vercel.app)

## XML Output Format

The tool generates TEI/XML files that follow the [LeggoManzoni project](https://projects.dharc.unibo.it/leggomanzoni) specifications. The output files:
- Include properly formatted XML annotations
- Maintain correct reference linking to the Quarantana edition
- Follow the project's metadata structure
- Are ready for direct integration into the LeggoManzoni digital edition

## Setup

### Prerequisites
- Python 3.8+
- FastAPI
- uvicorn
- lxml

### Installation

1. Clone the repository:
```bash
git clone https://github.com/mary-lev/aligner_backend.git
cd manzoni-comments-aligner-backend
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up the data directory structure:
```
data/
├── tei/        # TEI/XML chapter files
└── output.json # Edition metadata
```

### Running the Server

Development:
```bash
uvicorn main:app --reload --port 8000
```

Production:
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

## API Endpoints

### GET /api/chapters
Lists all available TEI chapters.

### GET /api/chapters/{chapter_id}
Gets the TEI content for a specific chapter.

### POST /api/align
Aligns comments with TEI text.
- Parameters:
  - chapter: Chapter identifier
  - author: Author name
  - comments_file: Text file with comments

### POST /api/save-tei
Generates TEI/XML output with aligned comments.
- Body:
  - chapter: Chapter identifier
  - metadata: Edition metadata
  - aligned_comments: List of aligned comments

## XML Output Format
Example of generated XML structure:
```xml
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <!-- Metadata following LeggoManzoni specifications -->
  </teiHeader>
  <text>
    <body>
      <div xml:id="Russo_intro">
        <note xml:id="Russo_intro-n1" type="comm" 
              target="quarantana/intro.xml#intro_10001" 
              targetEnd="quarantana/intro.xml#intro_10060">
          <ref rend="bold">Reference text</ref>: Comment text
        </note>
        <!-- Additional notes -->
      </div>
    </body>
  </text>
</TEI>
```

## Project Structure

```
├── main.py              # FastAPI application and routes
├── utils/
│   ├── txt_parser_2.py  # Comment parsing and alignment logic
│   └── xml_builder.py   # TEI/XML generation
├── data/
│   ├── tei/            # TEI/XML chapter files
│   └── output.json     # Edition metadata
└── requirements.txt    # Python dependencies
```

## Deployment

The service is deployed on Render.com. Configure the following:

1. Environment Variables:
   - `PYTHON_VERSION`: "3.8" or higher
   - `PORT`: Port for the service

2. Build Command:
```bash
pip install -r requirements.txt
```

3. Start Command:
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

## Data Structure

### Edition Metadata (output.json)
```json
[
  {
    "filename": "Russo",
    "title": "I promessi sposi",
    "author": "Alessandro Manzoni",
    "curator": "Russo, Luigi",
    "date": 1978,
    "city": "Firenze",
    "publisher": "Sansoni",
    "marcatura": [
      {
        "resp": "Codifica",
        "persName": "Name"
      }
    ]
  }
]
```