"""Dashboard Trade — Streamlit. Keputusan Claude (LLM) di depan, sinyal mesin jadi pembanding.

Jalanin:  streamlit run dashboard.py  ->  http://localhost:8501
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
from trade.fundamentals import red_flags, sanitize   # noqa: E402

st.set_page_config(page_title="Trade IDX", layout="wide")

IC_LOGO = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
           'stroke-linecap="round" stroke-linejoin="round"><path d="M22 7 13.5 15.5 8.5 10.5 2 17"/>'
           '<path d="M16 7h6v6"/></svg>')

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

.tiles {display:grid; grid-template-columns:repeat(4,1fr); gap:.8rem; margin-bottom:1.7rem;}
.tile {background:#fff; border:1px solid #ecedf0; border-radius:16px; padding:1rem 1.2rem;}
.tile .n {font-size:2rem; font-weight:800; line-height:1; color:#1a1f2e;}
.tile .l {color:#8b93a1; font-size:.74rem; font-weight:600; text-transform:uppercase;
          letter-spacing:.05em; margin-top:.45rem; display:flex; align-items:center;}
.tile.buy .n {color:#16a34a;} .tile.warn .n {color:#f59e0b;} .tile.sell .n {color:#dc2626;}
.dot {display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px;}
.dot.buy {background:#16a34a;} .dot.warn {background:#f59e0b;} .dot.sell {background:#dc2626;}

.macro {background:#fff; border:1px solid #ecedf0; border-radius:16px; padding:.95rem 1.2rem;
        margin-bottom:1.7rem; font-size:.88rem; color:#374151; line-height:1.5;}
.macro .ml {font-size:.68rem; text-transform:uppercase; letter-spacing:.05em; color:#16a34a;
            font-weight:700; margin-bottom:.4rem; display:flex; align-items:center; gap:.4rem;}
.macro .ml svg {width:14px; height:14px;}

.sec {display:flex; align-items:center; gap:.45rem; font-size:1.15rem; font-weight:700;
      color:#1a1f2e; margin:.3rem 0 1rem;}
.sec svg {width:20px; height:20px; color:#16a34a;}

.cg {display:grid; grid-template-columns:repeat(auto-fill,minmax(285px,1fr)); gap:.9rem;}
.call {background:#fff; border:1px solid #ecedf0; border-left:4px solid #16a34a;
       border-radius:16px; padding:1.1rem 1.2rem; transition:.15s;}
.call:hover {box-shadow:0 8px 24px rgba(20,30,50,.07); transform:translateY(-2px);}
.call.danger {border-left-color:#dc2626;} .call.caution {border-left-color:#f59e0b;}
.call.neutral {border-left-color:#9aa2b1;}
.call .r1 {display:flex; justify-content:space-between; align-items:center; margin-bottom:.7rem;}
.call .tk {font-weight:800; font-size:1.18rem; color:#1a1f2e;}
.call .act {font-size:.7rem; font-weight:700; padding:.22rem .6rem; border-radius:999px;}
.call .act.good {background:#dcfce7; color:#15803d;} .call .act.danger {background:#fee2e2; color:#b91c1c;}
.call .act.caution {background:#fef3c7; color:#b45309;} .call .act.neutral {background:#eef1f4; color:#475569;}
.call .nums {display:flex; align-items:baseline; gap:.5rem;}
.call .nums .entry {font-size:1.2rem; font-weight:800; color:#1a1f2e;}
.call .nums .arw {color:#c2c8d0; font-weight:700;}
.call .nums .tgt {font-size:1.5rem; font-weight:800; color:#16a34a;}
.call .nums.warn {font-size:1.05rem; font-weight:800; color:#b91c1c;}
.call .stopl {font-size:.78rem; color:#6b7280; margin-top:.35rem;}
.call .stopl b {color:#dc2626; font-size:.62rem; letter-spacing:.04em; margin-right:2px;}
.call .reason {color:#8b93a1; font-size:.75rem; line-height:1.45; margin-top:.7rem;}

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


ana = {}
_ap = DATA_DIR / "analysis.json"
if _ap.exists():
    try:
        ana = json.loads(_ap.read_text(encoding="utf-8"))
    except Exception:
        ana = {}
calls = ana.get("calls", [])

sig = q("SELECT * FROM signals")
nfocus = len(q("SELECT ticker FROM focus_list")) if not sig.empty else 0

st.markdown(
    f'<div class="hdr"><div class="brand">{IC_LOGO}<h1>Trade</h1></div>'
    f'<span class="date">Analisa {ana.get("generated", "—")}</span></div>'
    f'<div class="sub">Keputusan oleh Claude (LLM) · saham IDX · bukan nasihat keuangan</div>',
    unsafe_allow_html=True)

nbeli = sum(1 for c in calls if c["action"].startswith("BELI"))
ntunggu = sum(1 for c in calls if "TUNGGU" in c["action"])
nhindari = sum(1 for c in calls if c["action"] == "HINDARI")
st.markdown(
    f'<div class="tiles">'
    f'<div class="tile buy"><div class="n">{nbeli}</div>'
    f'<div class="l"><span class="dot buy"></span>Beli</div></div>'
    f'<div class="tile warn"><div class="n">{ntunggu}</div>'
    f'<div class="l"><span class="dot warn"></span>Tunggu</div></div>'
    f'<div class="tile sell"><div class="n">{nhindari}</div>'
    f'<div class="l"><span class="dot sell"></span>Hindari</div></div>'
    f'<div class="tile"><div class="n">{nfocus}</div>'
    f'<div class="l">Saham dipantau</div></div>'
    f'</div>', unsafe_allow_html=True)

if ana.get("macro"):
    st.markdown(
        f'<div class="macro"><div class="ml">{IC_LOGO} Baca Makro · Claude</div>'
        f'{ana["macro"]}</div>', unsafe_allow_html=True)


def callcard(c):
    flag = c.get("flag", "neutral")
    if c.get("entry"):
        nums = (f'<div class="nums"><span class="entry">{rp(c["entry"])}</span>'
                f'<span class="arw">&#8594;</span><span class="tgt">{rp(c["target"])}</span></div>'
                f'<div class="stopl"><b>STOP</b>{rp(c["stop"])} &nbsp;·&nbsp; '
                f'Konviksi {c.get("conviction", "-")}</div>')
    else:
        nums = '<div class="nums warn">Nol posisi</div>'
    return (f'<div class="call {flag}"><div class="r1"><span class="tk">{code(c["ticker"])}</span>'
            f'<span class="act {flag}">{c["action"]}</span></div>{nums}'
            f'<div class="reason">{c.get("reason", "")}</div></div>')


st.markdown(f'<div class="sec">{IC_LOGO} Keputusan Claude Hari Ini</div>', unsafe_allow_html=True)
if calls:
    st.markdown(f'<div class="cg">{"".join(callcard(c) for c in calls)}</div>', unsafe_allow_html=True)
else:
    st.info("Belum ada analisa Claude — generate `data/analysis.json` dulu.")

st.write("")
st.write("")
t_mesin, t_sent, t_fund, t_chart, t_paper = st.tabs([
    ":material/settings: Sinyal Mesin (teknikal)",
    ":material/newspaper: Sentimen",
    ":material/account_balance: Fundamental",
    ":material/show_chart: Chart",
    ":material/wallet: Paper"])

with t_mesin:
    st.caption("Sinyal rule-based (MA/RSI/ATR) — buat PEMBANDING. Yang di atas keputusan Claude.")
    if not sig.empty:
        acts = st.multiselect("Filter", ["BUY", "HOLD", "SELL"], default=["BUY"])
        d = sig[sig["action"].isin(acts)].copy().sort_values("score", ascending=False)
        d["saham"] = d["ticker"].map(code)
        st.dataframe(
            d[["saham", "action", "score", "close", "rsi", "sent", "n_news", "stop", "target"]],
            hide_index=True, use_container_width=True, height=420,
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
    if not sig.empty:
        tk = st.selectbox("Berita per saham", sorted(sig["ticker"].unique()))
        st.dataframe(q("SELECT published AS terbit, sent_score AS skor, source AS sumber, "
                       "title AS judul FROM news WHERE ticker=? ORDER BY published DESC LIMIT 25", (tk,)),
                     hide_index=True, use_container_width=True)

with t_fund:
    f = q("SELECT * FROM fundamentals")
    if f.empty:
        st.info("Belum ada data fundamental.")
    else:
        recs = f.to_dict("records")
        fs = pd.DataFrame([sanitize(r) for r in recs])          # buang data ngaco -> kosong
        fs["bendera merah"] = ["; ".join(red_flags(r)) for r in recs]
        fs["saham"] = fs["ticker"].map(code)
        for pc in ["roe", "div_yield", "margin"]:               # fraksi -> persen buat tampil
            fs[pc] = pd.to_numeric(fs[pc], errors="coerce") * 100
        st.caption("Rasio yfinance yang ngaco (mis. PBV ratusan ribu) disaring jadi kosong.")
        st.dataframe(
            fs[["saham", "per", "pbv", "roe", "der", "div_yield", "margin", "bendera merah"]],
            hide_index=True, use_container_width=True, height=440,
            column_config={
                "per": st.column_config.NumberColumn("PER", format="%.1f"),
                "pbv": st.column_config.NumberColumn("PBV", format="%.2f"),
                "roe": st.column_config.NumberColumn("ROE %", format="%.1f"),
                "der": st.column_config.NumberColumn("DER %", format="%.0f"),
                "div_yield": st.column_config.NumberColumn("Div yield %", format="%.2f"),
                "margin": st.column_config.NumberColumn("Margin %", format="%.1f"),
            })

with t_chart:
    if not sig.empty:
        tk = st.selectbox("Pilih saham", sorted(sig["ticker"].unique()), key="chart")
        px = q("SELECT date, close FROM prices WHERE ticker=? ORDER BY date", (tk,))
        if not px.empty:
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
        st.info("Belum ada posisi paper.")
