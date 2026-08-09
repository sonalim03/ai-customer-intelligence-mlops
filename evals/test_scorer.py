"""
Unit tests for evals/scorer.py — these run without any API key or live
agent call, so they belong in the fast CI test suite (Step 7), separate
from evals/run_evals.py which needs a real ANTHROPIC_API_KEY and hits
the live model.

Run: pytest evals/test_scorer.py -v
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from evals.scorer import score_tool_calls, score_groundedness, extract_numbers


def test_exact_tool_match():
    r = score_tool_calls(["get_stock_data"], ["get_stock_data"])
    assert r["exact_match"] is True
    assert r["f1"] == 1.0


def test_missed_tool_lowers_recall():
    r = score_tool_calls(["analyze_portfolio", "predict_risk_score"], ["analyze_portfolio"])
    assert r["exact_match"] is False
    assert r["recall"] == 0.5
    assert r["precision"] == 1.0


def test_extra_tool_lowers_precision():
    r = score_tool_calls(["get_stock_data"], ["get_stock_data", "search_financial_news"])
    assert r["precision"] == 0.5
    assert r["recall"] == 1.0


def test_no_tools_expected_and_none_called_is_exact_match():
    r = score_tool_calls([], [])
    assert r["exact_match"] is True
    assert r["f1"] == 1.0


def test_groundedness_passes_when_number_matches_tool_output():
    g = score_groundedness(
        "AAPL is at $195.0 with volatility 0.22",
        "ticker AAPL latest_close 195.0 volatility_30d 0.22",
    )
    assert g["grounded_ratio"] == 1.0
    assert g["ungrounded_numbers"] == []


def test_groundedness_catches_hallucinated_number():
    g = score_groundedness(
        "AAPL is trading at $999.0 today",
        "ticker AAPL latest_close 195.0",
    )
    assert g["grounded_ratio"] == 0.0
    assert "999.0" in g["ungrounded_numbers"]


def test_extract_numbers_includes_real_data_points():
    nums = extract_numbers("I checked 2 tools and found 3 stocks at $150.50")
    assert "150.50" in nums


def test_extract_numbers_known_limitation_small_prose_integers():
    """
    KNOWN LIMITATION, documented here rather than hidden: extract_numbers
    only filters values < 1 (e.g. bare "0" or decimals like "0.5" used in
    prose), so small prose integers like "2" in "2 tools" ARE currently
    picked up as if they were data points. In practice this makes
    groundedness scoring slightly pessimistic (it'll sometimes flag a
    prose number as "ungrounded" even though it was never meant to be a
    data claim) rather than falsely optimistic — pessimistic-by-default
    is the safer failure mode for a groundedness check, but it's worth
    fixing with a smarter regex (e.g. requiring a $ / % / decimal point)
    if false positives get noisy in real eval runs.
    """
    nums = extract_numbers("I checked 2 tools and found 3 stocks at $150.50")
    assert "2" in nums  # documents current behavior, not ideal behavior
    assert "3" in nums


def test_groundedness_with_no_numbers_returns_none_ratio():
    g = score_groundedness("Your portfolio looks reasonably diversified.", "")
    assert g["grounded_ratio"] is None
    assert g["checked"] == 0
