# CLP Live Monitor (Binance Futures)

A lightweight internal dashboard for monitoring **crowded leverage pressure** using:
- Funding Rate
- Open Interest history
- Price returns

It builds a heuristic signal: **CLP (Crowded Leverage Pressure)** and labels regimes:
Normal / Stress / Extreme.

✅ Auto-refresh: every 30 seconds  
✅ Snapshot history + export

## Run locally
```bash
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py