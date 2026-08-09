"""
Ingest daily price history + fundamentals for a watchlist of tickers
using yfinance, and store them in the local SQLite DB.

Usage:
    python scripts/ingest_stock_data.py
"""
import sys
from pathlib import Path
from datetime import date

sys.path.append(str(Path(__file__).parent.parent))

import yfinance as yf
import numpy as np
from sqlalchemy import insert, delete

from data.db import ENGINE, stock_prices, stock_fundamentals, init_db

# Expanded to 35 tickers across sectors — the risk model (Step 2) needs
# 20+ to train on REAL data instead of falling back to synthetic data.
# This was flagged as a known limitation back in Step 2; fixing it now
# since a production deployment (Step 8) is exactly the point where it
# stops being acceptable to defer.
WATCHLIST = [
    # Technology
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "CRM", "ORCL", "ADBE", "CSCO",
    # Financials
    "JPM", "BAC", "GS", "MS", "V", "MA",
    # Healthcare
    "JNJ", "UNH", "PFE", "ABBV", "MRK",
    # Energy
    "XOM", "CVX", "COP",
    # Consumer
    "PG", "KO", "PEP", "WMT", "MCD", "NKE",
    # Industrials
    "BA", "CAT", "HON",
    # Growth / higher volatility (useful spread for the risk model)
    "TSLA", "AMD", "NFLX",
]


def ingest_prices(ticker: str, period: str = "6mo"):
    hist = yf.Ticker(ticker).history(period=period)
    if hist.empty:
        print(f"  [warn] no price data for {ticker}")
        return None

    rows = [
        {
            "ticker": ticker,
            "date": idx.date(),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        }
        for idx, row in hist.iterrows()
    ]

    with ENGINE.begin() as conn:
        conn.execute(delete(stock_prices).where(stock_prices.c.ticker == ticker))
        conn.execute(insert(stock_prices), rows)

    # 30-day annualized volatility from daily returns
    closes = hist["Close"].tail(30)
    daily_returns = closes.pct_change().dropna()
    vol_30d = float(daily_returns.std() * np.sqrt(252)) if len(daily_returns) > 1 else None
    return vol_30d


def ingest_fundamentals(ticker: str, vol_30d):
    info = yf.Ticker(ticker).info
    row = {
        "ticker": ticker,
        "company_name": info.get("longName", ticker),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "beta": info.get("beta"),
        "dividend_yield": info.get("dividendYield"),
        "volatility_30d": vol_30d,
        "updated_at": date.today(),
    }
    with ENGINE.begin() as conn:
        conn.execute(delete(stock_fundamentals).where(stock_fundamentals.c.ticker == ticker))
        conn.execute(insert(stock_fundamentals), [row])


def main():
    init_db()
    for ticker in WATCHLIST:
        print(f"Ingesting {ticker}...")
        try:
            vol_30d = ingest_prices(ticker)
            ingest_fundamentals(ticker, vol_30d)
        except Exception as e:
            print(f"  [error] {ticker}: {e}")
    print("Done.")


if __name__ == "__main__":
    main()
