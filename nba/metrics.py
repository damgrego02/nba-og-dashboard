"""Scoring a set of predictions."""
from __future__ import annotations

import numpy as np
import pandas as pd


def score(df: pd.DataFrame, prob_col: str = "home_win_prob") -> dict:
    """Accuracy, Brier score, log loss, and margin error for predictions vs results."""
    p = df[prob_col].clip(1e-4, 1 - 1e-4).to_numpy()
    y = df["home_win"].to_numpy()
    out = {
        "games": int(len(df)),
        "accuracy": float(np.mean((p >= 0.5) == (y == 1))),
        "brier": float(np.mean((p - y) ** 2)),
        "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
    }
    if "pred_margin" in df and prob_col == "home_win_prob":
        err = df["margin"] - df["pred_margin"]
        out["margin_mae"] = float(np.mean(np.abs(err)))
        out["margin_rmse"] = float(np.sqrt(np.mean(err ** 2)))
    return out


def calibration(df: pd.DataFrame, prob_col: str = "home_win_prob") -> pd.DataFrame:
    """When the model says 70%, does the favorite win about 70% of the time?"""
    fav_p = np.maximum(df[prob_col], 1 - df[prob_col])
    fav_won = np.where(df[prob_col] >= 0.5, df["home_win"], 1 - df["home_win"])
    bins = pd.cut(fav_p, [0.5, 0.6, 0.7, 0.8, 0.9, 1.0], include_lowest=True,
                  labels=["50-60%", "60-70%", "70-80%", "80-90%", "90-100%"])
    t = pd.DataFrame({"bucket": bins, "p": fav_p, "won": fav_won})
    return (t.groupby("bucket", observed=False)
             .agg(games=("won", "size"), predicted=("p", "mean"), actual=("won", "mean"))
             .round(3).reset_index())
