"""
Database schema and connection helper for FinSight.

Tables:
- stock_prices: daily OHLCV history per ticker
- stock_fundamentals: snapshot of key fundamentals per ticker
- portfolio_holdings: mock portfolio used by analyze_portfolio tool
"""
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, MetaData, Table
)
from pathlib import Path

DB_PATH = Path(__file__).parent / "finsight.db"
ENGINE = create_engine(f"sqlite:///{DB_PATH}", echo=False)
metadata = MetaData()

stock_prices = Table(
    "stock_prices", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ticker", String, nullable=False, index=True),
    Column("date", Date, nullable=False),
    Column("open", Float),
    Column("high", Float),
    Column("low", Float),
    Column("close", Float),
    Column("volume", Integer),
)

stock_fundamentals = Table(
    "stock_fundamentals", metadata,
    Column("ticker", String, primary_key=True),
    Column("company_name", String),
    Column("sector", String),
    Column("industry", String),
    Column("market_cap", Float),
    Column("pe_ratio", Float),
    Column("beta", Float),
    Column("dividend_yield", Float),
    Column("volatility_30d", Float),  # trailing 30-day annualized volatility
    Column("updated_at", Date),
)

portfolio_holdings = Table(
    "portfolio_holdings", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ticker", String, nullable=False),
    Column("shares", Float, nullable=False),
    Column("cost_basis", Float, nullable=False),
    Column("sector", String),
)


def init_db():
    """Create all tables if they don't already exist."""
    metadata.create_all(ENGINE)
    print(f"Database initialized at {DB_PATH}")


if __name__ == "__main__":
    init_db()
