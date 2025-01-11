import sys
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, List, Tuple
from dataclasses import dataclass
from utils.xml_builder import create_xml

@dataclass
class Comment:
    text: str
    number: int
    source: str
    tag: str
    author: str
    line: str = ""
    comment: str = ""
    start: int = None
    end: int = None
    line_start: str = ""
    line_end: str = ""
    status: str = ""

    def __str__(self):
        end_line = f'targetEnd="quarantana/{self.source}.xml#{self.tag}_{self.end}"' if self.start != self.end else ""
        status = f'status="{self.status}"' if self.status != "OK" else ""
        return f'<note {status} xml:id="{self.author}_{self.source}-n{self.number}" type="comm" target="quarantana/{self.source}.xml#{self.tag}_{self.start}" {end_line}><ref rend="bold">{self.line}</ref>: {self.comment}</note>'

    def parse(self, word_index: Dict[str, List[int]]):
        # Split line and comment
        parts = self.text.split(":", 1)
        if len(parts) > 1:
            self.line, self.comment = parts[0], parts[1]
        else:
            self.line = parts[0]
            self.comment = ""

        # Handle line ranges
        line_parts = self.line.split("... ")
        self.line_start = line_parts[0]
        self.line_end = line_parts[-1] if len(line_parts) > 1 else None

        self.find_origin(word_index)
        self.status = self.check()
        if self.status != "OK":
            print(f"Warning: Issue with comment {self.number}: {self.line} ({self.start}, {self.end}, {self.status})")

    def find_origin(self, word_index: Dict[str, List[int]]):
        """Find word positions using precomputed index"""
        start_ids = find_sequence_in_text(self.line_start, word_index)
        if start_ids:
            self.start = start_ids[0]
            if not self.line_end:
                self.end = start_ids[-1]
        
        if self.line_end:
            end_ids = find_sequence_in_text(self.line_end, word_index)
            if end_ids:
                self.end = end_ids[-1]

    def check(self) -> str:
        """Validate comment alignment"""
        words_count = len(self.line.split())
        if re.match(r"^\d+[-]*\d*[.]\s", self.line):
            words_count -= 1

        if not self.start:
            return "NOT OK"
            
        if self.start and self.end and words_count > 1:
            if self.start > self.end:
                return "NOT OK"
            elif words_count > (self.end - self.start + 1):
                return "NOT OK"
        
        return "OK"

def normalize_chars(word: str) -> List[str]:
    """Generate normalized variants of the word to handle common OCR errors"""
    variants = {
        'è': ['e', 'è', 'é', 'E'],  # Added 'é' as variant
        'é': ['e', 'è', 'é', 'E'],  # Added 'è' as variant
        'e': ['e', 'è', 'é', 'E'],
        'E': ['e', 'è', 'é', 'E'],
        'à': ['a', 'à', 'A', 'á'],  # Added 'á' as variant
        'ò': ['o', 'ò', 'O', 'ó'],  # Added 'ó' as variant
        'ì': ['i', 'ì', 'I', 'í'],  # Added 'í' as variant
        'ù': ['u', 'ù', 'U', 'ú'],  # Added 'ú' as variant
    }
    result = [word]
    for char, replacements in variants.items():
        if char in word:
            new_variants = []
            for variant in result:
                for replacement in replacements:
                    new_variants.append(variant.replace(char, replacement))
            result.extend(new_variants)
    
    return list(set(result))

def normalize_apostrophes(word: str) -> str:
    """Normalize different types of apostrophes to standard one"""
    return word.replace('’', "'")

def clean_word(word: str) -> str:
    """Clean word from punctuation while preserving letters"""
    # First normalize apostrophes
    word = normalize_apostrophes(word)
    # Then clean punctuation but preserve apostrophes
    cleaned = re.sub(r'[.,:?;()!»«]', '', word)
    # Then lowercase
    return cleaned.lower()

def create_word_index(root: ET.Element) -> Dict[str, List[int]]:
    """Create inverted index of words and their positions"""
    word_index = defaultdict(list)
    
    for elem in root.iter('w'):
        if elem.text:
            word_id = int(elem.attrib.get('{http://www.w3.org/XML/1998/namespace}id').split('_')[1])
            cleaned_word = clean_word(elem.text)
            word_index[cleaned_word].append(word_id)
    
    return word_index

