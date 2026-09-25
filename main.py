from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from learning import LearningRequest, LearningServiceError, create_learning_response
from query import ask_journey

app = FastAPI(title="Journey RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

class Question(BaseModel):
    question: str

@app.post("/ask")
def ask(q: Question):
    answer, citations = ask_journey(q.question)
    return {
        "answer": answer,
        "citations": citations
    }

@app.post("/learn")
def learn(request: LearningRequest):
    """Return a cited explanation and learner-facing quiz from the current RAG pipeline."""
    try:
        return create_learning_response(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LearningServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@app.get("/health")
def health():
    return {"status": "ok", "message": "Journey RAG is running"}

@app.get("/")
def root():
    return {"message": "Welcome to Journey RAG API"}