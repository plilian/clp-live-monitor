from __future__ import annotations

import pandas as pd


def compute_clp(
    df: pd.DataFrame,
    w_funding: float = 0.5,
    w_oi: float = 0.3,
    w_absret: float = 0.2,
) -> pd.DataFrame:
    out = df.copy()
    out["clp"] = (
        w_funding * out["z_funding"]
        + w_oi * out["z_oi"]
        + w_absret * out["z_absret"]
    )
    return out


def compute_thresholds(
    series: pd.Series,
    mode: str,
    p_stress: float = 0.85,
    p_extreme: float = 0.95,
    k_stress: float = 1.0,
    k_extreme: float = 2.0,
) -> tuple[float, float]:
    x = series.dropna().astype(float)
    if len(x) < 80:
        # fallback, avoids "everything Normal" on short history
        return 0.8, 1.8

    if mode == "percentile":
        return float(x.quantile(p_stress)), float(x.quantile(p_extreme))

    if mode == "std":
        mu = float(x.mean())
        sd = float(x.std(ddof=0))
        return mu + k_stress * sd, mu + k_extreme * sd

    raise ValueError("mode must be one of: percentile, std")


def add_regime(df: pd.DataFrame, stress_thr: float, extreme_thr: float) -> pd.DataFrame:
    out = df.copy()
    out["regime"] = "Normal"
    out.loc[out["clp"] > stress_thr, "regime"] = "Stress"
    out.loc[out["clp"] > extreme_thr, "regime"] = "Extreme"
    return out