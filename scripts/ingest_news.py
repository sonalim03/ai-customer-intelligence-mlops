"""
Embed the sample news/filing docs into a persistent local Chroma DB.
Run this once (and again whenever data/sample_news.py changes).

Usage:
    python scripts/ingest_news.py
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import chromadb
from data.sample_news import SAMPLE_DOCS

CHROMA_PATH = str(Path(__file__).parent.parent / "data" / "chroma")
COLLECTION_NAME = "financial_news"


def main():
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Fresh collection each run, so re-running this script is idempotent
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)

    collection.add(
        ids=[d["id"] for d in SAMPLE_DOCS],
        documents=[d["text"] for d in SAMPLE_DOCS],
        metadatas=[
            {"ticker": d["ticker"] or "GENERAL", "source": d["source"]}
            for d in SAMPLE_DOCS
        ],
    )

    print(f"Ingested {len(SAMPLE_DOCS)} docs into Chroma collection '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    main()
