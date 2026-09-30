from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from textbook_ingest import (
    LIBRARY_COLLECTION,
    TextbookPage,
    build_payloads,
    chunk_text,
    discover_textbooks,
    ingest_textbooks,
)


class FakeQdrant:
    def __init__(self):
        self.exists = False
        self.vector_size = None
        self.deleted = []
        self.upserts = []

    def collection_exists(self, collection_name):
        return self.exists

    def create_collection(self, collection_name, vectors_config):
        assert collection_name == LIBRARY_COLLECTION
        self.exists = True
        self.vector_size = vectors_config.size

    def get_collection(self, collection_name):
        vectors = SimpleNamespace(size=self.vector_size)
        return SimpleNamespace(config=SimpleNamespace(params=SimpleNamespace(vectors=vectors)))

    def delete(self, collection_name, points_selector, wait):
        self.deleted.append((collection_name, points_selector, wait))

    def upsert(self, collection_name, points, wait):
        self.upserts.append((collection_name, points, wait))


@pytest.fixture
def workspace_tmp_path() -> Path:
    path = Path(__file__).parents[1] / ".test-artifacts" / str(uuid4())
    path.mkdir(parents=True)
    return path


def test_discover_textbooks_accepts_multiple_files_and_directories(workspace_tmp_path):
    tmp_path = workspace_tmp_path
    first = tmp_path / "First Book.txt"
    first.write_text("first", encoding="utf-8")
    nested = tmp_path / "course"
    nested.mkdir()
    second = nested / "Second Book.md"
    second.write_text("second", encoding="utf-8")
    (nested / "notes.csv").write_text("ignored", encoding="utf-8")

    assert set(discover_textbooks([first, nested])) == {first.resolve(), second.resolve()}


def test_generic_chunking_is_bounded_and_overlapping():
    text = " ".join(f"word-{index}" for index in range(300))
    chunks = chunk_text(text, max_chars=240, overlap_chars=40)

    assert len(chunks) > 1
    assert all(1 <= len(chunk) <= 240 for chunk in chunks)
    assert set(chunks[0].split()) & set(chunks[1].split())


def test_payloads_keep_book_page_and_generic_citation_metadata(workspace_tmp_path):
    tmp_path = workspace_tmp_path
    path = tmp_path / "Control_Systems.pdf"
    path.touch()
    payloads = build_payloads(path, [TextbookPage(7, "A stable system returns to equilibrium.")])

    assert payloads[0]["source_name"] == "Control_Systems.pdf"
    assert payloads[0]["page_number"] == 7
    assert payloads[0]["chapter_topic"] == "Control Systems"
    assert "page 7" in str(payloads[0]["problem_id"])
    assert "source_key" in payloads[0]
    assert str(path.resolve()) not in str(payloads[0])


def test_ingest_multiple_books_creates_library_and_replaces_each_source(workspace_tmp_path):
    tmp_path = workspace_tmp_path
    first = tmp_path / "first.txt"
    second = tmp_path / "second.md"
    first.write_text("First textbook content.", encoding="utf-8")
    second.write_text("Second textbook content.", encoding="utf-8")
    client = FakeQdrant()

    results = ingest_textbooks(
        [first, second],
        client=client,
        embedder=lambda text: [float(len(text)), 1.0, 0.0],
    )

    assert [result.source_name for result in results] == ["first.txt", "second.md"]
    assert client.vector_size == 3
    assert len(client.deleted) == 2
    assert len(client.upserts) == 2
    ids = [point.id for _, points, _ in client.upserts for point in points]
    assert len(ids) == len(set(ids))
