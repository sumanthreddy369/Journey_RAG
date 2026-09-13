# Journey RAG

AI-powered Retrieval-Augmented Generation pipeline for the Journey adaptive textbook platform (CS-ERG, Michigan Tech).

## Stack
- **PDF extraction:** pdfplumber
- **Vector database:** Qdrant (Docker)
- **Embeddings:** Ollama + nomic-embed-text
- **LLM:** Ollama + llama3.2
- **RAG:** LlamaIndex
- **API:** FastAPI + uvicorn
- **MCP:** FastMCP, wrapping the existing Journey retrieval and answer functions

## Setup

1. Install dependencies in a virtual environment:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

2. Start Qdrant at `http://localhost:6333` and Ollama. Make sure these models are available:

```powershell
ollama pull nomic-embed-text
ollama pull llama3.2
```

3. Start the existing HTTP API:

```powershell
.\venv\Scripts\python.exe -m uvicorn main:app --reload
```

4. Start the MCP server in a separate terminal:

```powershell
.\venv\Scripts\python.exe mcp_server.py
```

The MCP endpoint is `http://127.0.0.1:8001/mcp`. It is read-only and uses the existing `journey_textbook` Qdrant collection; it does not reprocess or duplicate textbook vectors.
