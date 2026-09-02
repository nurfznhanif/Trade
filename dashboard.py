"""Dashboard Trade — Streamlit. Keputusan Claude (LLM) di depan, sinyal mesin jadi pembanding.

Jalanin:  streamlit run dashboard.py  ->  http://localhost:8501
"""
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from trade.config import DATA_DIR          # noqa: E402
from trade.db import get_connection        # noqa: E402
from trade.fundamentals import red_flags, sanitize   # noqa: E402
from trade.journal import add_trade, close_trade, pl as jpl, summary as jsummary   # noqa: E402
from trade.macro import snapshot as macro_snapshot   # noqa: E402
from trade.risk import position_size, trailing_stop_level   # noqa: E402

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


def _poscard(saham, lot, entry, cur, trail, ret, pl_rp, sistem):
    """Kartu visual 1 posisi: bar warna + titik harga vs garis jual (buat pemula)."""
    entry = float(entry)
    cur = float(cur) if cur else entry
    trail = float(trail) if trail else entry * 0.95
    lo = trail
    hi = cur + max(cur - trail, cur * 0.02) * 0.25
    span = (hi - lo) or 1.0
    cl = lambda x: max(2.0, min(98.0, x))
    ent_pct = cl((entry - lo) / span * 100)
    cur_pct = cl((cur - lo) / span * 100)
    fill = "#16a34a" if cur >= entry else "#dc2626"
    flo, fhi = min(ent_pct, cur_pct), max(ent_pct, cur_pct)
    cushion = cur - trail
    if cur < trail:
        stat, sc = "JUAL — harga udah di bawah garis jual", "#dc2626"
    elif cushion / cur < 0.03:
        stat, sc = f"Waspada — harga tinggal {rp(cushion)} di atas garis jual", "#f59e0b"
    else:
        stat, sc = f"Aman — harga masih {rp(cushion)} di atas garis jual", "#16a34a"
    rc = "#16a34a" if (ret is not None and ret >= 0) else "#dc2626"
    rets = f"{ret*100:+.2f}%" if ret is not None else "—"
    return (
        f'<div style="background:#fff;border:1px solid #ecedf0;border-radius:14px;padding:.85rem 1.1rem;">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;">'
        f'<span style="font-weight:800;font-size:1.05rem;color:#1a1f2e;">{saham} '
        f'<span style="font-size:.7rem;font-weight:600;color:#8b93a1;">{lot:g} lot · sinyal {sistem}</span></span>'
        f'<span style="font-weight:800;font-size:1.2rem;color:{rc};">{rets}</span></div>'
        f'<div style="position:relative;height:12px;background:#eef1f4;border-radius:999px;margin:.75rem 0 .45rem;">'
        f'<div style="position:absolute;left:{flo}%;width:{fhi-flo}%;top:0;bottom:0;background:{fill};border-radius:999px;"></div>'
        f'<div style="position:absolute;left:0;top:-4px;bottom:-4px;width:3px;background:#dc2626;border-radius:2px;"></div>'
        f'<div style="position:absolute;left:{ent_pct}%;top:-4px;bottom:-4px;width:2px;background:#9aa2b1;"></div>'
        f'<div style="position:absolute;left:{cur_pct}%;top:50%;width:15px;height:15px;background:{fill};'
        f'border:2px solid #fff;border-radius:50%;transform:translate(-50%,-50%);box-shadow:0 1px 3px rgba(0,0,0,.25);"></div>'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;font-size:.72rem;color:#6b7280;">'
        f'<span style="color:#dc2626;font-weight:600;">↓ jual di {rp(trail)}</span>'
        f'<span>beli {rp(entry)}</span><span style="color:#1a1f2e;font-weight:600;">skrg {rp(cur)}</span></div>'
        f'<div style="font-size:.82rem;font-weight:600;color:{sc};margin-top:.5rem;">'
        f'{stat}  ·  P/L {rp(pl_rp)}</div></div>')


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
    f'<div class="sub">Keputusan oleh Claude (LLM) · saham IDX · bukan nasihat keuangan'
    f'{(" · sizing buat modal " + rp(ana["modal"])) if ana.get("modal") else ""}</div>',
    unsafe_allow_html=True)

