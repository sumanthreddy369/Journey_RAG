from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from guardrails import GuardrailViolation, SlidingWindowRateLimiter, validate_citations, validate_question
from learning import LearningRequest, LearningServiceError, create_learning_response
from query import ask_journey

app = FastAPI(title="Journey RAG API")
rate_limiter = SlidingWindowRateLimiter(limit=20, window_seconds=60)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

class Question(BaseModel):
    question: str

@app.post("/ask")
def ask(q: Question, request: Request):
    try:
        question = validate_question(q.question)
        rate_limiter.check(request.client.host if request.client else "local")
        answer, citations = ask_journey(question)
        validate_citations(citations)
        return {"answer": answer, "citations": citations}
    except GuardrailViolation as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/learn")
def learn(learning_request: LearningRequest, request: Request):
    """Return a cited explanation and learner-facing quiz from the current RAG pipeline."""
    try:
        learning_request.question = validate_question(learning_request.question)
        rate_limiter.check(request.client.host if request.client else "local")
        response = create_learning_response(learning_request)
        validate_citations(response.citations)
        return response
    except GuardrailViolation as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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