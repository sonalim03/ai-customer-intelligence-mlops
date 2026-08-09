"""
Train the risk-classification model used by tools/predict_risk_score.py.

Approach:
    We predict a stock's risk bucket (Low / Medium / High) from its
    FUNDAMENTALS ALONE (beta, P/E, market cap, dividend yield, sector) —
    not from volatility itself, since volatility is the thing we're
    trying to estimate for stocks we may not have price history for yet.

    Labels are derived from trailing 30-day realized volatility, bucketed
    into tertiles. This is a standard "proxy label" setup: volatility is
    our ground truth for past risk, fundamentals are what we'd know about
    a new/lesser-covered stock.

Note:
    With only ~10 tickers ingested, this is a toy training set — enough
    to prove the pipeline works end-to-end. For a real portfolio, expand
    WATCHLIST in ingest_stock_data.py to 50-100+ tickers (e.g. S&P 500
    constituents) before retraining, or the model will overfit badly.
    If fewer than 20 rows are available, this script trains on a
    synthetic fallback dataset so the rest of the pipeline is testable
    without waiting on data ingestion.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import joblib
from sqlalchemy import select
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import xgboost as xgb

from data.db import ENGINE, stock_fundamentals

MODEL_PATH = Path(__file__).parent.parent / "data" / "risk_model.pkl"
ENCODER_PATH = Path(__file__).parent.parent / "data" / "sector_encoder.pkl"
MIN_ROWS_FOR_REAL_TRAINING = 20

FEATURES = ["beta", "pe_ratio", "market_cap_log", "dividend_yield", "sector_encoded"]


def load_real_data() -> pd.DataFrame:
    with ENGINE.connect() as conn:
        rows = conn.execute(select(stock_fundamentals)).fetchall()
    df = pd.DataFrame(rows, columns=stock_fundamentals.columns.keys())
    return df.dropna(subset=["beta", "pe_ratio", "market_cap", "volatility_30d"])


def synthetic_fallback(n=300, seed=42) -> pd.DataFrame:
    """Generate a plausible synthetic fundamentals dataset for pipeline testing."""
    rng = np.random.default_rng(seed)
    sectors = ["Technology", "Financials", "Energy", "Healthcare", "Consumer Staples", "Industrials"]
    beta = rng.normal(1.1, 0.5, n).clip(0.2, 3.0)
    pe_ratio = rng.normal(22, 12, n).clip(3, 90)
    market_cap = rng.lognormal(24, 2, n)  # spread across small -> mega cap
    dividend_yield = rng.exponential(0.015, n).clip(0, 0.08)
    sector = rng.choice(sectors, n)

    # Ground-truth-ish volatility driven mostly by beta + inversely by market cap,
    # plus noise, so there's a learnable (not trivial) relationship.
    vol = (
        0.15
        + 0.12 * beta
        - 0.02 * np.log(market_cap / 1e9).clip(0, None)
        + rng.normal(0, 0.05, n)
    ).clip(0.05, 1.2)

    return pd.DataFrame({
        "beta": beta, "pe_ratio": pe_ratio, "market_cap": market_cap,
        "dividend_yield": dividend_yield, "sector": sector, "volatility_30d": vol,
    })


def prepare_features(df: pd.DataFrame, encoder: LabelEncoder = None, fit_encoder=False):
    df = df.copy()
    df["market_cap_log"] = np.log(df["market_cap"].clip(lower=1))
    df["dividend_yield"] = df["dividend_yield"].fillna(0)
    df["sector"] = df["sector"].fillna("Unknown")

    if fit_encoder:
        encoder = LabelEncoder().fit(df["sector"])
    df["sector_encoded"] = df["sector"].apply(
        lambda s: encoder.transform([s])[0] if s in encoder.classes_ else -1
    )
    return df, encoder


def main():
    df = load_real_data()
    if len(df) < MIN_ROWS_FOR_REAL_TRAINING:
        print(
            f"Only {len(df)} tickers with full fundamentals in DB "
            f"(need {MIN_ROWS_FOR_REAL_TRAINING}+). Training on synthetic "
            f"fallback data instead so the pipeline is testable end-to-end.\n"
            f"-> Expand WATCHLIST and re-run ingest_stock_data.py for a real model."
        )
        df = synthetic_fallback()

    df, encoder = prepare_features(df, fit_encoder=True)

    # Bucket volatility into tertiles -> Low / Medium / High risk labels
    df["risk_label"] = pd.qcut(df["volatility_30d"], q=3, labels=["Low", "Medium", "High"])

    X = df[FEATURES]
    y = LabelEncoder().fit_transform(df["risk_label"])
    label_names = ["Low", "Medium", "High"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=150, max_depth=4, learning_rate=0.08,
        objective="multi:softprob", num_class=3, random_state=42,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    print("\nEval on held-out test set:")
    print(classification_report(y_test, preds, target_names=label_names))

    joblib.dump({"model": model, "label_names": label_names}, MODEL_PATH)
    joblib.dump(encoder, ENCODER_PATH)
    print(f"\nSaved model -> {MODEL_PATH}")
    print(f"Saved sector encoder -> {ENCODER_PATH}")


if __name__ == "__main__":
    main()
