"""
Seed a mock investor portfolio into the DB. Used by the analyze_portfolio
tool to answer questions like 'am I overexposed to tech?'.

Usage:
    python scripts/seed_portfolio.py
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import insert, delete
from data.db import ENGINE, portfolio_holdings, init_db

# Intentionally tech-heavy so 'sector concentration' queries have a real answer
MOCK_PORTFOLIO = [
    {"ticker": "AAPL", "shares": 50, "cost_basis": 165.00, "sector": "Technology"},
    {"ticker": "MSFT", "shares": 30, "cost_basis": 310.00, "sector": "Technology"},
    {"ticker": "NVDA", "shares": 20, "cost_basis": 450.00, "sector": "Technology"},
    {"ticker": "GOOGL", "shares": 25, "cost_basis": 130.00, "sector": "Technology"},
    {"ticker": "JPM", "shares": 15, "cost_basis": 145.00, "sector": "Financials"},
    {"ticker": "XOM", "shares": 40, "cost_basis": 105.00, "sector": "Energy"},
    {"ticker": "PG", "shares": 20, "cost_basis": 150.00, "sector": "Consumer Staples"},
]


def main():
    init_db()
    with ENGINE.begin() as conn:
        conn.execute(delete(portfolio_holdings))
        conn.execute(insert(portfolio_holdings), MOCK_PORTFOLIO)
    print(f"Seeded {len(MOCK_PORTFOLIO)} holdings.")


if __name__ == "__main__":
    main()
