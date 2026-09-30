import ollama
import os
from qdrant_client import QdrantClient
from reranker import configured_reranker
from query_rewrite import rewrite_query

BASELINE_COLLECTION = "journey_textbook"
LIBRARY_COLLECTION = "journey_textbooks_v1"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL   = "llama3.2"
QDRANT_URL  = "http://localhost:6333"

client = QdrantClient(url=QDRANT_URL)


def active_collection() -> str:
    """Use an explicit collection, otherwise prefer an ingested multi-book library."""
    configured = os.getenv("JOURNEY_COLLECTION")
    if configured:
        return configured
    if client.collection_exists(LIBRARY_COLLECTION):
        if client.get_collection(LIBRARY_COLLECTION).points_count > 0:
            return LIBRARY_COLLECTION
    return BASELINE_COLLECTION


def library_status() -> dict[str, int | str]:
    """Report the collection that new baseline requests will search."""
    collection = active_collection()
    info = client.get_collection(collection)
    return {"collection": collection, "points": int(info.points_count)}

def search(question, top_k=3):
    """Retrieve passages and optionally rerank them with a local ONNX model."""
    question = rewrite_query(question)
    collection = active_collection()
    configured_collection = os.getenv("JOURNEY_COLLECTION")
    hybrid_selected = os.getenv("JOURNEY_RETRIEVAL_MODE", "baseline").lower() == "hybrid"
    if hybrid_selected and (
        collection == BASELINE_COLLECTION
        and configured_collection in {None, BASELINE_COLLECTION}
    ):
        from hybrid_retrieval import hybrid_search

        return hybrid_search(question, top_k=top_k)
    vec = ollama.embeddings(
        model=EMBED_MODEL,
        prompt=question
    )["embedding"]

    reranker = configured_reranker()
    # A reranker needs a wider candidate pool than the final answer uses.
    candidate_limit = max(top_k, 10) if reranker else top_k
    results = client.query_points(
        collection_name=collection,
        query=vec,
        limit=candidate_limit,
        with_payload=True
    ).points
    return reranker.rerank(question, results, top_k) if reranker else results

def ask_journey(question):

    # Find relevant chunks
    hits = search(question)

    # Build context
    context = ""
    citations = []
    for h in hits:
        p = h.payload or {}
        passage_id = str(p.get("problem_id") or p.get("source_name") or "Textbook passage")
        page_number = p.get("page_number", 0)
        source_name = str(p.get("source_name") or p.get("source_pdf") or "Textbook")
        context += f"\n[{passage_id} | {source_name} | Page {page_number}]\n"
        context += str(p.get("text", ""))[:1500] + "\n"
        citations.append({
            "problem_id": passage_id,
            "chapter": p.get("chapter", ""),
            "chapter_topic": p.get("chapter_topic", source_name),
            "page": page_number,
            "set_desc": p.get("set_desc", "Textbook passage"),
            "source_name": source_name,
        })

    # Build prompt
    prompt = f"""You are Journey, an AI textbook tutor.
Use ONLY the textbook content below to answer the student's question.
Be clear, helpful, and precise. Match the subject and terminology of the supplied textbooks.
If the supplied context does not contain the answer, say that the textbooks do not provide enough information.

TEXTBOOK CONTENT:
{context}

STUDENT QUESTION: {question}

Give a clear answer and include code only when it is relevant to the textbook material."""

    # Generate answer
    response = ollama.chat(
        model=os.getenv("JOURNEY_LLM_MODEL", LLM_MODEL),
        messages=[{"role": "user", "content": prompt}]
    )
    answer = response["message"]["content"]

    return answer, citations

if __name__ == "__main__":
    ask_journey("How do I convert degrees to radians in MATLAB?")
    ask_journey("What is the difference between a scalar and a vector?")
    ask_journey("How do I calculate the area of a circle in MATLAB?")
