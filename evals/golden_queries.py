"""
Golden evaluation set for the FinSight agent.

Each entry defines a realistic user query plus what a *correct* agent
response should do — which tool(s) it should call, and any specific
facts the answer should be grounded in. The scorer (evals/scorer.py)
checks actual agent behavior against this.

Keep this file growing over time — 30-50 cases is a reasonable target
for a portfolio project. Cover:
  - single-tool queries (one clear tool)
  - multi-tool queries (agent must chain/combine tools)
  - edge cases (invalid ticker, ambiguous question)
  - questions that should NOT trigger a tool (pure clarification)
"""

GOLDEN_QUERIES = [
    # --- get_stock_data: single tool ---
    {
        "id": "stock-001",
        "query": "What's AAPL's current price and volatility?",
        "expected_tools": ["get_stock_data"],
        "category": "single_tool",
        "notes": "Straightforward lookup, should call get_stock_data once with AAPL.",
    },
    {
        "id": "stock-002",
        "query": "What is Tesla's P/E ratio and beta?",
        "expected_tools": ["get_stock_data"],
        "category": "single_tool",
        "notes": "Should map 'Tesla' -> ticker TSLA.",
    },
    {
        "id": "stock-003",
        "query": "What's the market cap of a ticker that doesn't exist, like ZZZZ?",
        "expected_tools": ["get_stock_data"],
        "category": "edge_case",
        "notes": "Tool should return an error; agent must report it plainly, not invent a number.",
    },

    # --- analyze_portfolio: single tool ---
    {
        "id": "portfolio-001",
        "query": "Am I overexposed to any sector in my portfolio?",
        "expected_tools": ["analyze_portfolio"],
        "category": "single_tool",
        "notes": "Should surface the tech concentration flag.",
    },
    {
        "id": "portfolio-002",
        "query": "What's the total value of my portfolio right now?",
        "expected_tools": ["analyze_portfolio"],
        "category": "single_tool",
    },
    {
        "id": "portfolio-003",
        "query": "Which of my holdings is currently at a loss?",
        "expected_tools": ["analyze_portfolio"],
        "category": "single_tool",
    },

    # --- predict_risk_score: single tool ---
    {
        "id": "risk-001",
        "query": "What's the risk score for NVDA, and why?",
        "expected_tools": ["predict_risk_score"],
        "category": "single_tool",
        "notes": "Answer should mention it's model-generated with a confidence value.",
    },
    {
        "id": "risk-002",
        "query": "Is JPM considered a high risk stock?",
        "expected_tools": ["predict_risk_score"],
        "category": "single_tool",
    },

    # --- search_financial_news: single tool ---
    {
        "id": "news-001",
        "query": "Any recent news on Tesla I should know about?",
        "expected_tools": ["search_financial_news"],
        "category": "single_tool",
    },
    {
        "id": "news-002",
        "query": "What's the general market sentiment around interest rates?",
        "expected_tools": ["search_financial_news"],
        "category": "single_tool",
        "notes": "Should search without a ticker filter (general/macro query).",
    },

    # --- multi-tool: the interesting cases ---
    {
        "id": "multi-001",
        "query": "Check my portfolio's tech exposure and NVDA's risk score together.",
        "expected_tools": ["analyze_portfolio", "predict_risk_score"],
        "category": "multi_tool",
        "notes": "Core 'agent, not wrapper' proof case — must call both tools.",
    },
    {
        "id": "multi-002",
        "query": "Give me AAPL's current price, its risk rating, and any recent news on it.",
        "expected_tools": ["get_stock_data", "predict_risk_score", "search_financial_news"],
        "category": "multi_tool",
        "notes": "Three-tool case.",
    },
    {
        "id": "multi-003",
        "query": "Is my portfolio's tech concentration justified given how risky NVDA and MSFT currently look?",
        "expected_tools": ["analyze_portfolio", "predict_risk_score"],
        "category": "multi_tool",
        "notes": "predict_risk_score should be called for BOTH tickers.",
    },

    # --- should NOT call a tool ---
    {
        "id": "no-tool-001",
        "query": "What does P/E ratio mean?",
        "expected_tools": [],
        "category": "no_tool",
        "notes": "General finance knowledge question, no data lookup needed.",
    },
    {
        "id": "no-tool-002",
        "query": "Thanks, that's all I needed.",
        "expected_tools": [],
        "category": "no_tool",
    },
]
