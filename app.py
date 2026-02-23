from __future__ import annotations

import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

from src.binance_api import build_merged_frame
from src.features import add_returns, add_oi_change, add_zscores
from src.scoring import compute_clp, compute_thresholds, add_regime
from src.risk import crowding_index
from src.state import append_snapshot, load_snapshots
from src.viz import fig_price_and_clp, fig_components
from src.insights import current_regime_streak, regime_time_share

WATERMARK = "Parham Lilian"


@st.cache_data(ttl=30)
def compute_one(
    symbol: str,
    interval: str,
    lookback: int,
    zwin: int,
    wF: float,
    wOI: float,
    wR: float,
    thr_mode: str,
    p_stress: float,
    p_extreme: float,
    k_stress: float,
    k_extreme: float,
):
    df = build_merged_frame(symbol=symbol, interval=interval, lookback_limit=lookback)
    df = add_returns(df)
    df = add_oi_change(df)
    df = add_zscores(df, zwin=zwin)
    df = compute_clp(df, w_funding=wF, w_oi=wOI, w_absret=wR)
    df = df.dropna().copy()

    if thr_mode == "percentile":
        stress_thr, extreme_thr = compute_thresholds(
            df["clp"], "percentile", p_stress=p_stress, p_extreme=p_extreme
        )
    else:
        stress_thr, extreme_thr = compute_thresholds(
            df["clp"], "std", k_stress=k_stress, k_extreme=k_extreme
        )

    df = add_regime(df, stress_thr=stress_thr, extreme_thr=extreme_thr)
    latest = df.iloc[-1]

    snap = {
        "symbol": symbol,
        "price": float(latest["Close"]),
        "funding": float(latest.get("fundingRate", float("nan"))),
        "oi": float(latest.get("openInterest", float("nan"))),
        "clp": float(latest["clp"]),
        "regime": str(latest["regime"]),
        "stress_thr": float(stress_thr),
        "extreme_thr": float(extreme_thr),
    }
    return df, snap