def find_sequence_in_text(text: str, word_index: Dict[str, List[int]]) -> List[int]:
    """Find sequence of words in text allowing for variations"""
    if re.match(r"^\d+[-]*\d*[.]\s", text):
        text = re.sub(r"^\d+[-]*\d*[.]\s", "", text)
    
    words = [clean_word(w) for w in text.split()]
    if not words:
        return []
    
    # Get positions for first word considering all variants
    positions = set()
    first_word = words[0]
    # Try all possible variants of the first word
    for variant in normalize_chars(first_word):
        cleaned_variant = clean_word(variant)
        positions.update(word_index.get(cleaned_variant, []))
        # Also try with Cyrillic character replacements
        alt_variant = clean_word(variant.replace('е', 'e').replace('о', 'o').replace('р', 'p'))
        if alt_variant != cleaned_variant:
            positions.update(word_index.get(alt_variant, []))
    
    if not positions:
        return []
    
    valid_sequences = []
    for start_pos in positions:
        sequence = find_best_matching_sequence(words, start_pos, word_index)
        if sequence:
            valid_sequences.append(sequence)
            
    return sorted(valid_sequences[0]) if valid_sequences else []

def find_best_matching_sequence(words: List[str], start_pos: int, word_index: Dict[str, List[int]]) -> List[int]:
    """Find best matching sequence allowing for variations"""
    MAX_GAP = 2  # Maximum number of words that can be different/missing
    MIN_MATCH_RATIO = 0.7  # Minimum ratio of words that must match
    
    sequence = [start_pos]
    current_pos = start_pos
    matched_words = 1  # First word is already matched
    skipped = 0
    
    for word in words[1:]:
        next_pos = current_pos + 1
        # Generate all possible variants for the current word
        word_variants = normalize_chars(word)
        word_variants = [clean_word(w) for w in word_variants]
        
        # Look ahead up to MAX_GAP positions for the next matching word
        found = False
        for look_ahead in range(MAX_GAP + 1):
            check_pos = next_pos + look_ahead
            # Get the word at this position from the index
            matching_words = [k for k, v in word_index.items() if check_pos in v]
            if matching_words:
                # Check if any variant matches
                if any(variant in matching_words for variant in word_variants):
                    sequence.extend(range(next_pos, check_pos + 1))
                    current_pos = check_pos
                    matched_words += 1
                    skipped += look_ahead
                    found = True
                    break
        
        if not found:
            skipped += 1
            current_pos = next_pos
            sequence.append(next_pos)
    
    if matched_words / len(words) >= MIN_MATCH_RATIO and skipped <= MAX_GAP:
        return sequence
    return []

def process_comments(xml_path: str, comments_path: str, source: str, tag: str, author: str) -> List[Comment]:
    """Process XML and comments files"""
    # Parse XML and create word index
    print(f"Processing comments for {author} in source {source}")
    tree = ET.parse(xml_path)
    root = tree.getroot()
    word_index = create_word_index(root)
    
    # Process comments
    comments = []
    with open(comments_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if line.strip():
                comment = Comment(
                    text=line.strip(),
                    number=i,
                    source=source,
                    tag=tag,
                    author=author
                )
                comment.parse(word_index)
                comments.append(comment)
    
    return comments

def main(author: str, chapter: str):
    chapter_num = chapter.zfill(2)  # Pad with zero if needed
    sources = [
        {f"cap{chapter}": {
            "xml": f"cap{chapter}.xml",
            "comments": f"{author}_cap{chapter}.txt",
            "tag": f"c{chapter}",
        }}
    ]
    
    comments_by_source = {}
    for source in sources:
        for name, values in source.items():
            comments = process_comments(
                values["xml"],
                values["comments"],
                name,
                values["tag"],
                author
            )
            comments_by_source[name] = comments
    
    create_xml(comments_by_source, author=author)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py AUTHOR CHAPTER")
        print("Example: python script.py Russo 17")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])