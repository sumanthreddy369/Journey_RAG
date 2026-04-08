import pdfplumber
import json
from pathlib import Path

def extract_pdf(pdf_path):
    print(f"Opening {pdf_path}...")
    all_text = ""
    pages_data = []
    
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        print(f"Total pages: {total}")
        
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                all_text += f"\n[PAGE_{i+1}]\n{text}\n"
                pages_data.append({
                    "page": i+1,
                    "text": text
                })
            if (i+1) % 20 == 0:
                print(f"Processed {i+1}/{total} pages...")
    
    # Save full text
    Path("extracted_text.txt").write_text(
        all_text, encoding="utf-8"
    )
    
    # Save pages as JSON
    Path("pages.json").write_text(
        json.dumps(pages_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    print(f"Done! Extracted {len(pages_data)} pages")
    print("Saved to extracted_text.txt and pages.json")

if __name__ == "__main__":
    extract_pdf("MATLAB_JHS_1st_edition_SOLUTIONS.pdf")