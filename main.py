from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

@app.get("/health")
def health():
    return {"status": "ok", "message": "Journey RAG is running"}

@app.get("/")
def root():
    return {"message": "Welcome to Journey RAG API"}