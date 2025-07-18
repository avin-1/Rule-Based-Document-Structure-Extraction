import fitz  # PyMuPDF
import json
import sys
import os
from collections import defaultdict
import re

def extract_text_blocks(pdf_path):
    """Extract text blocks with attributes from the PDF."""
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF: {e}")
        sys.exit(1)
    
    blocks = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_blocks = page.get_text("dict")["blocks"]
        for block in page_blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text:  # Skip empty text
                        continue
                    blocks.append({
                        "text": text,
                        "font_size": span["size"],
                        "font": span["font"],
                        "flags": span["flags"],  # For bold, italic, etc.
                        "bbox": span["bbox"],  # (x0, y0, x1, y1)
                        "page": page_num 
                    })
    
    doc.close()
    return blocks

def detect_title(blocks, metadata):
    """Identify the document title robustly, merging multi-line titles."""
    # Check metadata first
    if metadata.get("title") and metadata["title"].strip():
        return metadata["title"]
    
    # Find the first non-empty page
    first_page = min([b["page"] for b in blocks], default=1)
    first_page_blocks = [b for b in blocks if b["page"] == first_page]
    if not first_page_blocks:
        return "Untitled"
    
    # Sort by font size (desc) and vertical position (asc)
    candidates = sorted(first_page_blocks, key=lambda x: (-x["font_size"], x["bbox"][1]))
    if not candidates:
        return "Untitled"
    
    # Take the largest font size among candidates
    max_font_size = candidates[0]["font_size"]
    title_lines = []
    for block in candidates:
        # Merge lines with similar font size and close vertical position
        if abs(block["font_size"] - max_font_size) < 1.0 and len(block["text"]) > 2:
            title_lines.append((block["bbox"][1], block["text"]))
    # Sort by vertical position and join
    title_lines = [t[1] for t in sorted(title_lines, key=lambda x: x[0])]
    title = " ".join(title_lines).strip()
    if title:
        return title
    return "Untitled"

def detect_headings(blocks):
    """Detect headings (H1, H2, H3) for complex PDFs."""
    # Calculate font size statistics
    font_sizes = [b["font_size"] for b in blocks if b["text"]]
    if not font_sizes:
        return []
    
    # Dynamic thresholds for H1, H2, H3 (handles inconsistent PDFs)
    sorted_sizes = sorted(set(font_sizes), reverse=True)
    h1_threshold = sorted_sizes[min(2, len(sorted_sizes)-1)] if sorted_sizes else 12
    h2_threshold = sorted_sizes[min(4, len(sorted_sizes)-1)] if len(sorted_sizes) > 3 else h1_threshold * 0.9
    h3_threshold = sorted_sizes[min(6, len(sorted_sizes)-1)] if len(sorted_sizes) > 5 else h2_threshold * 0.9

    headings = []
    for block in blocks:
        text = block["text"]
        if len(text) < 3 or re.match(r"^\d+(\.\d+)*$", text):  # Skip short or number-only (e.g., "4.4.4...")
            continue
        
        # Heading criteria: font size, bold, or content patterns
        is_heading = (
            block["font_size"] >= h3_threshold or
            block["flags"] & 2 or  # Bold flag
            re.match(r"^(Round|Section|Chapter|Part)\s+\w+", text, re.IGNORECASE) or
            text.isupper()  # All caps often indicate headings
        )
        
        if is_heading:
            # Assign level based on font size and position
            if block["font_size"] >= h1_threshold:
                level = "H1"
            elif block["font_size"] >= h2_threshold:
                level = "H2"
            else:
                level = "H3"
            headings.append({
                "level": level,
                "text": text,
                "page": block["page"],
                "font_size": block["font_size"]
            })
    
    # Merge adjacent blocks with similar attributes (for multi-line headings)
    merged_headings = []
    i = 0
    while i < len(headings):
        current = headings[i]
        if i + 1 < len(headings) and headings[i]["page"] == headings[i+1]["page"]:
            next_heading = headings[i+1]
            if abs(headings[i]["font_size"] - headings[i+1]["font_size"]) < 1.0:
                current["text"] += " " + next_heading["text"]
                i += 1
        merged_headings.append(current)
        i += 1
    
    return merged_headings

def main(pdf_path, output_path):
    """Process PDF and generate JSON output."""
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found")
        sys.exit(1)
    
    # Extract text blocks and metadata
    blocks = extract_text_blocks(pdf_path)
    doc = fitz.open(pdf_path)
    metadata = doc.metadata
    doc.close()
    
    # Detect title and headings
    title = detect_title(blocks, metadata)
    headings = detect_headings(blocks)
    
    # Create JSON output
    output = {
        "title": title,
        "outline": headings
    }
    
    # Write to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Output written to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python extract_outline.py <input.pdf> <output.json>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_path = sys.argv[2]
    main(pdf_path, output_path)