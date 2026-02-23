from __future__ import annotations

import numpy as np
import pandas as pd


def add_returns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ret"] = np.log(out["Close"]).diff()
    out["abs_ret"] = out["ret"].abs()
    return out


def add_oi_change(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["oi_chg_pct"] = out["openInterest"].pct_change()
    return out


def rolling_zscore(s: pd.Series, window: int = 120) -> pd.Series:
    mu = s.rolling(window).mean()
    sd = s.rolling(window).std(ddof=0)
    return (s - mu) / sd


def add_zscores(df: pd.DataFrame, zwin: int = 120) -> pd.DataFrame:
    out = df.copy()
    out["z_funding"] = rolling_zscore(out["fundingRate"], window=zwin)
    out["z_oi"] = rolling_zscore(out["oi_chg_pct"], window=zwin)
    out["z_absret"] = rolling_zscore(out["abs_ret"], window=zwin)
    return out