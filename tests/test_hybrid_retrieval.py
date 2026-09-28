from hybrid_retrieval import HybridRetriever
from retrieval import LexicalDocument


class Encoder:
    def encode(self, values, **kwargs):
        assert values == ["query: scalar"]
        return [[0.1, 0.2]]


class Point:
    def __init__(self, chunk_id, score):
        self.payload = {"chunk_id": chunk_id, "text": chunk_id}
        self.score = score


class Client:
    def query_points(self, **kwargs):
        assert kwargs["collection_name"] == "journey_textbook_bge_v1"
        return type("Response", (), {"points": [Point("vector", 0.9), Point("scalar", 0.8)]})()


def test_hybrid_retriever_fuses_dense_and_bm25_candidates():
    documents = [
        LexicalDocument("scalar", "A scalar is one number.", {"chunk_id": "scalar", "text": "scalar"}),
        LexicalDocument("vector", "A vector has multiple numbers.", {"chunk_id": "vector", "text": "vector"}),
    ]
    retriever = HybridRetriever(documents=documents, encoder=Encoder(), client=Client())

    hits = retriever.search("scalar", top_k=2, candidate_k=2)

    assert [hit.payload["chunk_id"] for hit in hits] == ["scalar", "vector"]
