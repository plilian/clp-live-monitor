from __future__ import annotations

import numpy as np
import pandas as pd


def crowding_index(clp_series: pd.Series, top_pct: float = 0.10, min_n: int = 3) -> float:
    """
    Robust crowding metric that works even when CLP can be negative.

    crowding_index = mean(|CLP| of top X%) / mean(|CLP|)

    - Uses absolute CLP to avoid sign cancellations
    - Works with small watchlists (min_n default=3)
    """
    x = clp_series.dropna().astype(float).values
    if len(x) < min_n:
        return float("nan")

    x = np.abs(x)
    denom = float(np.mean(x))
    if denom <= 0:
        return float("nan")

    thr = np.percentile(x, 100 * (1 - top_pct))
    heavy = x[x >= thr]
    if len(heavy) == 0:
        return float("nan")

    return float(np.mean(heavy) / denom)