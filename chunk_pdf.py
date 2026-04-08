import re
import json
from pathlib import Path

CHAPTER_MAP = {
    "3": "MATLAB Basics: Scalars",
    "4": "Saving Your Work in MATLAB",
    "5": "Vector Operations",
    "6": "2D Plotting and Using MATLAB Help",
    "7": "Arrays",
    "8": "Conditional and Iterative Programming",
}

def chunk_pdf():
    print("Reading extracted text...")
    text = Path("extracted_text.txt").read_text(encoding="utf-8")

    # Find all problems
    pattern = re.compile(
        r'Problem\s+(\d+)-([AB])\.(\d+)', re.MULTILINE
    )
    matches = list(pattern.finditer(text))
    print(f"Found {len(matches)} problems")

    chunks = []
    for i, m in enumerate(matches):
        chapter  = m.group(1)
        set_type = m.group(2)
        prob_num = m.group(3)
        problem_id = f"Problem {chapter}-{set_type}.{prob_num}"

        # Get text between this problem and next
        start = m.start()
        end   = matches[i+1].start() if i+1 < len(matches) else len(text)
        content = text[start:end].strip()

        # Find page number — look backwards for [PAGE_X]
        before = text[:start]
        page_matches = re.findall(r'\[PAGE_(\d+)\]', before)
        page_num = int(page_matches[-1]) if page_matches else 0

        chunks.append({
            "id":            f"{problem_id.replace(' ','_')}",
            "text":          content,
            "source_pdf":    "MATLAB_JHS_1st_edition_SOLUTIONS.pdf",
            "problem_id":    problem_id,
            "chapter":       int(chapter),
            "chapter_topic": CHAPTER_MAP.get(chapter, f"Chapter {chapter}"),
            "set":           set_type,
            "set_desc":      "Nuts and Bolts" if set_type=="A" else "Problem Solving",
            "problem_num":   int(prob_num),
            "page_number":   page_num,
        })

    # Save chunks
    Path("chunks.json").write_text(
        json.dumps(chunks, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"Saved {len(chunks)} chunks to chunks.json")

    # Show sample
    print("\nSample chunk:")
    print(f"  ID: {chunks[0]['id']}")
    print(f"  Chapter: {chunks[0]['chapter']} - {chunks[0]['chapter_topic']}")
    print(f"  Page: {chunks[0]['page_number']}")
    print(f"  Text preview: {chunks[0]['text'][:100]}")

if __name__ == "__main__":
    chunk_pdf()