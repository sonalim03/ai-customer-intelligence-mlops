"""
Scoring functions used by evals/run_evals.py.

Two things get scored per query:
1. Tool-call accuracy — did the agent call the expected tool(s), no more
   and no fewer? (set comparison, order doesn't matter)
2. Groundedness — do the numbers in the agent's final answer actually
   appear somewhere in the tool outputs it received? A rough but useful
   proxy for "did it hallucinate a number instead of using the tool result."
"""
import re
from typing import List


def score_tool_calls(expected: List[str], actual: List[str]) -> dict:
    """
    Set-based comparison of expected vs. actually-called tool names.
    Returns precision, recall, F1, and whether it was an exact match.
    """
    expected_set, actual_set = set(expected), set(actual)

    if not expected_set and not actual_set:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "exact_match": True}

    true_positives = len(expected_set & actual_set)
    precision = true_positives / len(actual_set) if actual_set else 0.0
    recall = true_positives / len(expected_set) if expected_set else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0 else 0.0
    )

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "exact_match": expected_set == actual_set,
    }


_NUMBER_PATTERN = re.compile(r"-?\d[\d,]*\.?\d*%?")


def extract_numbers(text: str) -> List[str]:
    """Pull out numeric-looking tokens (prices, percentages, ratios) from text."""
    raw = _NUMBER_PATTERN.findall(text)
    # normalize: strip commas/percent signs, drop tiny numbers like "1" or "2"
    # that are likely to just be prose (e.g. "2 tools", "3 stocks") not data
    cleaned = []
    for tok in raw:
        norm = tok.replace(",", "").rstrip("%")
        try:
            val = float(norm)
        except ValueError:
            continue
        if abs(val) >= 1:  # filters out noise like bare "1" or "2" in prose
            cleaned.append(norm)
    return cleaned


def score_groundedness(final_answer: str, tool_outputs_text: str) -> dict:
    """
    Check what fraction of numbers in the final answer also appear
    (as a substring match) somewhere in the concatenated tool outputs.

    This is a heuristic, not perfect (numbers can coincidentally match,
    or be legitimately derived/rounded from tool data) — treat it as a
    signal to spot-check manually, not an infallible ground truth.
    """
    answer_numbers = extract_numbers(final_answer)
    if not answer_numbers:
        return {"grounded_ratio": None, "ungrounded_numbers": [], "checked": 0}

    ungrounded = [n for n in answer_numbers if n not in tool_outputs_text]
    grounded_ratio = 1 - (len(ungrounded) / len(answer_numbers))

    return {
        "grounded_ratio": round(grounded_ratio, 3),
        "ungrounded_numbers": ungrounded,
        "checked": len(answer_numbers),
    }
