from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from guardrails import GuardrailViolation, SlidingWindowRateLimiter, validate_citations, validate_question
from learning import LearningRequest, LearningServiceError, create_learning_response, create_learning_session
from progress import QuizEvaluation, QuizSubmission
from query import ask_journey
from sessions import LocalQuizSessionStore
from progress_history import HistoryEntry, HistoryUnavailable, read_progress, save_progress, textbook_topic

app = FastAPI(title="Journey RAG API")
PROJECT_ROOT = Path(__file__).parent
app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "static"), name="static")
rate_limiter = SlidingWindowRateLimiter(limit=20, window_seconds=60)
quiz_sessions = LocalQuizSessionStore()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8003", "http://localhost:8003"],
    allow_methods=["*"],
    allow_headers=["*"]
)

class Question(BaseModel):
    question: str


class LocalQuizSessionRequest(BaseModel):
    """Development-only answer key input; no learner data is persisted."""

    answer_key: list[int]


class LearningSessionEvaluation(QuizEvaluation):
    progress_saved: bool
    progress_message: str

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


@app.post("/learning-sessions")
def create_learning_session_route(learning_request: LearningRequest, request: Request):
    """Create a real local learning session and retain its answer key server-side."""
    try:
        learning_request.question = validate_question(learning_request.question)
        rate_limiter.check(request.client.host if request.client else "local")
        draft = create_learning_session(learning_request)
        validate_citations(draft.response.citations)
        session_id = quiz_sessions.create(draft.answer_key, topic=textbook_topic(draft.response.citations))
        return {"session_id": session_id, **draft.response.model_dump()}
    except GuardrailViolation as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LearningServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/learning-sessions/{session_id}/submit", response_model=LearningSessionEvaluation)
def submit_learning_session(session_id: str, submission: QuizSubmission) -> LearningSessionEvaluation:
    """Evaluate answers for a model-generated local learning session."""
    try:
        warning = None

        def record(topic: str, result: QuizEvaluation, timestamp: datetime) -> bool:
            nonlocal warning
            try:
                return save_progress(topic, result, timestamp)
            except HistoryUnavailable as exc:
                warning = str(exc)
                return False

        result, saved = quiz_sessions.complete(session_id, submission, record)
        return LearningSessionEvaluation(
            **result.model_dump(), progress_saved=saved,
            progress_message="Progress saved locally." if saved else
            (warning or "Progress history is disabled; this score was not saved."),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/progress-history", response_model=list[HistoryEntry])
def progress_history(limit: int = Query(default=20, ge=1, le=100),
                     offset: int = Query(default=0, ge=0)) -> list[HistoryEntry]:
    """Shared anonymous history for this local installation; no learner identities."""
    try:
        return read_progress(limit, offset)
    except HistoryUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/local-quiz-sessions")
def create_local_quiz_session(payload: LocalQuizSessionRequest):
    """Create a process-local session for a synthetic answer key."""
    try:
        return {"session_id": quiz_sessions.create(payload.answer_key)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/local-quiz-sessions/{session_id}/submit")
def submit_local_quiz(session_id: str, submission: QuizSubmission):
    """Evaluate a synthetic local quiz and return the deterministic route."""
    try:
        return quiz_sessions.evaluate(session_id, submission)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.get("/health")
def health():
    return {"status": "ok", "message": "Journey RAG is running"}

@app.get("/")
def root():
    return {"message": "Welcome to Journey RAG API"}


@app.get("/app", include_in_schema=False)
def learner_app():
    """Serve the local learner-facing demonstration interface."""
    return FileResponse(PROJECT_ROOT / "static" / "index.html")
