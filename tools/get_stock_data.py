"""
Tool: get_stock_data

Returns latest price, recent trend, and fundamentals for a given ticker.
This is the simplest tool — a direct DB read, no ML/LLM involved.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from data.db import ENGINE, stock_prices, stock_fundamentals


def get_stock_data(ticker: str) -> dict:
    """
    Args:
        ticker: stock symbol, e.g. 'AAPL'

    Returns:
        dict with latest close, 5-day/30-day change, and fundamentals.
        Returns {"error": ...} if ticker not found.
    """
    ticker = ticker.upper().strip()

    with ENGINE.connect() as conn:
        prices = conn.execute(
            select(stock_prices)
            .where(stock_prices.c.ticker == ticker)
            .order_by(stock_prices.c.date.desc())
            .limit(30)
        ).fetchall()

        fundamentals = conn.execute(
            select(stock_fundamentals).where(stock_fundamentals.c.ticker == ticker)
        ).fetchone()

    if not prices:
        return {"error": f"No price data found for ticker '{ticker}'. Has it been ingested?"}

    latest = prices[0]
    change_5d = None
    change_30d = None
    if len(prices) >= 6:
        change_5d = round((latest.close - prices[5].close) / prices[5].close * 100, 2)
    if len(prices) >= 30:
        change_30d = round((latest.close - prices[-1].close) / prices[-1].close * 100, 2)

    result = {
        "ticker": ticker,
        "latest_close": latest.close,
        "latest_date": str(latest.date),
        "change_5d_pct": change_5d,
        "change_30d_pct": change_30d,
    }

    if fundamentals:
        result.update({
            "company_name": fundamentals.company_name,
            "sector": fundamentals.sector,
            "industry": fundamentals.industry,
            "market_cap": fundamentals.market_cap,
            "pe_ratio": fundamentals.pe_ratio,
            "beta": fundamentals.beta,
            "dividend_yield": fundamentals.dividend_yield,
            "volatility_30d": round(fundamentals.volatility_30d, 4) if fundamentals.volatility_30d else None,
        })

    return result


if __name__ == "__main__":
    import json
    print(json.dumps(get_stock_data("AAPL"), indent=2, default=str))
