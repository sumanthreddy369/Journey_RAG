# Multi-textbook ingestion

Journey can prepare any number of local searchable PDF, DOCX, EPUB, TXT,
Markdown, or mixed textbook files. The generic pipeline is independent of the original
problem-number-specific MATLAB chunker.

## One-command workflow

Start Ollama with `nomic-embed-text` and Qdrant on `127.0.0.1:6333`, then pass
files, directories, or both:

```powershell
.\scripts\add-textbooks.ps1 "C:\Books\linear-algebra.pdf" "C:\Books\controls" "C:\Notes\review.md"
```

For every supported file, the command:

1. extracts searchable text while retaining PDF page numbers;
2. normalizes whitespace and creates bounded overlapping chunks;
3. embeds every chunk with local Ollama `nomic-embed-text`;
4. creates `journey_textbooks_v1` with the returned embedding dimension;
5. replaces the prior chunks for that same local path;
6. uploads points in batches with stable UUID identifiers; and
7. stores generic source, page, passage, and title metadata for citations.

Directories are searched recursively. Duplicate input paths are ingested once.
Each book is fully extracted and embedded before its previous points are removed,
so extraction or embedding failure does not erase its existing copy. A failure
stops the command and is printed; it is never silently marked successful.

PDF pages without extracted text are sent through `pytesseract` automatically.
This requires the Tesseract executable to be installed locally and available on
`PATH`. The Python integration is included, but the engine itself is not bundled.
If neither extraction nor OCR yields text, ingestion fails explicitly.

DOCX content is read directly from the document package without Microsoft Word.
EPUB chapters follow the book's spine order. DOCX has no reliable rendered page
map outside Word, so its citation locator is document section 1; EPUB locators
are spine-section positions rather than publisher page numbers.

## Answer selection

When the generic library exists and contains points, normal baseline requests use
it automatically. The selection happens per request, so textbooks added while the
API is running are available immediately. The UI fetches `/library-status` and
shows the active passage count.

Use an explicit override when needed:

```powershell
$env:JOURNEY_COLLECTION = "journey_textbook"       # Original MATLAB corpus
$env:JOURNEY_COLLECTION = "journey_textbooks_v1"  # Generic multi-book library
```

`JOURNEY_RETRIEVAL_MODE=hybrid` applies only to the original corpus when the
active collection is `journey_textbook`. The generic library currently uses
Ollama dense retrieval and optional ONNX reranking with the same embedding space.

## Boundaries

- Searchable PDFs, DOCX, EPUB, TXT, and Markdown are supported.
- Scanned PDF OCR works only when the local Tesseract engine is installed.
- Web pages, audio, video, and DRM-protected ebooks are not accepted.
- Tables, equations, diagrams, and multi-column pages are limited by
  `pdfplumber` text extraction quality.
- There is no browser upload endpoint. Files stay local and are supplied through
  the PowerShell command.
- The pipeline stores extracted chunks in local Qdrant. It does not copy source
  textbook files into the repository or commit them.
- Moving a source creates a new source identity. Remove the old path explicitly
  before or after moving it.

## Remove textbooks

Removal requires the same original path used for ingestion and deletes only that
source's chunks:

```powershell
.\scripts\remove-textbooks.ps1 "C:\Books\old-edition.pdf"
```

An existing directory removes all supported sources currently found beneath it.
If a source file has already been deleted, pass its exact former path. The command
prints how many chunks were removed for each source. Other books and the original
`journey_textbook` collection are untouched.

The collection name is versioned because a future embedding-model change must use
a different collection rather than mixing incompatible vectors.
