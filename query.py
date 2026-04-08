import ollama
from qdrant_client import QdrantClient

COLLECTION  = "journey_textbook"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL   = "llama3.2"
QDRANT_URL  = "http://localhost:6333"

client = QdrantClient(url=QDRANT_URL)

def search(question, top_k=3):
    vec = ollama.embeddings(
        model=EMBED_MODEL,
        prompt=question
    )["embedding"]

    results = client.query_points(
        collection_name=COLLECTION,
        query=vec,
        limit=top_k,
        with_payload=True
    ).points
    return results

def ask_journey(question):
    print(f"\n{'='*60}")
    print(f"QUESTION: {question}")
    print('='*60)

    # Find relevant chunks
    hits = search(question)

    # Build context
    context = ""
    citations = []
    for h in hits:
        p = h.payload
        context += f"\n[{p['problem_id']} | Ch{p['chapter']} | Page {p['page_number']}]\n"
        context += p["text"][:1500] + "\n"
        citations.append({
            "problem_id":    p["problem_id"],
            "chapter":       p["chapter"],
            "chapter_topic": p["chapter_topic"],
            "page":          p["page_number"],
            "set_desc":      p["set_desc"],
        })

    # Build prompt
    prompt = f"""You are Journey, an AI tutor for MATLAB programming.
Use ONLY the textbook content below to answer the student's question.
Be clear, helpful and precise. Show MATLAB code when relevant.

TEXTBOOK CONTENT:
{context}

STUDENT QUESTION: {question}

Give a clear answer with any relevant MATLAB code."""

    # Generate answer
    response = ollama.chat(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    answer = response["message"]["content"]

    print("\nANSWER:")
    print(answer)
    print("\nSOURCES:")
    for c in citations:
        print(f"  - {c['problem_id']} | Ch{c['chapter']}: {c['chapter_topic']} | Page {c['page']} | {c['set_desc']}")

    return answer, citations

if __name__ == "__main__":
    ask_journey("How do I convert degrees to radians in MATLAB?")
    ask_journey("What is the difference between a scalar and a vector?")
    ask_journey("How do I calculate the area of a circle in MATLAB?")