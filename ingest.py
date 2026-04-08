import json
import ollama
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from tqdm import tqdm

COLLECTION  = "journey_textbook"
EMBED_MODEL = "nomic-embed-text"
QDRANT_URL  = "http://localhost:6333"

def embed(text):
    resp = ollama.embeddings(
        model=EMBED_MODEL,
        prompt=text[:4000]
    )
    return resp["embedding"]

def ingest():
    # Connect to Qdrant
    client = QdrantClient(url=QDRANT_URL)
    print("Connected to Qdrant")

    # Create collection if not exists
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(
                size=768,
                distance=Distance.COSINE
            ),
        )
        print(f"Created collection: {COLLECTION}")
    else:
        print(f"Collection {COLLECTION} already exists")

    # Load chunks
    chunks = json.loads(
        open("chunks.json", encoding="utf-8").read()
    )
    print(f"Loaded {len(chunks)} chunks")

    # Embed and upload
    points = []
    for i, chunk in enumerate(tqdm(chunks, desc="Embedding")):
        try:
            vec = embed(chunk["text"])
            points.append(PointStruct(
                id=i,
                vector=vec,
                payload={
                    "text":          chunk["text"][:2000],
                    "problem_id":    chunk["problem_id"],
                    "chapter":       chunk["chapter"],
                    "chapter_topic": chunk["chapter_topic"],
                    "set":           chunk["set"],
                    "set_desc":      chunk["set_desc"],
                    "page_number":   chunk["page_number"],
                    "source_pdf":    chunk["source_pdf"],
                }
            ))
        except Exception as e:
            print(f"Error on chunk {i}: {e}")
            continue

    # Upload in batches of 20
    print("Uploading to Qdrant...")
    batch_size = 20
    for i in range(0, len(points), batch_size):
        batch = points[i:i+batch_size]
        client.upsert(
            collection_name=COLLECTION,
            points=batch
        )
        print(f"Uploaded {min(i+batch_size, len(points))}/{len(points)}")

    print(f"\nDone! {len(points)} chunks stored in Qdrant")
    print("Open http://localhost:6333/dashboard to see them")

if __name__ == "__main__":
    ingest()