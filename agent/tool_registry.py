"""
Registers the 4 standalone tools (built in Step 2) as LangChain tools the
agent can call. Each wrapper:
  - has a clear docstring (this is what the LLM reads to decide when to use it)
  - converts the dict return value to a JSON string (tool outputs must be text)
  - keeps the actual logic in tools/*.py untouched and independently testable
"""
import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from langchain_core.tools import tool

from tools.get_stock_data import get_stock_data as _get_stock_data
from tools.analyze_portfolio import analyze_portfolio as _analyze_portfolio
from tools.predict_risk_score import predict_risk_score as _predict_risk_score
from tools.news_search import search_financial_news as _search_financial_news


@tool
def get_stock_data(ticker: str) -> str:
    """
    Get the latest price, recent price change, and fundamentals
    (sector, market cap, P/E ratio, beta, dividend yield, volatility)
    for a given stock ticker symbol.

    Args:
        ticker: stock symbol, e.g. "AAPL" or "TSLA"
    """
    return json.dumps(_get_stock_data(ticker), default=str)


@tool
def analyze_portfolio() -> str:
    """
    Analyze the user's current investment portfolio: total value,
    per-sector exposure percentages, sector concentration risk flags,
    and unrealized profit/loss per position. Takes no arguments —
    always analyzes the full portfolio.
    """
    return json.dumps(_analyze_portfolio(), default=str)


@tool
def predict_risk_score(ticker: str) -> str:
    """
    Predict a risk rating (Low / Medium / High) for a given stock,
    based on its fundamentals (beta, P/E ratio, market cap, dividend
    yield, sector), using a trained ML classifier. Also returns the
    model's confidence and the fundamentals it used.

    Args:
        ticker: stock symbol, e.g. "NVDA"
    """
    return json.dumps(_predict_risk_score(ticker), default=str)


@tool
def search_financial_news(query: str, ticker: str = "") -> str:
    """
    Search recent financial news and filing summaries for information
    relevant to a natural-language question. Optionally restrict results
    to a specific ticker.

    Args:
        query: natural-language question, e.g. "what risks does Tesla face?"
        ticker: optional stock symbol to filter results, e.g. "TSLA".
                Leave empty to search across all tickers.
    """
    return json.dumps(
        _search_financial_news(query, ticker=ticker or None), default=str
    )


ALL_TOOLS = [get_stock_data, analyze_portfolio, predict_risk_score, search_financial_news]
