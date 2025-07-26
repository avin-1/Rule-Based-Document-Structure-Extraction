import fitz  # PyMuPDF
import json
import os
import re
import argparse
from collections import defaultdict
from statistics import median, mode, StatisticsError

CONFIG = {
    "header_threshold": 0.15,
    "footer_threshold": 0.85,
    "min_heading_score": 3.0,
    "font_size_ratio": 1.0,
    "min_body_text_words": 6,
    "title_page_limit": 2,
}

def get_document_structure(pdf_path):
    doc = fitz.open(pdf_path)
    doc_structure = []
    for page_num, page in enumerate(doc):
        page_data = {
            "page_num": page_num + 1,
            "page_width": page.rect.width,
            "page_height": page.rect.height,
            "blocks": []
        }
        blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_LIGATURES).get("blocks", [])
        for b in blocks:
            if b.get("type") == 0:
                block_data = {"bbox": b['bbox'], "lines": []}
                for line in b.get("lines", []):
                    spans = line.get("spans")
                    if spans:
                        line_text = " ".join(s.get("text", "") for s in spans).strip()
                        if line_text:
                            clean_line = {
                                "text": line_text,
                                "bbox": line.get("bbox", []),
                                "spans": spans,
                            }
                            block_data["lines"].append(clean_line)
                if block_data["lines"]:
                    page_data["blocks"].append(block_data)
        doc_structure.append(page_data)
    doc.close()
    return doc_structure

def identify_and_filter_content(doc_structure, config):
    ignored_line_ids = set()
    potential_hf_lines = defaultdict(list)
    
    for page in doc_structure[1:]:
        for block in page['blocks']:
            is_header = block['bbox'][3] < page['page_height'] * config['header_threshold']
            is_footer = block['bbox'][1] > page['page_height'] * config['footer_threshold']
            if is_header or is_footer:
                for line in block['lines']:
                    normalized_text = re.sub(r'\d+', '#', line['text'])
                    if len(normalized_text.split()) < 8:
                        potential_hf_lines[normalized_text].append(page['page_num'])

    num_pages = len(doc_structure)
    for text, pages in potential_hf_lines.items():
        if len(set(pages)) > 2 or (num_pages > 5 and len(set(pages)) > num_pages * 0.5):
            for page in doc_structure:
                if page['page_num'] in pages:
                    for block in page['blocks']:
                        for line in block['lines']:
                            if re.sub(r'\d+', '#', line['text']) == text:
                                ignored_line_ids.add((line['text'], tuple(map(round, line['bbox']))))

    for page in doc_structure:
        for block in page['blocks']:
            if len(block['lines']) > 5:
                line_spacings = [
                    block['lines'][i+1]['bbox'][1] - block['lines'][i]['bbox'][3]
                    for i in range(len(block['lines']) - 1)
                ]
                if len(line_spacings) > 2 and len(set(round(s) for s in line_spacings)) < 3:
                    for line in block['lines']:
                        ignored_line_ids.add((line['text'], tuple(map(round, line['bbox']))))

    return ignored_line_ids

def find_title_by_layout(doc_structure, ignored_line_ids, config):
    candidates = []
    for page in doc_structure[:config['title_page_limit']]:
        for block in page['blocks']:
            if any((line['text'], tuple(map(round, line['bbox']))) in ignored_line_ids for line in block['lines']):
                continue
            if not (1 <= len(block['lines']) <= 4) or block['bbox'][1] > page['page_height'] * 0.4:
                continue

            block_text = " ".join(line['text'] for line in block['lines'])
            if not block_text:
                continue
            
            avg_size = median([s['size'] for line in block['lines'] for s in line['spans']]) if any(line['spans'] for line in block['lines']) else 0
            block_center_x = (block['bbox'][0] + block['bbox'][2]) / 2
            page_center_x = page['page_width'] / 2
            centering_score = (1 - abs(block_center_x - page_center_x) / page_center_x) * 15 if page_center_x > 0 else 0
            position_score = (1 - block['bbox'][1] / (page['page_height'] * 0.4)) * 5
            score = avg_size + centering_score + position_score
            candidates.append({"text": block_text, "score": score, "lines": block['lines']})

    if not candidates:
        return "Untitled Document", set()

    best_candidate = max(candidates, key=lambda x: x["score"])
    return best_candidate['text'], {(line['text'], tuple(map(round, line['bbox']))) for line in best_candidate['lines']}

