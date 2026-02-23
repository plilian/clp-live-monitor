from __future__ import annotations

import os
from datetime import datetime, timezone

import pandas as pd

SNAPSHOT_FILE = "snapshots.csv"


def append_snapshot(watch_df: pd.DataFrame) -> None:
    if watch_df is None or watch_df.empty:
        return

    snap = watch_df.copy()
    snap["timestamp"] = datetime.now(timezone.utc)

    if os.path.exists(SNAPSHOT_FILE):
        old = pd.read_csv(SNAPSHOT_FILE)
        snap = pd.concat([old, snap], ignore_index=True)

    snap.to_csv(SNAPSHOT_FILE, index=False)


def load_snapshots() -> pd.DataFrame:
    if not os.path.exists(SNAPSHOT_FILE):
        return pd.DataFrame()

    df = pd.read_csv(SNAPSHOT_FILE, parse_dates=["timestamp"])
    return df.sort_values("timestamp")