from typing import Dict, List, Optional
from pydantic import BaseModel
import json
from lxml import etree
from datetime import datetime

class TEIMetadata(BaseModel):
    author: str  # This is now the annotator's name
    editor: str  # This is the curator from the edition
    publisher: str
    publisherPlace: str
    publisherYear: str

class AlignedComment(BaseModel):
    number: int
    text: str
    comment: str
    start: Optional[int]
    end: Optional[int]
    status: str

class SaveTEIRequest(BaseModel):
    chapter: str
    metadata: TEIMetadata
    aligned_comments: List[AlignedComment]

def load_edition_data() -> Dict:
    with open('data/output.json', 'r', encoding='utf-8') as f:
        editions = json.load(f)
        return {ed['curator']: ed for ed in editions}

def create_xml(source: str, notes: list, annotator_name: str, edition_data: dict) -> str:
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    root = etree.Element("TEI", nsmap=ns)
    header = etree.SubElement(root, "teiHeader")
    text = etree.SubElement(root, "text")
    
    # FileDesc section
    fileDesc = etree.SubElement(header, "fileDesc")
    
    # TitleStmt
    titleStmt = etree.SubElement(fileDesc, "titleStmt")
    title = etree.SubElement(titleStmt, "title")
    title.text = "Commenti da " + edition_data['title']
    
    # Add original author
    author = etree.SubElement(titleStmt, "author")
    author.text = edition_data['author']
    
    # Add curator as editor
    editor = etree.SubElement(titleStmt, "editor")
    editor.text = edition_data['curator']
    
    # Add new respStmt for the annotator
    respStmt = etree.SubElement(titleStmt, "respStmt")
    resp = etree.SubElement(respStmt, "resp")
    resp.text = "Annotazione digitale"
    persName = etree.SubElement(respStmt, "persName")
    persName.set("{http://www.w3.org/XML/1998/namespace}id", annotator_name.replace(" ", "_"))
    persName.text = annotator_name
    
    # Add original markup information if available
    # if 'marcatura' in edition_data:
    #     for mark in edition_data['marcatura']:
    #         markRespStmt = etree.SubElement(titleStmt, "respStmt")
    #         markResp = etree.SubElement(markRespStmt, "resp")
    #         markResp.text = mark['resp']
    #         markPersName = etree.SubElement(markRespStmt, "persName")
    #         markPersName.text = mark['persName']

    # PublicationStmt
    publicationStmt = etree.SubElement(fileDesc, "publicationStmt")
    publisher = etree.SubElement(publicationStmt, "publisher")
    publisher.text = "Leggo Manzoni. Quaranta commenti alla Quarantana"
    pubPlace = etree.SubElement(publicationStmt, "pubPlace")
    pubPlace.text = 'Università di Bologna "Alma mater studiorum"'
    date = etree.SubElement(publicationStmt, "date")
    date.text = str(datetime.now().year)
    
    # Availability
    availability = etree.SubElement(publicationStmt, "availability")
    availability_p = etree.SubElement(availability, "p")
    availability_p.text = "Questa risorsa digitale è liberamente accessibile per uso personale o scientifico. Ogni uso commerciale è vietato."

    # SourceDesc
    sourceDesc = etree.SubElement(fileDesc, "sourceDesc")
    bibl = etree.SubElement(sourceDesc, "bibl")
    
    # Source edition details
    author_element = etree.SubElement(bibl, "author")
    author_element.text = edition_data['author']
    title = etree.SubElement(bibl, "title")
    title.text = edition_data['title']
    editor = etree.SubElement(bibl, "editor")
    editor.text = edition_data['curator']
    pubPlace = etree.SubElement(bibl, "pubPlace")
    pubPlace.text = edition_data['city']
    publisher = etree.SubElement(bibl, "publisher")
    publisher.text = edition_data['publisher']
    date = etree.SubElement(bibl, "date")
    date.text = str(edition_data['date'])

    # RevisionDesc
    revisionDesc = etree.SubElement(header, "revisionDesc")
    listChange = etree.SubElement(revisionDesc, "listChange")
    change = etree.SubElement(listChange, "change")
    change.set("who", annotator_name.replace(" ", "_"))
    change.set("when", datetime.today().strftime('%Y-%m-%d'))
    change.text = "Annotazione digitale"

    # Body with comments
    body = etree.SubElement(text, "body")
    div = etree.SubElement(body, "div")
    div_id = f"{edition_data['filename']}_{source}"
    div.set("{http://www.w3.org/XML/1998/namespace}id", div_id)
    
    # Add comments
    for note in notes:
        try:
            div.append(etree.XML(note.text))
        except Exception as e:
            print(f"Error adding note: {e}")
            print(f"Problematic note: {note.text}")
    
    # Generate output
    xml_string = etree.tostring(root, pretty_print=True, xml_declaration=False, encoding="UTF-8")
    filename = f"{edition_data['filename']}_{source}.xml"
    print(f"Writing TEI XML to: {filename}")
    
    with open(filename, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(b'<?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>\n')
        f.write(b'<?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" type="application/xml" schematypens="http://purl.oclc.org/dsdl/schematron"?>\n')
        f.write(xml_string)
    
    return filename