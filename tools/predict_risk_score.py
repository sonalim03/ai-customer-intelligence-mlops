"""
Tool: predict_risk_score

Loads the trained XGBoost model (see scripts/train_risk_model.py) and
predicts a risk bucket + confidence for a given ticker, using its
fundamentals from the DB.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import joblib
import numpy as np
from sqlalchemy import select
from data.db import ENGINE, stock_fundamentals

MODEL_PATH = Path(__file__).parent.parent / "data" / "risk_model.pkl"
ENCODER_PATH = Path(__file__).parent.parent / "data" / "sector_encoder.pkl"
FEATURES = ["beta", "pe_ratio", "market_cap_log", "dividend_yield", "sector_encoded"]

_model_bundle = None
_encoder = None


def _load():
    global _model_bundle, _encoder
    if _model_bundle is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                "Risk model not found. Run: python scripts/train_risk_model.py"
            )
        _model_bundle = joblib.load(MODEL_PATH)
        _encoder = joblib.load(ENCODER_PATH)
    return _model_bundle, _encoder


def predict_risk_score(ticker: str) -> dict:
    """
    Args:
        ticker: stock symbol, e.g. 'TSLA'

    Returns:
        dict with predicted risk_label (Low/Medium/High), confidence,
        and the fundamentals used to make the prediction.
    """
    ticker = ticker.upper().strip()
    bundle, encoder = _load()
    model, label_names = bundle["model"], bundle["label_names"]

    with ENGINE.connect() as conn:
        row = conn.execute(
            select(stock_fundamentals).where(stock_fundamentals.c.ticker == ticker)
        ).fetchone()

    if not row:
        return {"error": f"No fundamentals found for '{ticker}'. Has it been ingested?"}

    market_cap_log = np.log(max(row.market_cap or 1, 1))
    dividend_yield = row.dividend_yield or 0
    sector = row.sector or "Unknown"
    sector_encoded = encoder.transform([sector])[0] if sector in encoder.classes_ else -1

    features = np.array([[
        row.beta or 1.0, row.pe_ratio or 20.0, market_cap_log,
        dividend_yield, sector_encoded,
    ]])

    probs = model.predict_proba(features)[0]
    pred_idx = int(np.argmax(probs))

    return {
        "ticker": ticker,
        "risk_label": label_names[pred_idx],
        "confidence": round(float(probs[pred_idx]), 3),
        "probabilities": {label: round(float(p), 3) for label, p in zip(label_names, probs)},
        "based_on": {
            "beta": row.beta, "pe_ratio": row.pe_ratio,
            "sector": sector, "dividend_yield": dividend_yield,
        },
    }


if __name__ == "__main__":
    import json
    print(json.dumps(predict_risk_score("TSLA"), indent=2, default=str))
