"""
Quick CLI to manually chat with the FinSight agent.

Usage:
    python agent/run.py
    (then type questions, Ctrl+C to quit)

Requires ANTHROPIC_API_KEY set (see .env.example) and the DB/model/
Chroma store already populated (Steps 1-2).
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from agent.graph import build_agent, ask

EXAMPLE_QUERIES = [
    "What's AAPL's current price and volatility?",
    "Am I overexposed to any sector in my portfolio?",
    "What's the risk score for NVDA, and why?",
    "Any recent news on Tesla I should know about?",
    "Check my portfolio's tech exposure and NVDA's risk score together.",
]


def main():
    print("FinSight agent — type a question, or 'examples' to see sample "
          "queries, Ctrl+C to quit.\n")
    agent = build_agent()

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() == "examples":
            for q in EXAMPLE_QUERIES:
                print(f"  - {q}")
            continue

        response = ask(agent, user_input)
        print(f"FinSight: {response}\n")


if __name__ == "__main__":
    main()
