"""
qdrant_store.py — RAG storage and Q&A
======================================
Stores articles in Qdrant vector database on disk (survives restarts).
Used by pipeline.py to save articles, and by streamlit_app.py to answer
questions like "what was the Tesla narrative last week?"

Three main functions used by other files:
    store_articles(articles)         — save a list of articles
    retrieve(query, ticker, top_k)   — find similar articles
    ask(question, ticker)            — RAG Q&A: retrieve + LLM answer
"""

import hashlib
from pathlib import Path
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
)
from sentence_transformers import SentenceTransformer
from langchain_ollama import OllamaLLM


# ─── Setup ────────────────────────────────────────────────────────────────────

STORAGE_PATH    = Path("data/qdrant_storage")    
COLLECTION_NAME = "narrative_articles"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"             
VECTOR_SIZE     = 384

STORAGE_PATH.mkdir(parents=True, exist_ok=True)

# Initialize once at import time
embedder = SentenceTransformer(EMBEDDING_MODEL)
qdrant   = QdrantClient(path=str(STORAGE_PATH))
llm      = OllamaLLM(model="qwen2.5:7b", temperature=0.1)


def _setup_collection():
    """Create the collection if it does not exist yet."""
    existing = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION_NAME not in existing:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        print(f"Created collection '{COLLECTION_NAME}'")


# ─── Store articles ───────────────────────────────────────────────────────────

def store_articles(articles: list) -> int:
    """
    Save articles to Qdrant.
    Each article gets embedded (title + summary) and stored with metadata.

    Args:
        articles: list of dicts with keys date, headline, summary, source,
                  ticker, url, sentiment

    Returns:
        number of articles stored
    """
    if not articles:
        return 0

    _setup_collection()

    points = []
    for art in articles:
        text = f"{art.get('headline','')} {art.get('summary','')}".strip()
        if not text:
            continue

        vector = embedder.encode(text).tolist()

        article_key = (
            art.get("url")
            or f"{art.get('headline','')}_{art.get('date','')}"
        )

        #article_id = hashlib.md5(
            #article_key.encode("utf-8")
        #).hexdigest()

        article_key = (
            art.get("url")
            or f"{art.get('headline','')}_{art.get('date','')}"
        )

        article_id = hashlib.md5(
            article_key.encode("utf-8")
        ).hexdigest()

        points.append(PointStruct(
            id=article_id,
            vector=vector,
            payload={
                "ticker":    art.get("ticker",   ""),
                "headline":  art.get("headline", ""),
                "summary":   art.get("summary",  ""),
                "source":    art.get("source",   ""),
                "url":       art.get("url",      ""),
                "date":      art.get("date",     ""),
                "sentiment": art.get("sentiment", None),
                "stored_at": datetime.now().isoformat(),
            },
        ))

    if not points:
        return 0
    
    empty_urls = 0

    for art in articles:
        if not art.get("url"):
            empty_urls += 1

    print(f"Articles with empty URLs: {empty_urls}")

    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
    total = qdrant.count(collection_name=COLLECTION_NAME).count
    print(f"Stored {len(points)} articles. Total in DB: {total}")
    return len(points)


# ─── Retrieve articles ────────────────────────────────────────────────────────

def retrieve(query: str, ticker: str = None, top_k: int = 5) -> list:
    """
    Find articles most similar to the query.
    Optionally filter by ticker.
    """
    _setup_collection()

    if qdrant.count(collection_name=COLLECTION_NAME).count == 0:
        return []

    query_vector = embedder.encode(query).tolist()

    search_filter = None
    if ticker:
        search_filter = Filter(must=[
            FieldCondition(key="ticker", match=MatchValue(value=ticker.upper()))
        ])

   #hits = qdrant.search(
        #collection_name=COLLECTION_NAME,
        #query_vector=query_vector,
        #query_filter=search_filter,
        #limit=top_k,
    #)

    hits = qdrant.query_points(
    collection_name=COLLECTION_NAME,
    query=query_vector,
    query_filter=search_filter,
    limit=top_k,
    ).points


    results = []
    for hit in hits:
        article = dict(hit.payload)
        article["relevance_score"] = round(hit.score, 3)
        results.append(article)
    return results


# ─── RAG Q&A ──────────────────────────────────────────────────────────────────

def ask(question: str, ticker: str = None, top_k: int = 5) -> dict:
    """
    Answer a question using RAG:
    1. Retrieve relevant articles from Qdrant
    2. Pass them as context to the LLM
    3. Return the answer + sources used

    Returns:
        {"answer": str, "sources": list, "article_count": int}
    """
    print(f"\n[RAG] Question: {question}")
    articles = retrieve(question, ticker=ticker, top_k=top_k)

    if not articles:
        return {
            "answer":        "No articles in the database yet. "
                             "Run pipeline.py first to collect and store articles.",
            "sources":       [],
            "article_count": 0,
        }

    print(f"[RAG] Found {len(articles)} relevant articles")

    # Build context
    context = "\n\n".join(
        f"[Article {i+1} | {a.get('date','')} | {a.get('source','')}]\n"
        f"Headline: {a.get('headline','')}\n"
        f"Summary: {a.get('summary','')}"
        for i, a in enumerate(articles)
    )

    prompt = f"""You are a financial narrative analyst.
Answer the question using ONLY the articles below.
If the articles do not contain enough information, say so.
Do NOT give investment advice.

QUESTION:
{question}

ARTICLES:
{context}

Answer in 3-5 sentences. Reference specific dates and sources when relevant."""

    response = llm.invoke(prompt)

    return {
        "answer":        response,
        "sources":       articles,
        "article_count": len(articles),
    }


def db_info() -> dict:
    """Return statistics about the database."""
    _setup_collection()
    total = qdrant.count(collection_name=COLLECTION_NAME).count
    return {
        "total_articles": total,
        "storage_path":   str(STORAGE_PATH.resolve()),
        "collection":     COLLECTION_NAME,
    }


# ─── Quick test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Qdrant RAG store — quick test\n")
    print(f"Current database: {db_info()}\n")

    # Sample data for testing
    sample = [
        {
            "date":      "2026-06-08",
            "headline":  "Tesla Q2 deliveries beat expectations",
            "summary":   "Tesla reported 470k deliveries vs 445k expected. Energy storage record.",
            "source":    "Reuters",
            "ticker":    "TSLA",
            "url":       "https://example.com/1",
            "sentiment": 0.62,
        },
        {
            "date":      "2026-06-07",
            "headline":  "BYD overtakes Tesla in Europe again",
            "summary":   "Chinese EV maker BYD posted record European sales. Tesla market share fell to 12%.",
            "source":    "Bloomberg",
            "ticker":    "TSLA",
            "url":       "https://example.com/2",
            "sentiment": -0.38,
        },
    ]

    store_articles(sample)

    print("\n--- Asking a question ---")
    result = ask("What is happening with Tesla deliveries?", ticker="TSLA")
    print("\nAnswer:")
    print(result["answer"])
    print(f"\nBased on {result['article_count']} articles:")
    for src in result["sources"]:
        print(f"  [{src['relevance_score']:.0%}] {src['headline']}")