def main():
    st.set_page_config(page_title="CLP Live Monitor", layout="wide")

    st_autorefresh(interval=30_000, key="clp_refresh")

    st.title("CLP Live Monitor (Binance Futures)")
    st.caption("Funding + Open Interest + Price → crowding/leverage pressure. Auto-updates every 30 seconds.")
    st.info("⏱ Auto-refresh ON — updates every 30 seconds (public endpoints, no API key).")

    if "prev_regimes" not in st.session_state:
        st.session_state["prev_regimes"] = {}
    if "flip_log" not in st.session_state:
        st.session_state["flip_log"] = []

    with st.sidebar:
        st.header("Mode")
        simple_mode = st.toggle("Simple Mode (beginner-friendly)", value=True)

        st.divider()
        st.header("Watchlist")

        wF, wOI, wR = 0.5, 0.3, 0.2

        if simple_mode:
            preset = st.selectbox(
                "Preset",
                ["Crypto Majors", "Alt Mix"],
                index=0
            )

            preset_map = {
                "Crypto Majors": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
                "Alt Mix": ["SOLUSDT", "XRPUSDT", "BNBUSDT"],
            }
            symbols = preset_map[preset]

            interval = st.selectbox("Interval", ["15m", "1h", "4h"], index=1)
            lookback = st.slider("Lookback candles", 200, 800, 500, 50)

            sensitivity = st.select_slider("Sensitivity", ["Low", "Medium", "High"], value="Medium")
            if sensitivity == "Low":
                zwin = 180
                thr_mode = "percentile"
                p_stress, p_extreme = 0.90, 0.97
                k_stress, k_extreme = 1.2, 2.4
            elif sensitivity == "High":
                zwin = 90
                thr_mode = "percentile"
                p_stress, p_extreme = 0.80, 0.92
                k_stress, k_extreme = 0.9, 1.8
            else:
                zwin = 120
                thr_mode = "percentile"
                p_stress, p_extreme = 0.85, 0.95
                k_stress, k_extreme = 1.0, 2.0

            st.caption("Simple Mode hides advanced knobs but keeps the same signal + insights.")

        else:
            symbols = st.multiselect(
                "Symbols",
                ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"],
                default=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            )

            interval = st.selectbox("Interval", ["5m", "15m", "1h", "4h", "1d"], index=2)
            lookback = st.slider("Lookback candles", 200, 800, 500, 50)
            zwin = st.slider("Z-score window", 60, 240, 120, 10)

            st.divider()
            st.subheader("CLP weights")
            wF = st.slider("w(Funding)", 0.0, 1.0, 0.50, 0.05)
            wOI = st.slider("w(ΔOI%)", 0.0, 1.0, 0.30, 0.05)
            wR = st.slider("w(|return|)", 0.0, 1.0, 0.20, 0.05)

            s = wF + wOI + wR
            if s <= 0:
                wF, wOI, wR = 0.5, 0.3, 0.2
            else:
                wF, wOI, wR = wF / s, wOI / s, wR / s

            st.divider()
            st.subheader("Auto thresholds")
            thr_mode_ui = st.radio("Mode", ["Percentiles", "Mean±Std"], index=0)
            thr_mode = "percentile" if thr_mode_ui == "Percentiles" else "std"

            if thr_mode == "percentile":
                p_stress = st.slider("Stress percentile", 0.60, 0.95, 0.85, 0.01)
                p_extreme = st.slider("Extreme percentile", 0.70, 0.99, 0.95, 0.01)
                k_stress, k_extreme = 1.0, 2.0
            else:
                k_stress = st.slider("Stress = mean + k·std", 0.5, 3.0, 1.0, 0.1)
                k_extreme = st.slider("Extreme = mean + k·std", 1.0, 5.0, 2.0, 0.1)
                p_stress, p_extreme = 0.85, 0.95

        st.divider()
        keep_history = st.checkbox("Log snapshots to history", value=True)

    tabs = st.tabs(["Dashboard", "History", "About"])

    snapshots = []
    frames = {}

    for sym in symbols:
        try:
            df, snap = compute_one(
                sym, interval, lookback, zwin,
                wF, wOI, wR,
                thr_mode, p_stress, p_extreme,
                k_stress, k_extreme
            )
            frames[sym] = df
            snapshots.append(snap)
        except Exception as e:
            snapshots.append({"symbol": sym, "error": str(e)})

    watch = pd.DataFrame(snapshots)

    with tabs[0]:
        st.subheader("Cross-Asset Snapshot")

        if "error" in watch.columns and watch["error"].notna().any():
            st.warning("Some symbols failed to load:")
            st.dataframe(watch[watch["error"].notna()][["symbol", "error"]], use_container_width=True)

        good = watch.drop(columns=["error"], errors="ignore")
        if good.empty or ("clp" not in good.columns):
            st.error("No valid data loaded. Try fewer symbols or a different interval.")
            return

        good = good.sort_values("clp", ascending=False).reset_index(drop=True)
        good["rank"] = range(1, len(good) + 1)

        ci = crowding_index(good["clp"])
        colA, colB, colC = st.columns(3)
        colA.metric("Market Avg CLP", f"{good['clp'].mean():.2f}")
        colB.metric("Crowding Index", f"{ci:.2f}" if pd.notna(ci) else "NA", help="mean(|CLP| top10%) / mean(|CLP|)")
        colC.metric("Tracked Symbols", str(len(good)))
        extreme = good[good["clp"] > good["extreme_thr"]]
        stress = good[(good["clp"] > good["stress_thr"]) & (good["clp"] <= good["extreme_thr"])]

        if not extreme.empty:
            st.error("🚨 EXTREME crowding: " + ", ".join(extreme["symbol"].tolist()))
        elif not stress.empty:
            st.warning("⚠️ STRESS detected in: " + ", ".join(stress["symbol"].tolist()))
        else:
            st.success("✅ No stress flags right now (based on auto thresholds).")
        changes = []
        for _, r in good.iterrows():
            sym = r["symbol"]
            prev = st.session_state["prev_regimes"].get(sym)
            cur = r["regime"]
            if prev is not None and prev != cur:
                msg = f"{sym}: {prev} → {cur}"
                changes.append(msg)
                st.session_state["flip_log"].append(msg)
            st.session_state["prev_regimes"][sym] = cur

        if changes:
            st.warning("Regime shift detected:\n" + "\n".join(changes))

        st.dataframe(
            good[["rank", "symbol", "price", "clp", "regime", "funding", "oi"]],
            use_container_width=True
        )

        if keep_history:
            append_snapshot(good)

        st.divider()

        if st.button("Export current snapshot (CSV)"):
            good.to_csv("latest_snapshot.csv", index=False)
            st.success("Saved as latest_snapshot.csv (in app working directory).")

        st.divider()
        focus = st.selectbox("Focus symbol", options=good["symbol"].tolist(), index=0)

        df_focus = frames.get(focus)
        if df_focus is None or df_focus.empty:
            st.error("No data for selected focus symbol.")
            return

        row = good[good["symbol"] == focus].iloc[0]
        stress_thr = float(row["stress_thr"])
        extreme_thr = float(row["extreme_thr"])

        left, right = st.columns([2, 1])
        with left:
            st.plotly_chart(fig_price_and_clp(df_focus, stress_thr, extreme_thr), use_container_width=True)
        with right:
            st.plotly_chart(fig_components(df_focus.tail(300)), use_container_width=True)
        st.divider()
        st.subheader("Regime Time-in-State")

        streak = current_regime_streak(df_focus)
        bars = int(streak["streak_bars"])

        interval_to_min = {"5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}
        mins = interval_to_min.get(interval, 60)

        st.metric("Current regime streak", f"{bars} bars (~{bars * mins} min)")

        share = regime_time_share(df_focus, lookback=300)
        st.dataframe(share, use_container_width=True)
        st.divider()
        st.subheader("Top Contributor (Why is CLP high right now?)")

        last = df_focus.iloc[-1]
        c_f = wF * float(last["z_funding"])
        c_oi = wOI * float(last["z_oi"])
        c_r = wR * float(last["z_absret"])

        comp = pd.DataFrame({
            "component": ["Funding", "Open Interest Δ%", "|Return|"],
            "contribution": [c_f, c_oi, c_r],
            "z_value": [float(last["z_funding"]), float(last["z_oi"]), float(last["z_absret"])],
        })

        winner = comp.iloc[comp["contribution"].abs().argmax()]["component"]
        st.write(f"**Main driver now:** {winner}")

        st.bar_chart(comp.set_index("component")["contribution"])
        st.dataframe(comp, use_container_width=True)

        if st.session_state["flip_log"]:
            st.subheader("Recent regime flips")
            st.write(st.session_state["flip_log"][-8:])

        st.caption(f"© {WATERMARK} — CLP is a heuristic monitoring index (not financial advice).")

    with tabs[1]:
        st.subheader("Snapshot History (from snapshots.csv)")
        hist = load_snapshots()

        if hist.empty:
            st.info("No history yet. Enable 'Log snapshots to history' and wait a few refresh cycles.")
        else:
            pivot = hist.pivot_table(index="timestamp", columns="symbol", values="clp")
            st.line_chart(pivot.tail(150), use_container_width=True)

            st.divider()
            st.caption("Raw snapshot rows (tail):")
            st.dataframe(hist.tail(200), use_container_width=True)

    with tabs[2]:
        st.header("About")
        st.write(
            """
Built by **Parham Lilian**.

This dashboard uses Binance USD-M Futures public endpoints (no API key) and refreshes every **30 seconds**.
It is designed for **monitoring / regime detection** rather than prediction.
            """
        )
        st.link_button("Connect on LinkedIn", "https://linkedin.com/in/parhamlilian")
        st.write("Disclaimer: Analytics only. Not financial advice.")


if __name__ == "__main__":
    main()