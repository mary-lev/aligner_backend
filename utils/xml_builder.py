import os
import xml.etree.ElementTree as ET
from datetime import datetime


# Get temp directory
TEMP_DIR = "/tmp"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)


def register_namespaces():
    """Register namespaces to get proper prefixes in output"""
    ET.register_namespace('', "http://www.tei-c.org/ns/1.0")
    ET.register_namespace('xml', "http://www.w3.org/XML/1998/namespace")

def create_xml(source: str, notes: list, annotator_name: str, edition_data: dict) -> str:
    register_namespaces()
    
    # Create root element with namespace
    root = ET.Element("{http://www.tei-c.org/ns/1.0}TEI")
    
    # Create main structure
    header = ET.SubElement(root, "{http://www.tei-c.org/ns/1.0}teiHeader")
    text = ET.SubElement(root, "{http://www.tei-c.org/ns/1.0}text")
    
    # FileDesc section
    fileDesc = ET.SubElement(header, "{http://www.tei-c.org/ns/1.0}fileDesc")
    
    # TitleStmt
    titleStmt = ET.SubElement(fileDesc, "{http://www.tei-c.org/ns/1.0}titleStmt")
    title = ET.SubElement(titleStmt, "{http://www.tei-c.org/ns/1.0}title")
    title.text = "Commenti da " + edition_data['title']
    
    # Add original author
    author = ET.SubElement(titleStmt, "{http://www.tei-c.org/ns/1.0}author")
    author.text = edition_data['author']
    
    # Add curator as editor
    editor = ET.SubElement(titleStmt, "{http://www.tei-c.org/ns/1.0}editor")
    editor.text = edition_data['curator']
    
    # Add new respStmt for the annotator
    respStmt = ET.SubElement(titleStmt, "{http://www.tei-c.org/ns/1.0}respStmt")
    resp = ET.SubElement(respStmt, "{http://www.tei-c.org/ns/1.0}resp")
    resp.text = "Annotazione digitale"
    persName = ET.SubElement(respStmt, "{http://www.tei-c.org/ns/1.0}persName")
    persName.set("{http://www.w3.org/XML/1998/namespace}id", annotator_name.replace(" ", "_"))
    persName.text = annotator_name
    
    # PublicationStmt
    publicationStmt = ET.SubElement(fileDesc, "{http://www.tei-c.org/ns/1.0}publicationStmt")
    publisher = ET.SubElement(publicationStmt, "{http://www.tei-c.org/ns/1.0}publisher")
    publisher.text = "Leggo Manzoni. Quaranta commenti alla Quarantana"
    pubPlace = ET.SubElement(publicationStmt, "{http://www.tei-c.org/ns/1.0}pubPlace")
    pubPlace.text = 'Università di Bologna "Alma mater studiorum"'
    date = ET.SubElement(publicationStmt, "{http://www.tei-c.org/ns/1.0}date")
    date.text = str(datetime.now().year)
    
    # Availability
    availability = ET.SubElement(publicationStmt, "{http://www.tei-c.org/ns/1.0}availability")
    availability_p = ET.SubElement(availability, "{http://www.tei-c.org/ns/1.0}p")
    availability_p.text = "Questa risorsa digitale è liberamente accessibile per uso personale o scientifico. Ogni uso commerciale è vietato."

    # SourceDesc
    sourceDesc = ET.SubElement(fileDesc, "{http://www.tei-c.org/ns/1.0}sourceDesc")
    bibl = ET.SubElement(sourceDesc, "{http://www.tei-c.org/ns/1.0}bibl")
    
    # Source edition details
    author_element = ET.SubElement(bibl, "{http://www.tei-c.org/ns/1.0}author")
    author_element.text = edition_data['author']
    title = ET.SubElement(bibl, "{http://www.tei-c.org/ns/1.0}title")
    title.text = edition_data['title']
    editor = ET.SubElement(bibl, "{http://www.tei-c.org/ns/1.0}editor")
    editor.text = edition_data['curator']
    pubPlace = ET.SubElement(bibl, "{http://www.tei-c.org/ns/1.0}pubPlace")
    pubPlace.text = edition_data['city']
    publisher = ET.SubElement(bibl, "{http://www.tei-c.org/ns/1.0}publisher")
    publisher.text = edition_data['publisher']
    date = ET.SubElement(bibl, "{http://www.tei-c.org/ns/1.0}date")
    date.text = str(edition_data['date'])

    # RevisionDesc
    revisionDesc = ET.SubElement(header, "{http://www.tei-c.org/ns/1.0}revisionDesc")
    listChange = ET.SubElement(revisionDesc, "{http://www.tei-c.org/ns/1.0}listChange")
    change = ET.SubElement(listChange, "{http://www.tei-c.org/ns/1.0}change")
    change.set("who", annotator_name.replace(" ", "_"))
    change.set("when", datetime.today().strftime('%Y-%m-%d'))
    change.text = "Annotazione digitale"

    # Body with comments
    body = ET.SubElement(text, "{http://www.tei-c.org/ns/1.0}body")
    div = ET.SubElement(body, "{http://www.tei-c.org/ns/1.0}div")
    div_id = f"{edition_data['filename']}_{source}"
    div.set("{http://www.w3.org/XML/1998/namespace}id", div_id)
    
    # Add comments
    for note in notes:
        try:
            # Parse the note XML string and append it to div
            note_elem = ET.fromstring(note.text)
            div.append(note_elem)
        except Exception as e:
            print(f"Error adding note: {e}")
            print(f"Problematic note: {note.text}")
    
    # Generate output with proper indentation
    ET.indent(root, space="  ", level=0)
    xml_string = ET.tostring(root, encoding="UTF-8", xml_declaration=False)
    filename = os.path.join(TEMP_DIR, f"{edition_data['filename']}_{source}.xml")
    print(f"Writing TEI XML to: {filename}")
    
    with open(filename, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(b'<?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>\n')
        f.write(b'<?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" type="application/xml" schematypens="http://purl.oclc.org/dsdl/schematron"?>\n')
        f.write(xml_string)
    
    return filename