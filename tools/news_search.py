"""
Tool: search_financial_news
Semantic search over the ingested news/filings collection (Chroma).
Run scripts/ingest_news.py first to populate the store.
"""
from pathlib import Path
import chromadb

CHROMA_PATH = str(Path(__file__).parent.parent / "data" / "chroma")
COLLECTION_NAME = "financial_news"


def search_financial_news(query: str, ticker: str | None = None, top_k: int = 3) -> dict:
    """
    Retrieve the most relevant news/filing snippets for a query.

    Args:
        query: natural-language question, e.g. "any risks for Tesla this quarter?"
        ticker: optional filter, e.g. "TSLA" — restricts results to that ticker
        top_k: number of snippets to return

    Returns:
        dict with a list of matched snippets and their source metadata
    """
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        return {"error": "News collection not found. Run scripts/ingest_news.py first."}

    where_filter = {"ticker": ticker.upper()} if ticker else None

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where_filter,
    )

    matches = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    for doc, meta, dist in zip(docs, metas, dists):
        matches.append({
            "text": doc,
            "ticker": meta.get("ticker"),
            "source": meta.get("source"),
            "relevance_score": round(1 - dist, 3),  # higher = more relevant
        })

    return {"query": query, "matches": matches}


if __name__ == "__main__":
    import json
    result = search_financial_news("what risks does Tesla face this quarter?", ticker="TSLA")
    print(json.dumps(result, indent=2))
