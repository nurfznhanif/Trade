"""Dashboard Trade — Streamlit, desain bersih (icon, tanpa emoji). Baca data/trade.db.

Jalanin:  streamlit run dashboard.py   ->  http://localhost:8501
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

st.set_page_config(page_title="Trade IDX", layout="wide")

# --- icon SVG (garis, warisi warna via currentColor) ---
IC_LOGO = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
           'stroke-linecap="round" stroke-linejoin="round"><path d="M22 7 13.5 15.5 8.5 10.5 2 17"/>'
           '<path d="M16 7h6v6"/></svg>')
IC_TARGET = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
             'stroke-linecap="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/>'
             '<circle cx="12" cy="12" r="1.6"/></svg>')

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
#MainMenu, header[data-testid="stHeader"], footer, [data-testid="stToolbar"] {display:none !important;}
.stAppDeployButton {display:none !important;}
html, body, [class*="css"], .stApp {font-family:'Inter',system-ui,sans-serif;}
.stApp {background:#f6f7f9;}
.block-container {padding-top:1.6rem; padding-bottom:3rem; max-width:1180px;}

.hdr {display:flex; align-items:center; justify-content:space-between;}
.hdr .brand {display:flex; align-items:center; gap:.5rem;}
.hdr .brand svg {width:26px; height:26px; color:#16a34a;}
.hdr h1 {font-size:1.7rem; font-weight:800; margin:0; letter-spacing:-.02em; color:#1a1f2e;}
.hdr .date {color:#6b7280; font-size:.82rem; font-weight:600;}
.sub {color:#8b93a1; font-size:.84rem; margin:.15rem 0 1.6rem;}

.tiles {display:grid; grid-template-columns:repeat(4,1fr); gap:.8rem; margin-bottom:1.9rem;}
.tile {background:#fff; border:1px solid #ecedf0; border-radius:16px; padding:1rem 1.2rem;}
.tile .n {font-size:2rem; font-weight:800; line-height:1; color:#1a1f2e;}
.tile .l {color:#8b93a1; font-size:.74rem; font-weight:600; text-transform:uppercase;
          letter-spacing:.05em; margin-top:.45rem; display:flex; align-items:center;}
.tile.buy .n {color:#16a34a;} .tile.sell .n {color:#dc2626;}
.dot {display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px;}
.dot.buy {background:#16a34a;} .dot.hold {background:#9aa2b1;} .dot.sell {background:#dc2626;}

.sec {display:flex; align-items:center; gap:.45rem; font-size:1.1rem; font-weight:700;
      color:#1a1f2e; margin:.3rem 0 1rem;}
.sec svg {width:19px; height:19px; color:#16a34a;}
.sec small {color:#9099a6; font-weight:500; font-size:.8rem;}

.grid {display:grid; grid-template-columns:repeat(auto-fill,minmax(224px,1fr)); gap:.85rem;}
.card {background:#fff; border:1px solid #ecedf0; border-left:4px solid #16a34a;
       border-radius:16px; padding:1rem 1.15rem; transition:.15s;}
.card:hover {box-shadow:0 8px 24px rgba(20,30,50,.07); transform:translateY(-2px);}
.card .r1 {display:flex; justify-content:space-between; align-items:center;}
.card .tk {font-weight:800; font-size:1.08rem; color:#1a1f2e;}
.card .badge {background:#dcfce7; color:#15803d; font-size:.68rem; font-weight:700;
              padding:.15rem .55rem; border-radius:999px;}
.card .px {font-size:1.55rem; font-weight:800; color:#1a1f2e; margin:.45rem 0 .1rem;}
.card .bar {height:5px; background:#eef0f3; border-radius:99px; overflow:hidden; margin:.55rem 0 .4rem;}
.card .bar span {display:block; height:100%; background:#16a34a;}
.card .stats {color:#6b7280; font-size:.78rem;}
.card .lvl {display:flex; gap:.9rem; font-size:.85rem; margin-top:.55rem; font-weight:700;}
.card .lvl b {font-size:.6rem; letter-spacing:.05em; opacity:.65; margin-right:3px; font-weight:700;}
.card .lvl .s {color:#dc2626;} .card .lvl .t {color:#16a34a;}
.card .why {color:#a3a9b5; font-size:.71rem; margin-top:.55rem; line-height:1.4;}

.stTabs [data-baseweb="tab-list"] {gap:.3rem;}
.stTabs [data-baseweb="tab"] {font-weight:600;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data(ttl=300)
def q(sql, params=None):
    return pd.read_sql_query(sql, get_connection(), params=params)


def rp(v):
    try:
        return "Rp" + f"{int(round(float(v))):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def code(t):
    return t.replace(".JK", "")


sig = q("SELECT * FROM signals")
if sig.empty:
    st.warning("Belum ada sinyal — jalanin `python scripts/generate_signals.py` dulu.")
    st.stop()

nbuy = int((sig["action"] == "BUY").sum())
nhold = int((sig["action"] == "HOLD").sum())
nsell = int((sig["action"] == "SELL").sum())
nfocus = len(q("SELECT ticker FROM focus_list"))
asof = str(sig["asof"].max())

st.markdown(
    f'<div class="hdr"><div class="brand">{IC_LOGO}<h1>Trade</h1></div>'
    f'<span class="date">Data per {asof}</span></div>'
    f'<div class="sub">Dashboard swing IDX · momentum + sentimen + fundamental · '
    f'bukan nasihat keuangan</div>', unsafe_allow_html=True)

st.markdown(
    f'<div class="tiles">'
    f'<div class="tile buy"><div class="n">{nbuy}</div>'
    f'<div class="l"><span class="dot buy"></span>Sinyal Beli</div></div>'
    f'<div class="tile"><div class="n">{nhold}</div>'
    f'<div class="l"><span class="dot hold"></span>Tahan</div></div>'
    f'<div class="tile sell"><div class="n">{nsell}</div>'
    f'<div class="l"><span class="dot sell"></span>Jual / Hindari</div></div>'
    f'<div class="tile"><div class="n">{nfocus}</div>'
    f'<div class="l">Saham dipantau</div></div>'
    f'</div>', unsafe_allow_html=True)


def card(r):
    reasons = " · ".join(json.loads(r["reasons"])) if r["reasons"] else ""
    w = max(0.0, min(float(r["score"]) / 3.0, 1.0)) * 100
    rsi = f'{r["rsi"]:.0f}' if pd.notna(r["rsi"]) else "—"
    return (
        f'<div class="card"><div class="r1"><span class="tk">{code(r["ticker"])}</span>'
        f'<span class="badge">BUY</span></div>'
        f'<div class="px">{rp(r["close"])}</div>'
        f'<div class="bar"><span style="width:{w:.0f}%"></span></div>'
        f'<div class="stats">skor {r["score"]:.2f} &nbsp;·&nbsp; RSI {rsi} '
        f'&nbsp;·&nbsp; sentimen {r["sent"]:+.2f}</div>'
        f'<div class="lvl"><span class="s"><b>STOP</b>{rp(r["stop"])}</span>'
        f'<span class="t"><b>TARGET</b>{rp(r["target"])}</span></div>'
        f'<div class="why">{reasons}</div></div>')


buys = sig[sig["action"] == "BUY"].sort_values("score", ascending=False)
top = buys.head(12)
extra = f"menampilkan 12 dari {len(buys)}" if len(buys) > 12 else ""
st.markdown(f'<div class="sec">{IC_TARGET} Sinyal Beli Hari Ini <small>{extra}</small></div>',
            unsafe_allow_html=True)
st.markdown(f'<div class="grid">{"".join(card(r) for _, r in top.iterrows())}</div>',
            unsafe_allow_html=True)

st.write("")
st.write("")
t_all, t_sent, t_fund, t_chart, t_paper = st.tabs([
    ":material/format_list_bulleted: Semua Sinyal",
    ":material/newspaper: Sentimen",
    ":material/account_balance: Fundamental",
    ":material/show_chart: Chart",
    ":material/wallet: Paper"])

with t_all:
    acts = st.multiselect("Filter", ["BUY", "HOLD", "SELL"], default=["BUY", "SELL"])
    d = sig[sig["action"].isin(acts)].copy().sort_values("score", ascending=False)
    d["saham"] = d["ticker"].map(code)
    d["alasan"] = d["reasons"].apply(lambda r: " · ".join(json.loads(r)) if r else "")
    st.dataframe(
        d[["saham", "action", "score", "close", "rsi", "sent", "n_news", "stop", "target", "alasan"]],
        hide_index=True, use_container_width=True, height=460,
        column_config={
            "action": "aksi",
            "score": st.column_config.ProgressColumn("skor", min_value=0, max_value=3, format="%.2f"),
            "close": st.column_config.NumberColumn("harga", format="Rp %.0f"),
            "rsi": st.column_config.NumberColumn("RSI", format="%.0f"),
            "sent": st.column_config.NumberColumn("sentimen", format="%+.2f"),
            "n_news": "berita",
            "stop": st.column_config.NumberColumn("stop", format="Rp %.0f"),
            "target": st.column_config.NumberColumn("target", format="Rp %.0f"),
        })

with t_sent:
    since = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat(timespec="seconds")
    lb = q("SELECT n.ticker AS saham, i.name AS nama, COUNT(*) AS berita, "
           "ROUND(AVG(n.sent_score),2) AS sentimen "
           "FROM news n JOIN instruments i ON i.ticker=n.ticker "
           "WHERE n.sent_score IS NOT NULL AND (n.published IS NULL OR n.published>=?) "
           "GROUP BY n.ticker HAVING berita>=3 ORDER BY sentimen DESC", (since,))
    conf = {"sentimen": st.column_config.NumberColumn("sentimen", format="%+.2f")}
    a, b = st.columns(2)
    a.markdown(":material/trending_up: **Paling positif**")
    a.dataframe(lb.head(10), hide_index=True, use_container_width=True, column_config=conf)
    b.markdown(":material/trending_down: **Paling negatif**")
    b.dataframe(lb.tail(10).iloc[::-1], hide_index=True, use_container_width=True, column_config=conf)
    st.divider()
    tk = st.selectbox("Berita per saham", sorted(sig["ticker"].unique()))
    st.dataframe(q("SELECT published AS terbit, sent_score AS skor, source AS sumber, title AS judul "
                   "FROM news WHERE ticker=? ORDER BY published DESC LIMIT 25", (tk,)),
                 hide_index=True, use_container_width=True)

with t_fund:
    f = q("SELECT * FROM fundamentals")
    if f.empty:
        st.info("Belum ada data fundamental — jalanin `scripts/fetch_fundamentals.py`.")
    else:
        f["bendera merah"] = f.apply(lambda r: "; ".join(red_flags(r.to_dict())), axis=1)
        f["saham"] = f["ticker"].map(code)
        st.dataframe(f[["saham", "per", "pbv", "roe", "der", "div_yield", "margin", "bendera merah"]],
                     hide_index=True, use_container_width=True, height=460)

with t_chart:
    tk = st.selectbox("Pilih saham", sorted(sig["ticker"].unique()), key="chart")
    px = q("SELECT date, close FROM prices WHERE ticker=? ORDER BY date", (tk,))
    if px.empty:
        st.info("Belum ada data harga.")
    else:
        px = px.set_index("date")
        px["MA20"] = px["close"].rolling(20).mean()
        px["MA50"] = px["close"].rolling(50).mean()
        st.line_chart(px.tail(180), color=["#1a1f2e", "#16a34a", "#f59e0b"])

with t_paper:
    csv = DATA_DIR / "paper_open_positions.csv"
    if csv.exists():
        st.markdown(":material/push_pin: **Posisi paper terbuka**")
        st.dataframe(pd.read_csv(csv), hide_index=True, use_container_width=True)
    else:
        st.info("Belum ada posisi paper — jalanin `scripts/paper_run.py`.")
