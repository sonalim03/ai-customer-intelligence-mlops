"""
Sample news & filing snippets used to seed the RAG vector store for
development/demo purposes.

⚠️ These are SYNTHETIC placeholder snippets written for this project,
not real scraped articles. Before showing this project publicly, swap
this out for a real ingestion pipeline (e.g. NewsAPI, SEC EDGAR full-text
search, or a scraper) — that's a good "v2" improvement to mention in
your README.
"""

SAMPLE_DOCS = [
    {
        "id": "news-aapl-1",
        "ticker": "AAPL",
        "source": "sample_news",
        "text": (
            "Apple reported quarterly iPhone revenue roughly in line with "
            "analyst expectations, while Services revenue continued to grow "
            "faster than the overall company, now representing a larger share "
            "of total sales. Management pointed to strong subscription growth "
            "across App Store, iCloud, and Apple Music."
        ),
    },
    {
        "id": "news-aapl-2",
        "ticker": "AAPL",
        "source": "sample_news",
        "text": (
            "Analysts flagged softer demand in the China smartphone market as "
            "a near-term risk for Apple, citing increased competition from "
            "local manufacturers offering competitive pricing on premium "
            "devices."
        ),
    },
    {
        "id": "news-tsla-1",
        "ticker": "TSLA",
        "source": "sample_news",
        "text": (
            "Tesla's delivery numbers for the quarter came in slightly below "
            "consensus estimates, which some analysts attributed to increased "
            "EV competition and price cuts across the industry pressuring "
            "margins. The company reiterated its full-year production targets."
        ),
    },
    {
        "id": "news-tsla-2",
        "ticker": "TSLA",
        "source": "sample_news",
        "text": (
            "Tesla shares have shown elevated volatility this quarter, driven "
            "in part by comments from company leadership on social media and "
            "shifting investor sentiment around the timeline for autonomous "
            "driving features."
        ),
    },
    {
        "id": "news-nvda-1",
        "ticker": "NVDA",
        "source": "sample_news",
        "text": (
            "Nvidia's data center segment continued to be the primary growth "
            "driver for the company, with demand for AI training and inference "
            "hardware remaining a central theme across earnings commentary "
            "from major cloud providers."
        ),
    },
    {
        "id": "news-jpm-1",
        "ticker": "JPM",
        "source": "sample_news",
        "text": (
            "JPMorgan's net interest income benefited from the prevailing "
            "interest rate environment, though executives cautioned that "
            "margins could compress if rates begin to decline over the "
            "coming year."
        ),
    },
    {
        "id": "news-xom-1",
        "ticker": "XOM",
        "source": "sample_news",
        "text": (
            "Exxon Mobil's results were closely tied to crude oil price "
            "movements during the quarter, with refining margins offering "
            "an additional swing factor in overall profitability."
        ),
    },
    {
        "id": "news-macro-1",
        "ticker": None,
        "source": "sample_news",
        "text": (
            "Broader market sentiment remained sensitive to signals from "
            "central bank commentary on interest rate policy, with "
            "technology and growth stocks generally showing higher "
            "sensitivity to rate expectations than defensive sectors."
        ),
    },
]

if __name__ == "__main__":
    print(f"{len(SAMPLE_DOCS)} sample documents available for ingestion.")
