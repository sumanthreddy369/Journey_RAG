# Dataset, provenance, and citation policy

## Included corpus

The project contains extracted content from a local MATLAB textbook solution
corpus. `chunk_pdf.py` produces `chunks.json`; each chunk records:

| Field | Purpose |
| --- | --- |
| `text` | Content available to retrieval and generation. |
| `source_pdf` | Source-document identifier. |
| `problem_id` | Textbook exercise reference. |
| `chapter` / `chapter_topic` | Learning-topic metadata. |
| `set` / `set_desc` | Exercise category. |
| `page_number` | Citation page reference. |
| `chunk_id` | Stable experimental identifier in the BGE collection. |

## Dataset flow

```text
PDF -> extracted_text.txt -> chunks.json -> embedding/index collection
    -> retrieved passages -> answer citations
```

## Evaluation data

`evals/retrieval_cases.json` contains eight source-checked questions with expected
relevant chunks spanning chapters 3–8. `evaluate_live.py` scores those labels
against the running local baseline or experimental hybrid path. It validates
baseline Qdrant payload metadata against `chunks.json` before mapping point IDs
to citation IDs. Run from the repository root with Qdrant and Ollama available:

```powershell
.\venv\Scripts\python.exe evaluate_live.py --mode baseline --top-k 5
.\venv\Scripts\python.exe evaluate_live.py --mode hybrid --top-k 5
```

On 2026-09-28, the local baseline returned recall@5 1.0, MRR 0.875 and
NDCG@5 0.908. The existing experimental BGE/BM25/RRF path returned recall@5
0.875, MRR 0.629 and NDCG@5 0.690 on the same eight questions. These are
small, question-derived local retrieval checks, not held-out quality estimates,
grounded-answer scores or a reason to switch the default path. No latency
comparison was recorded. The installed Qdrant client 1.19.0 warned that the
local server 1.17.1 is outside its supported minor-version range; both runs
completed, but compatibility should be corrected before further benchmarks.

## Boundaries

- Never commit student names, grades, quiz answers, access tokens, API keys,
  private PDFs, or institutional documents.
- Keep learner progress separate from the corpus; current sessions are only
  in-memory local data.
- Keep provenance and citation metadata for every new document source.
- Confirm copyright and institutional approval before publishing another corpus.