def get_heading_score(line, block, body_text_size, config):
    text = line['text']
    spans = line['spans']
    
    if re.match(r'^\s*•|^\s*\|^\s-|`', text) or \
       re.search(r'https?://\S+|www\.\S+|\S+\.git$', text) or \
       len(text.split()) > 15 or \
       text.endswith(('.', ',')):
        return -10
    
    font_sizes = {round(s['size']) for s in spans}
    if len(font_sizes) > 1:
        return -10

    score = 0.0
    line_size = font_sizes.pop()
    is_bold = any(s['flags'] & 2 for s in spans)

    if line_size > body_text_size:
        score += (line_size - body_text_size) * 3
    elif line_size < body_text_size:
        score -= (body_text_size - line_size)

    if is_bold:
        score += 2.5
    if re.match(r"^\d+\.\s", text):
        score += 2.0
    if text.istitle():
        score += 1.5
    if text.isupper():
        score += 2.0
    if len(text.split()) < 10:
        score += 1.0
    if text.endswith(':'):
        score += 2.0
    if len(block['lines']) == 1:
        score += 3.0
    if line_size < body_text_size and not is_bold:
        score -= 3.0

    return score

def extract_pdf_outline(pdf_path, config=CONFIG):
    doc_structure = get_document_structure(pdf_path)
    
    if not any(block['lines'] for page in doc_structure for block in page['blocks']):
        return {"title": "No Text Found", "outline": [], "error": "No text extracted. Consider using OCR."}

    font_sizes = [
        round(s['size']) for page in doc_structure for b in page['blocks'] 
        for line in b['lines'] for s in line['spans']
        if len(line['text'].split()) > config['min_body_text_words'] and not any(sp['flags'] & 2 for sp in line['spans'])
    ]
    body_text_size = median(font_sizes) if font_sizes else 10

    ignored_line_ids = identify_and_filter_content(doc_structure, config)
    title_text, title_line_ids = find_title_by_layout(doc_structure, ignored_line_ids, config)
    ignored_line_ids.update(title_line_ids)

    heading_candidates = []
    for page in doc_structure:
        for block in page['blocks']:
            for line in block['lines']:
                if (line['text'], tuple(map(round, line['bbox']))) in ignored_line_ids:
                    continue
                score = get_heading_score(line, block, body_text_size, config)
                if score > config['min_heading_score']:
                    line['page'] = page['page_num']
                    heading_candidates.append(line)

    if not heading_candidates:
        return {"title": title_text, "outline": []}

    style_properties = defaultdict(list)
    for h in heading_candidates:
        try:
            style_key = (mode([round(s['size']) for s in h['spans']]), any(s['flags'] & 2 for s in h['spans']))
            style_properties[style_key].append(h['bbox'][0])
        except StatisticsError:
            continue

    ranked_styles = [
        {"size": style[0], "bold": style[1], "x0": median(x0s), "style_key": style}
        for style, x0s in style_properties.items()
    ]
    ranked_styles.sort(key=lambda x: (-x["size"], x["x0"]))

    style_to_level = {style["style_key"]: f"H{min(i+1, 3)}" for i, style in enumerate(ranked_styles[:3])}

    outline = []
    for line in heading_candidates:
        try:
            style_key = (mode([round(s['size']) for s in line['spans']]), any(s['flags'] & 2 for s in line['spans']))
        except StatisticsError:
            style_key = None
        level = style_to_level.get(style_key, "H3")
        outline.append({"level": level, "text": line["text"], "page": line["page"]})

    return {"title": title_text, "outline": outline}

def save_json(data, output_path):
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

### MAIN BLOCK: Replace this with argparse version later
if __name__ == "__main__":
    input_pdf = "input/sample.pdf"
    output_json = "output/output.json"
    try:
        print(f"Processing {input_pdf}...")
        result = extract_pdf_outline(input_pdf)
        save_json(result, output_json)
        print(f"Success! Outline saved to {output_json}")
    except Exception as e:
        print(f"Error: {e}")
        save_json({"title": "Extraction Failed", "outline": [], "error": str(e)}, output_json)
