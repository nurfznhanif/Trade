"""Dashboard Trade — Streamlit. Baca data/trade.db langsung.

Jalanin:  streamlit run dashboard.py   (buka di browser: http://localhost:8501)
"""
import json
import pathlib
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from trade.config import DATA_DIR          # noqa: E402
from trade.db import get_connection        # noqa: E402
from trade.fundamentals import red_flags   # noqa: E402

st.set_page_config(page_title="Trade IDX", page_icon="📈", layout="wide")


@st.cache_data(ttl=300)
def q(sql, params=None):
    return pd.read_sql_query(sql, get_connection(), params=params)


def flag(m):
    return "🇮🇩" if m == "IDX" else "🇺🇸"


st.title("📈 Trade — Dashboard Saham IDX")
st.caption("Alat bantu keputusan swing (momentum + sentimen + fundamental). "
           "Bukan nasihat keuangan.")

sig = q("SELECT * FROM signals")
if sig.empty:
    st.warning("Belum ada sinyal — jalanin `python scripts/generate_signals.py` dulu.")
    st.stop()

m = st.columns(5)
m[0].metric("Focus list", len(q("SELECT ticker FROM focus_list")))
m[1].metric("🟢 BUY", int((sig.action == "BUY").sum()))
m[2].metric("⚪ HOLD", int((sig.action == "HOLD").sum()))
m[3].metric("🔴 SELL", int((sig.action == "SELL").sum()))
m[4].metric("Data per", str(sig["asof"].max()))

t_sig, t_sent, t_fund, t_chart, t_paper = st.tabs(
    ["📈 Sinyal", "🧠 Sentimen", "💎 Fundamental", "📊 Chart", "📝 Paper"])

with t_sig:
    acts = st.multiselect("Filter aksi", ["BUY", "HOLD", "SELL"], default=["BUY"])
    d = sig[sig.action.isin(acts)].copy().sort_values("score", ascending=False)
    d["🏳"] = d.market.map(flag)
    d["alasan"] = d.reasons.apply(lambda r: " · ".join(json.loads(r)) if r else "")
    cols = {"ticker": "ticker", "action": "aksi", "score": "skor", "close": "harga",
            "rsi": "RSI", "sent": "sentimen", "n_news": "#berita",
            "stop": "stop", "target": "target"}
    show = d[["🏳"] + list(cols)].rename(columns=cols)
    show["alasan"] = d["alasan"].values
    st.dataframe(show, use_container_width=True, hide_index=True, height=520)

with t_sent:
    since = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat(timespec="seconds")
    lb = q("""SELECT n.ticker, i.name, i.market, COUNT(*) AS n_news,
                     ROUND(AVG(n.sent_score), 2) AS avg_sent
              FROM news n JOIN instruments i ON i.ticker = n.ticker
              WHERE n.sent_score IS NOT NULL AND (n.published IS NULL OR n.published >= ?)
              GROUP BY n.ticker HAVING n_news >= 3 ORDER BY avg_sent DESC""", (since,))
    a, b = st.columns(2)
    a.subheader("🟢 Sentimen positif")
    a.dataframe(lb.head(12), hide_index=True, use_container_width=True)
    b.subheader("🔴 Sentimen negatif")
    b.dataframe(lb.tail(12).iloc[::-1], hide_index=True, use_container_width=True)
    st.divider()
    tk = st.selectbox("Berita per saham", sorted(sig.ticker.unique()))
    st.dataframe(q("SELECT published, sent_score, source, title FROM news "
                   "WHERE ticker = ? ORDER BY published DESC LIMIT 25", (tk,)),
                 hide_index=True, use_container_width=True)

with t_fund:
    f = q("SELECT * FROM fundamentals")
    if f.empty:
        st.info("Belum ada data fundamental — jalanin `scripts/fetch_fundamentals.py`.")
    else:
        f["⚠️ bendera merah"] = f.apply(lambda r: "; ".join(red_flags(r.to_dict())), axis=1)
        st.dataframe(f[["ticker", "per", "pbv", "roe", "der", "div_yield",
                        "margin", "⚠️ bendera merah"]],
                     use_container_width=True, hide_index=True, height=520)

with t_chart:
    tk = st.selectbox("Pilih saham", sorted(sig.ticker.unique()), key="chart")
    px = q("SELECT date, close FROM prices WHERE ticker = ? ORDER BY date", (tk,))
    if px.empty:
        st.info("Belum ada data harga.")
    else:
        px = px.set_index("date")
        px["MA20"] = px["close"].rolling(20).mean()
        px["MA50"] = px["close"].rolling(50).mean()
        st.line_chart(px.tail(180))

with t_paper:
    csv = DATA_DIR / "paper_open_positions.csv"
    if csv.exists():
        st.subheader("📌 Posisi paper terbuka")
        st.dataframe(pd.read_csv(csv), hide_index=True, use_container_width=True)
    else:
        st.info("Belum ada posisi paper — jalanin `scripts/paper_run.py`.")
