# Optional ONNX Runtime Reranking

Journey RAG can use an ONNX cross-encoder after Qdrant vector search. It keeps
the best semantic matches from Qdrant, then scores each question/passage pair
for relevance before sending the final passages to Ollama.

```text
Question -> nomic-embed-text -> Qdrant top 10 -> ONNX cross-encoder -> top 3 -> Ollama + citations
```

## Setup

1. Install the project dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

2. Export a Hugging Face sequence-classification reranker to ONNX. A suitable
   model is `BAAI/bge-reranker-base`.

   ```powershell
   pip install optimum[onnxruntime]
   optimum-cli export onnx --model BAAI/bge-reranker-base .\models\bge-reranker-onnx
   ```

3. Point Journey RAG to the exported model for the current terminal session:

   ```powershell
   $env:JOURNEY_ONNX_RERANKER_DIR = "$PWD\models\bge-reranker-onnx"
   uvicorn main:app --reload
   ```

If `JOURNEY_ONNX_RERANKER_DIR` is not set, reranking is disabled and the
existing Qdrant-only retrieval behavior is unchanged. The exported model is
local and should not be committed to Git because it is large.