with st.expander("⚙️  Aksi cepat — refresh data / buat brief"):
    st.caption("Data ketarik OTOMATIS tiap pagi 08:00 (scheduler). Tombol ini cuma buat on-demand.")
    ac1, ac2 = st.columns(2)
    if ac1.button("🔄  Refresh data sekarang  (~6 menit)", use_container_width=True):
        with st.status("Menarik harga + makro + berita + sinyal + brief...", expanded=True) as _s:
            _r = subprocess.run([sys.executable, str(ROOT / "scripts" / "daily.py")],
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
            _s.code((_r.stdout or "")[-1500:])
            _s.update(label="Selesai" if _r.returncode == 0 else "Selesai (ada warning)",
                      state="complete")
        st.cache_data.clear()
        st.rerun()
    if ac2.button("📄  Buat brief (bahan /analisa)", use_container_width=True):
        with st.spinner("Bikin brief..."):
            subprocess.run([sys.executable, str(ROOT / "scripts" / "brief.py"), "--quiet"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        st.success("Brief siap → `data/brief_latest.md`. Sekarang ketik `/analisa` di Claude Code.")
    st.info("**Update keputusan Claude:** ketik `/analisa` di Claude Code — dia baca brief + artikel "
            "lalu nulis keputusan. Ini butuh Claude (LLM), jadi **nggak bisa dari tombol**. Gratis, pakai langgananmu.")

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

try:
    _ms = macro_snapshot(get_connection())
    _reg = _ms["regime"]
    if _reg.get("level"):
        _clr = {"risk-on": "#16a34a", "netral": "#f59e0b",
                "risk-off": "#dc2626"}.get(_reg["regime"], "#6b7280")
        _inds = []
        for _i in _ms["indikator"]:
            if _i["ticker"] == "^JKSE" or _i.get("chg1mo") is None:
                continue
            _c = "#16a34a" if _i.get("arah") == "bagus" else "#dc2626"
            _inds.append(f'<span style="margin-right:1.1rem;white-space:nowrap;">{_i["label"]} '
                         f'<b style="color:{_c}">{_i["chg1mo"]*100:+.1f}%</b></span>')
        _ma200 = f"{_reg['ma200']:.0f}" if _reg["ma200"] else "—"
        st.markdown(
            f'<div class="macro" style="border-left:4px solid {_clr};">'
            f'<div class="ml">{IC_LOGO} Regime Makro (DATA) · '
            f'<b style="color:{_clr}">{_reg["regime"].upper()}</b></div>'
            f'<div style="font-size:.86rem;margin-bottom:.45rem;color:#374151;">'
            f'{_reg["note"]} — IHSG {_reg["level"]:.0f} (MA200 {_ma200})</div>'
            f'<div style="font-size:.8rem;">{"".join(_inds)}</div></div>',
            unsafe_allow_html=True)
except Exception:
    pass

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
    lot = c.get("lot")
    if lot is not None and str(c.get("action", "")).startswith("BELI") and c.get("entry"):
        if lot > 0:
            nums += (f'<div style="margin-top:.5rem;display:inline-block;font-size:.82rem;'
                     f'font-weight:800;color:#15803d;background:#dcfce7;border-radius:8px;'
                     f'padding:.28rem .6rem;">Beli {lot} lot · {rp(int(lot) * 100 * c["entry"])}</div>')
        else:
            nums += ('<div style="margin-top:.5rem;font-size:.78rem;color:#b45309;">'
                     '1 lot pun kemahalan buat modalmu</div>')
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
t_mesin, t_sent, t_fund, t_chart, t_paper, t_jurnal = st.tabs([
    ":material/settings: Sinyal Mesin (teknikal)",
    ":material/newspaper: Sentimen",
    ":material/account_balance: Fundamental",
    ":material/show_chart: Chart",
    ":material/wallet: Paper",
    ":material/book: Jurnal"])

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

with t_jurnal:
    st.caption("Trade REAL kamu (Fase 5 · duit kecil). Bukan nasihat / eksekusi — "
               "cuma catat & evaluasi disiplin.")

    jj = q("SELECT * FROM journal")

    with st.expander("➕  Catat posisi baru", expanded=jj.empty):
        with st.form("j_add", clear_on_submit=True):
            a1, a2, a3 = st.columns(3)
            f_tk = a1.text_input("Saham", placeholder="mis. CMRY")
            f_price = a2.number_input("Harga entry", min_value=0.0, step=5.0, format="%.0f")
            f_lot = a3.number_input("Lot (×100 lembar)", min_value=0.0, step=1.0,
                                    value=1.0, format="%.0f")
            a4, a5 = st.columns(2)
            f_stop = a4.number_input("Stop (opsional)", min_value=0.0, step=5.0, format="%.0f")
            f_tgt = a5.number_input("Target (opsional)", min_value=0.0, step=5.0, format="%.0f")
            f_note = st.text_input("Catatan (opsional)", placeholder="mis. ikut /analisa CMRY")
            if st.form_submit_button("Catat posisi", use_container_width=True, type="primary"):
                if f_tk.strip() and f_price > 0 and f_lot > 0:
                    add_trade(get_connection(), f_tk, f_price, f_lot,
                              stop=f_stop or None, target=f_tgt or None, thesis=f_note or None)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("Minimal isi: Saham, Harga entry, Lot.")

    with st.expander("📐  Kalkulator ukuran posisi (risk-based)"):
        z1, z2, z3, z4 = st.columns(4)
        z_cap = z1.number_input("Modal (Rp)", min_value=0.0, value=1_500_000.0,
                                step=100_000.0, format="%.0f")
        z_risk = z2.number_input("Risiko %/trade", min_value=0.1, value=2.0, step=0.5)
        z_entry = z3.number_input("Entry", min_value=0.0, step=5.0, format="%.0f", key="sz_e")
        z_stop = z4.number_input("Stop", min_value=0.0, step=5.0, format="%.0f", key="sz_s")
        if z_entry > 0 and z_stop > 0:
            rs = position_size(z_cap, z_entry, z_stop, risk_pct=z_risk / 100.0)
            if rs["lot"] > 0:
                st.success(f"Beli **{rs['lot']} lot** ({rs['shares']:.0f} lembar) = "
                           f"{rp(rs['modal'])} · kalau kena stop rugi {rp(rs['risk_rp'])} "
                           f"({rs['risk_pct_real']*100:.1f}% modal)")
            else:
                st.warning(rs["note"] or "modal kurang")

    if jj.empty:
        st.info("Jurnal masih kosong — catat trade pertama lewat form di atas. 👆")
    else:
        lastpx = q("SELECT ticker, close FROM prices WHERE (ticker, date) IN "
                   "(SELECT ticker, MAX(date) FROM prices GROUP BY ticker)")
        pxmap = dict(zip(lastpx["ticker"], lastpx["close"]))
        sigmap = dict(zip(sig["ticker"], sig["action"])) if not sig.empty else {}
        recs = jj.to_dict("records")
        s = jsummary(recs, pxmap)

        m1, m2, m3 = st.columns(3)
        m1.metric("Realized", rp(s["realized"]))
        m2.metric("Open P/L", rp(s["unreal"]))
        m3.metric("Total", rp(s["total"]), f"{s['closed']} closed · win {s['win_rate']*100:.0f}%")

        cfg = {
            "entry": st.column_config.NumberColumn("entry", format="Rp %.0f"),
            "sekarang": st.column_config.NumberColumn("sekarang", format="Rp %.0f"),
            "keluar": st.column_config.NumberColumn("keluar", format="Rp %.0f"),
            "return %": st.column_config.NumberColumn("return %", format="%.2f"),
            "P/L": st.column_config.NumberColumn("P/L", format="Rp %.0f"),
            "stop": st.column_config.NumberColumn("stop awal", format="Rp %.0f"),
            "trail": st.column_config.NumberColumn("trail stop", format="Rp %.0f"),
        }
        opn = [r for r in recs if r["status"] == "open"]
        cld = [r for r in recs if r["status"] == "closed"]
        if opn:
            st.markdown(":material/push_pin: **Posisi kamu** — bar HIJAU = untung, MERAH = rugi. "
                        "Titik makin ke KIRI (dekat garis merah) = makin deket harus **jual**.")
            _cards = ['<div style="display:flex;flex-direction:column;gap:.6rem;">']
            for r in opn:
                cur = pxmap.get(r["ticker"])
                p = jpl(r, cur)
                tr = trailing_stop_level(get_connection(), r["ticker"],
                                         r["entry_date"], r["stop"])["trail"]
                _cards.append(_poscard(code(r["ticker"]), r["lot"], r["entry"], cur, tr,
                                       p["net_pct"], p["pl_rp"], sigmap.get(r["ticker"], "-")))
            _cards.append("</div>")
            st.markdown("".join(_cards), unsafe_allow_html=True)
            with st.expander("✔  Tutup posisi"):
                opts = {f"#{r['id']} · {code(r['ticker'])} @ {rp(r['entry'])}": r["id"]
                        for r in opn}
                pick = st.selectbox("Pilih posisi", list(opts), key="j_close_pick")
                x1, x2 = st.columns([2, 1])
                x_price = x1.number_input("Harga keluar", min_value=0.0, step=5.0,
                                          format="%.0f", key="j_close_price")
                if x2.button("Tutup", use_container_width=True, type="primary"):
                    if x_price > 0:
                        close_trade(get_connection(), opts[pick], x_price)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.warning("Isi harga keluar dulu.")
        if cld:
            st.markdown(":material/check_circle: **Sudah ditutup**")
            crows = []
            for r in cld:
                p = jpl(r, None)
                crows.append({
                    "saham": code(r["ticker"]), "lot": r["lot"], "entry": r["entry"],
                    "keluar": p["px"],
                    "return %": (p["net_pct"] * 100 if p["net_pct"] is not None else None),
                    "P/L": p["pl_rp"]})
            st.dataframe(pd.DataFrame(crows), hide_index=True,
                         use_container_width=True, column_config=cfg)
