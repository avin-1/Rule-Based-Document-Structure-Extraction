# PDF Outline Extractor (Adobe Hackathon - Round 1A)

This solution addresses the "Understand Your Document" challenge by extracting a structured outline (Title, H1, H2, H3) from PDF files. It is designed to be fast, accurate, and fully compliant with the hackathon's execution constraints.

---

## ⚙️ Core Logic & Approach

The extraction process is a rule-based pipeline that analyzes a document's structural and stylistic properties. This model-free approach ensures the solution is lightweight and runs efficiently offline.

1.  **Document Parsing (`PyMuPDF`)**: The process begins by parsing the PDF to create a structured representation of its content, capturing text, font properties (size, weight), and precise coordinates for every line on each page.


2.  **Noise Reduction (Header/Footer Removal)**: To improve accuracy, the script identifies and excludes repetitive text that appears in the top and bottom margins across multiple pages. This prevents page numbers and running headers from being mistaken for headings.

3.  **Title Identification**: The title is located by scoring text blocks on the first two pages. The scoring algorithm prioritizes text that is:
    * **Prominently Sized**: Has a larger font size than typical body text.
    * **Centered**: Aligned near the horizontal center of the page.
    * **Well-Positioned**: Located in the upper portion of the page.

4.  **Heuristic Heading Scoring**: Every line in the document is evaluated against a set of heuristics to determine if it's a heading. A score is calculated based on properties like:
    * **Style**: Bold text, larger font size, title case, or all-caps.
    * **Structure**: Brevity (fewer than 15 words), being the sole line in a text block.
    * **Punctuation**: Ending with a colon (`:`) vs. a period (`.`).

5.  **Hierarchy Classification**:
    * Candidates that exceed a score threshold are identified as headings.
    * These headings are then grouped by their style (font size and boldness).
    * The styles are ranked—primarily by font size—to establish a hierarchy. The top style is mapped to `H1`, the second to `H2`, and all others to `H3`.

---

## 📚 Technology Stack

* **Primary Library**: **PyMuPDF (`fitz`)** is used for its high-speed and accurate PDF parsing capabilities.
* **Standard Libraries**: The solution exclusively uses built-in Python libraries (`os`, `json`, `re`, `collections`, `statistics`), requiring no external models or network calls. This ensures compliance with the **CPU-only**, **offline**, and **≤ 200MB** size constraints.

---

## 🛠️ Execution Instructions

The solution is containerized with Docker for seamless execution as per the hackathon requirements.

### 1. Build the Docker Image and run

From the project's root directory, run the following command:

```bash
docker build --platform linux/amd64 -t mysolutionname:somerandomidentifier .
docker run --rm -v "$(pwd)/input:/app/input" -v "$(pwd)/output:/app/output" --network none mysolutionname:somerandomidentifier

