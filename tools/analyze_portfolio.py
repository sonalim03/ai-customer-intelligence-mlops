"""
Tool: analyze_portfolio

Answers questions like "am I overexposed to tech?" by computing sector
concentration, unrealized P&L, and largest positions from the mock
portfolio + latest prices in the DB.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from collections import defaultdict
from sqlalchemy import select
from data.db import ENGINE, portfolio_holdings, stock_prices

# Flag a sector as "concentrated" above this % of portfolio value
CONCENTRATION_THRESHOLD_PCT = 40.0


def _latest_price(conn, ticker: str):
    row = conn.execute(
        select(stock_prices.c.close)
        .where(stock_prices.c.ticker == ticker)
        .order_by(stock_prices.c.date.desc())
        .limit(1)
    ).fetchone()
    return row.close if row else None


def analyze_portfolio() -> dict:
    """
    Returns:
        dict with total value, per-sector exposure %, flagged concentration
        risks, and per-holding unrealized P&L.
    """
    with ENGINE.connect() as conn:
        holdings = conn.execute(select(portfolio_holdings)).fetchall()

        if not holdings:
            return {"error": "No portfolio holdings found. Run scripts/seed_portfolio.py first."}

        sector_value = defaultdict(float)
        total_value = 0.0
        positions = []

        for h in holdings:
            price = _latest_price(conn, h.ticker)
            if price is None:
                continue
            market_value = round(price * h.shares, 2)
            cost = round(h.cost_basis * h.shares, 2)
            unrealized_pnl = round(market_value - cost, 2)
            unrealized_pnl_pct = round((market_value - cost) / cost * 100, 2) if cost else None

            sector_value[h.sector] += market_value
            total_value += market_value

            positions.append({
                "ticker": h.ticker,
                "shares": h.shares,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": unrealized_pnl_pct,
                "sector": h.sector,
            })

    sector_exposure = {
        sector: round(value / total_value * 100, 2)
        for sector, value in sector_value.items()
    } if total_value else {}

    concentration_flags = [
        f"{sector} makes up {pct}% of the portfolio (threshold: {CONCENTRATION_THRESHOLD_PCT}%)"
        for sector, pct in sector_exposure.items()
        if pct > CONCENTRATION_THRESHOLD_PCT
    ]

    return {
        "total_value": round(total_value, 2),
        "sector_exposure_pct": sector_exposure,
        "concentration_flags": concentration_flags,
        "positions": sorted(positions, key=lambda p: -p["market_value"]),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(analyze_portfolio(), indent=2, default=str))
