"""Optional local PostgreSQL history. No questions, answers, or identities are stored."""

from datetime import datetime, timezone
from functools import lru_cache
import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import CheckConstraint, Column, DateTime, Integer, MetaData, String, Table, create_engine, select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError

from progress import QuizEvaluation

metadata = MetaData()
history = Table(
    "progress_history", metadata,
    Column("timestamp", DateTime(timezone=True), primary_key=True),
    Column("topic_label", String(120), nullable=False),
    Column("score", Integer, nullable=False),
    Column("route", String(10), nullable=False),
    Column("recommendation", String(200), nullable=False),
    CheckConstraint("score BETWEEN 0 AND 100", name="valid_score"),
    CheckConstraint("route IN ('reteach', 'practice', 'advance')", name="valid_route"),
)


class HistoryUnavailable(RuntimeError):
    """A deliberately redacted database error safe for the API."""


class HistoryEntry(BaseModel):
    topic_label: str
    score: int
    route: Literal["reteach", "practice", "advance"]
    recommendation: str
    timestamp: datetime


def database_url() -> str | None:
    """Allow only a local psycopg PostgreSQL connection, without URI overrides."""
    raw = os.getenv("JOURNEY_DATABASE_URL")
    if not raw:
        return None
    try:
        url = make_url(raw)
        if (url.drivername != "postgresql+psycopg"
                or url.host not in {"127.0.0.1", "localhost", "::1"}
                or url.query):
            raise ValueError("Nonlocal or unsupported database configuration")
    except (ValueError, SQLAlchemyError) as exc:
        raise HistoryUnavailable("Progress database configuration is invalid.") from exc
    return raw


@lru_cache(maxsize=1)
def _engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True, pool_size=2, max_overflow=0, pool_timeout=3,
                         hide_parameters=True,
                         connect_args={"connect_timeout": 3, "options": "-c statement_timeout=3000"})


@lru_cache(maxsize=1)
def _topics() -> frozenset[str]:
    chunks = json.loads(Path(__file__).with_name("chunks.json").read_text(encoding="utf-8"))
    return frozenset(str(chunk["chapter_topic"]) for chunk in chunks if chunk.get("chapter_topic"))


def textbook_topic(citations: list[dict]) -> str:
    """Select a corpus label; never derive persisted text from a learner question."""
    for citation in citations:
        label = citation.get("chapter_topic")
        if isinstance(label, str) and label in _topics() and len(label) <= 120:
            return label
    return "MATLAB fundamentals"


def save_progress(topic: str, result: QuizEvaluation, timestamp: datetime) -> bool:
    """Store one completed quiz; retrying the same timestamp is idempotent."""
    url = database_url()
    if url is None:
        return False
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    try:
        with _engine(url).begin() as connection:
            connection.execute(pg_insert(history).values(
                topic_label=topic, score=result.score_percent, route=result.route,
                recommendation=result.next_action, timestamp=timestamp,
            ).on_conflict_do_nothing(index_elements=[history.c.timestamp]))
    except SQLAlchemyError as exc:
        raise HistoryUnavailable("Progress could not be saved. Check the local database and migrations.") from exc
    return True


def read_progress(limit: int, offset: int) -> list[HistoryEntry]:
    url = database_url()
    if url is None:
        raise HistoryUnavailable("Progress history is disabled. Configure the local database to enable it.")
    try:
        with _engine(url).connect() as connection:
            rows = connection.execute(select(history).order_by(history.c.timestamp.desc())
                                      .limit(limit).offset(offset)).mappings().all()
    except SQLAlchemyError as exc:
        raise HistoryUnavailable("Progress history is unavailable. Check the local database and migrations.") from exc
    return [HistoryEntry(**{**row, "timestamp": row["timestamp"].astimezone(timezone.utc)}) for row in rows]
