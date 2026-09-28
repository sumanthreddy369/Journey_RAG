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

`evals/retrieval_cases.json` is a small seed set of questions with expected
relevant chunks. Expand it with human-verified labels before publishing quality
claims. Compare the same cases, settings, and latency measurement across dense,
hybrid, and reranked retrieval.

## Boundaries

- Never commit student names, grades, quiz answers, access tokens, API keys,
  private PDFs, or institutional documents.
- Keep learner progress separate from the corpus; current sessions are only
  in-memory local data.
- Keep provenance and citation metadata for every new document source.
- Confirm copyright and institutional approval before publishing another corpus.
