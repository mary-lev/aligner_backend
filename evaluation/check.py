import os
from dataclasses import dataclass
from typing import Dict, List, Tuple
import xml.etree.ElementTree as ET
from collections import defaultdict
from utils.txt_parser_2 import Comment, process_comments

@dataclass
class AlignmentError:
    comment_num: int
    error_type: str
    line: str
    start_id: int = None
    end_id: int = None
    details: str = ""

class CommentEvaluator:
    def __init__(self, xml_dir: str, comments_dir: str):
        self.xml_dir = xml_dir
        self.comments_dir = comments_dir
        self.errors = defaultdict(list)
        self.stats = defaultdict(lambda: defaultdict(int))

    def evaluate_file_pair(self, author: str, chapter: str) -> Dict:
        """Evaluate alignment for a single file pair"""
        chapter_num = chapter.zfill(2)
        xml_path = os.path.join(self.xml_dir, f"cap{chapter}.xml")
        print(xml_path)
        comments_path = os.path.join(self.comments_dir, f"{author}_cap{chapter}.txt")
        print("comments_path", comments_path)
        
        if not (os.path.exists(xml_path) and os.path.exists(comments_path)):
            print(f"Missing files for {author} chapter {chapter}, {os.path.exists(xml_path)}, {os.path.exists(comments_path)}")
            return
        
        # Process the file pair
        comments = process_comments(
            xml_path,
            comments_path,
            f"cap{chapter}",
            f"c{chapter}",
            author
        )
        
        # Analyze alignments
        self._analyze_alignments(comments, author, chapter)
        
        return self._get_chapter_stats(author, chapter)

    def _analyze_alignments(self, comments: List[Comment], author: str, chapter: str):
        """Analyze alignment issues in comments"""
        prev_start = 0
        key = f"{author}_cap{chapter}"
        
        for comment in comments:
            # Track total comments
            self.stats[key]["total"] += 1
            
            if not comment.start and not comment.end:
                self._add_error(key, AlignmentError(
                    comment_num=comment.number,
                    error_type="both_missing",
                    line=comment.line,
                    details="Neither start nor end position found"
                ))
                self.stats[key]["both_missing"] += 1
                
            elif not comment.start:
                self._add_error(key, AlignmentError(
                    comment_num=comment.number,
                    error_type="start_missing",
                    line=comment.line,
                    end_id=comment.end,
                    details="Start position not found"
                ))
                self.stats[key]["start_missing"] += 1
                
            elif not comment.end:
                self._add_error(key, AlignmentError(
                    comment_num=comment.number,
                    error_type="end_missing",
                    line=comment.line,
                    start_id=comment.start,
                    details="End position not found"
                ))
                self.stats[key]["end_missing"] += 1
            
            # Check for out-of-order alignments
            if comment.start and comment.start < prev_start:
                self._add_error(key, AlignmentError(
                    comment_num=comment.number,
                    error_type="out_of_order",
                    line=comment.line,
                    start_id=comment.start,
                    end_id=comment.end,
                    details=f"Start ID {comment.start} is less than previous start {prev_start}"
                ))
                self.stats[key]["out_of_order"] += 1
            
            if comment.start:
                prev_start = comment.start

    def _add_error(self, key: str, error: AlignmentError):
        """Add error to tracking"""
        self.errors[key].append(error)

    def _get_chapter_stats(self, author: str, chapter: str) -> Dict:
        """Get statistics for a specific chapter"""
        key = f"{author}_cap{chapter}"
        stats = dict(self.stats[key])
        stats["error_rate"] = (
            (stats.get("both_missing", 0) + 
             stats.get("start_missing", 0) + 
             stats.get("end_missing", 0) + 
             stats.get("out_of_order", 0)) / 
            stats["total"]
        ) if stats["total"] > 0 else 0
        return stats

    def evaluate_all(self) -> Tuple[Dict, Dict]:
        """Process all matching files in directories"""
        # Get all comment files
        for filename in os.listdir(self.comments_dir):
            print(filename)
            if filename.endswith(".txt") and filename.startswith("Russo"):
                # Extract author and chapter from filename
                parts = filename.split("_")
                if len(parts) >= 2:
                    author = parts[0]
                    chapter = parts[1].replace("cap", "").replace(".txt", "")
                    self.evaluate_file_pair(author, chapter)
        
        return self._generate_summary()

    def _generate_summary(self) -> Tuple[Dict, Dict]:
        """Generate overall summary statistics"""
        total_stats = defaultdict(int)
        author_stats = defaultdict(lambda: defaultdict(int))
        
        for key, stats in self.stats.items():
            author = key.split("_")[0]
            
            # Aggregate by author
            for stat_type, count in stats.items():
                author_stats[author][stat_type] += count
                total_stats[stat_type] += count
        
        # Calculate error rates
        total_stats["error_rate"] = (
            (total_stats["both_missing"] + 
             total_stats["start_missing"] + 
             total_stats["end_missing"] + 
             total_stats["out_of_order"]) / 
            total_stats["total"]
        ) if total_stats["total"] > 0 else 0
        
        for author in author_stats:
            author_stats[author]["error_rate"] = (
                (author_stats[author]["both_missing"] + 
                 author_stats[author]["start_missing"] + 
                 author_stats[author]["end_missing"] + 
                 author_stats[author]["out_of_order"]) / 
                author_stats[author]["total"]
            ) if author_stats[author]["total"] > 0 else 0
        
        return dict(total_stats), dict(author_stats)

def main():
    # Example usage
    xml_dir = "evaluation/quarantana"
    comments_dir = "evaluation/data_txt"
    
    evaluator = CommentEvaluator(xml_dir, comments_dir)
    total_stats, author_stats = evaluator.evaluate_all()
    
    print("\nOverall Statistics:")
    print(f"Total Comments: {total_stats['total']}")
    print(f"Error Rate: {total_stats['error_rate']:.2%}")
    print(f"Missing Start: {total_stats['start_missing']}")
    print(f"Missing End: {total_stats['end_missing']}")
    print(f"Both Missing: {total_stats['both_missing']}")
    print(f"Out of Order: {total_stats['out_of_order']}")
    
    # print("\nBy Author:")
    # for author, stats in author_stats.items():
    #     print(f"\n{author}:")
    #     print(f"  Total Comments: {stats['total']}")
    #     print(f"  Error Rate: {stats['error_rate']:.2%}")
    #     print(f"  Missing Start: {stats['start_missing']}")
    #     print(f"  Missing End: {stats['end_missing']}")
    #     print(f"  Both Missing: {stats['both_missing']}")
    #     print(f"  Out of Order: {stats['out_of_order']}")

if __name__ == "__main__":
    main()