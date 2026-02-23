from __future__ import annotations

import pandas as pd


def current_regime_streak(df: pd.DataFrame) -> dict:

    if df is None or df.empty or "regime" not in df.columns:
        return {"current_regime": "NA", "streak_bars": 0}

    r = df["regime"].astype(str).values
    cur = r[-1]

    streak = 1
    for i in range(len(r) - 2, -1, -1):
        if r[i] == cur:
            streak += 1
        else:
            break

    return {"current_regime": cur, "streak_bars": streak}


def regime_time_share(df: pd.DataFrame, lookback: int = 300) -> pd.DataFrame:

    if df is None or df.empty or "regime" not in df.columns:
        return pd.DataFrame(columns=["regime", "count", "pct"])

    x = df.tail(lookback).copy()
    vc = x["regime"].value_counts(dropna=False)

    out = vc.reset_index()
    out.columns = ["regime", "count"]
    out["pct"] = out["count"] / out["count"].sum() * 100.0
    return out