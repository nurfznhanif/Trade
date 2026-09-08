"""Dashboard Trade — Linear/Raycast Dark Fintech & Trading Cockpit HUD.
Keputusan Claude (LLM) di depan, sinyal mesin jadi pembanding.
Fase 5: Validasi Modal Kecil (~Rp1,5 Juta) & Jurnal Disiplin Psikologi.

Jalanin:  streamlit run dashboard.py  ->  http://localhost:8501
"""
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import altair as alt
import pandas as pd
import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from trade.config import DATA_DIR                                # noqa: E402
from trade.db import get_connection                              # noqa: E402
from trade.fundamentals import red_flags, sanitize               # noqa: E402
from trade.journal import add_trade, close_trade, pl as jpl, summary as jsummary  # noqa: E402
from trade.macro import snapshot as macro_snapshot               # noqa: E402
from trade.risk import position_size, trailing_stop_level        # noqa: E402

# ==============================================================================
# 1. PAGE CONFIG & LINEAR/RAYCAST DARK FINTECH DESIGN SYSTEM
# ==============================================================================
st.set_page_config(
    page_title="Trade IDX — Cockpit",
    page_icon=":material/trending_up:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def clean_html(s: str) -> str:
    """Bersihkan semua indentasi agar Streamlit tidak menganggapnya indented code block."""
    return "\n".join(line.strip() for line in s.strip().splitlines() if line.strip())


DARK_FINTECH_CSS = clean_html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

#MainMenu, header[data-testid="stHeader"], footer, [data-testid="stToolbar"] {display: none !important;}
.stAppDeployButton {display: none !important;}

/* Canvas & Backgrounds */
html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background-color: #080c14 !important;
    color: #f1f5f9;
}
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 3.5rem;
    max-width: 1260px;
}

/* Sidebar Styling */
section[data-testid="stSidebar"] {
    background-color: #0d121f !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
}
section[data-testid="stSidebar"] .block-container {
    padding-top: 1rem;
    padding-left: 1.1rem;
    padding-right: 1.1rem;
}

/* Native Containers as Dark Glass Cards */
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    background-color: #111827 !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 14px !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div:hover {
    border-color: rgba(255, 255, 255, 0.16) !important;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35) !important;
}

/* Typography & Numerals */
div[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 1.25rem !important;
    color: #f8fafc !important;
    letter-spacing: -0.02em;
}
div[data-testid="stMetricLabel"] {
    color: #94a3b8 !important;
    font-size: 0.74rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
}

/* Status Badges & Dots */
.dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
}
.dot-buy { background-color: #10b981; box-shadow: 0 0 8px rgba(16, 185, 129, 0.5); }
.dot-caution { background-color: #f59e0b; box-shadow: 0 0 8px rgba(245, 158, 11, 0.5); }
.dot-wait { background-color: #6366f1; box-shadow: 0 0 8px rgba(99, 102, 241, 0.5); }
.dot-avoid { background-color: #f43f5e; box-shadow: 0 0 8px rgba(244, 63, 94, 0.5); }

.badge-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 0.2rem 0.6rem;
    border-radius: 9999px;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}
.badge-pill.success { background: rgba(16, 185, 129, 0.12); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
.badge-pill.warning { background: rgba(245, 158, 11, 0.12); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
.badge-pill.danger { background: rgba(244, 63, 94, 0.12); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.3); }
.badge-pill.neutral { background: rgba(255, 255, 255, 0.06); color: #cbd5e1; border: 1px solid rgba(255, 255, 255, 0.1); }
.badge-pill.info { background: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }

/* Linear Callout Boxes */
.edu-box {
    background: rgba(16, 185, 129, 0.08);
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 10px;
    padding: 0.7rem 0.95rem;
    font-size: 0.82rem;
    color: #a7f3d0;
    line-height: 1.5;
    margin-bottom: 0.85rem;
}
.edu-box.amber { background: rgba(245, 158, 11, 0.08); border-color: rgba(245, 158, 11, 0.25); color: #fde68a; }
.edu-box.blue { background: rgba(56, 189, 248, 0.08); border-color: rgba(56, 189, 248, 0.25); color: #bae6fd; }

/* Dynamic Position Bar (Dark HUD) */
.pos-bar-wrapper {
    background: #111827;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.85rem;
}
.pos-track {
    position: relative;
    height: 10px;
    background: #1f293d;
    border-radius: 9999px;
    margin: 0.75rem 0 0.5rem;
}
.pos-fill {
    position: absolute;
    top: 0;
    bottom: 0;
    border-radius: 9999px;
}
.pos-stop-line {
    position: absolute;
    top: -4px;
    bottom: -4px;
    width: 3px;
    background: #f43f5e;
    border-radius: 2px;
    z-index: 2;
    box-shadow: 0 0 6px rgba(244, 63, 94, 0.6);
}
.pos-entry-line {
    position: absolute;
    top: -4px;
    bottom: -4px;
    width: 2px;
    background: #94a3b8;
    z-index: 2;
}
.pos-cur-dot {
    position: absolute;
    top: 50%;
    width: 15px;
    height: 15px;
    border: 2px solid #0f172a;
    border-radius: 50%;
    transform: translate(-50%, -50%);
    box-shadow: 0 0 8px rgba(0, 0, 0, 0.6);
    z-index: 3;
}
.pos-scale {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: #94a3b8;
    font-family: 'JetBrains Mono', monospace;
}

/* Tabs */
div[data-baseweb="tab-list"] {
    gap: 0.35rem;
    background-color: #0d121f !important;
    padding: 0.3rem !important;
    border-radius: 12px !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
}
button[data-baseweb="tab"] {
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.45rem 0.95rem !important;
    color: #94a3b8 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    background-color: rgba(255, 255, 255, 0.08) !important;
    color: #f8fafc !important;
    font-weight: 700 !important;
}

/* ============================================================
   MOTION SYSTEM — halus & profesional
   ============================================================ */
@keyframes fadeUp { from { opacity:0; transform: translateY(8px); } to { opacity:1; transform: translateY(0); } }
@keyframes fadeIn { from { opacity:0; } to { opacity:1; } }
@keyframes growX  { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes pulseAmber { 0%,100% { box-shadow:0 0 0 0 rgba(245,158,11,0.5); } 50% { box-shadow:0 0 0 5px rgba(245,158,11,0); } }
@keyframes pulseRose  { 0%,100% { box-shadow:0 0 0 0 rgba(244,63,94,0.5); } 50% { box-shadow:0 0 0 5px rgba(244,63,94,0); } }

.stButton button { transition: transform 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease, border-color 0.15s ease !important; }
.stButton button:hover { transform: translateY(-1px); }
button[data-baseweb="tab"] { transition: background-color 0.15s ease, color 0.15s ease !important; }

/* Titik alert berdenyut halus untuk menarik mata (hanya waspada/bahaya) */
.dot-caution { animation: pulseAmber 2.4s ease-out infinite; }
.dot-avoid   { animation: pulseRose 2.4s ease-out infinite; }

/* ============================================================
   KPI TILES — berwarna & mudah di-scan sekilas
   ============================================================ */
.kpi-row { display:flex; gap:0.7rem; margin-top:0.9rem; flex-wrap:wrap; }
.kpi-tile {
    flex:1; min-width:118px; position:relative; overflow:hidden;
    background:#111827; border:1px solid rgba(255,255,255,0.08);
    border-radius:14px; padding:0.85rem 1rem 0.9rem;
    animation: fadeUp 0.4s ease both;
    transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}
.kpi-tile:hover { transform: translateY(-2px); border-color: rgba(255,255,255,0.18); box-shadow: 0 8px 22px rgba(0,0,0,0.35); }
.kpi-tile::before { content:''; position:absolute; left:0; top:0; bottom:0; width:3px; background: var(--acc,#94a3b8); }
.kpi-tile .kpi-num { font-family:'JetBrains Mono',monospace; font-size:1.85rem; font-weight:700; line-height:1; letter-spacing:-0.02em; color: var(--acc,#f8fafc); }
.kpi-tile .kpi-lbl { display:flex; align-items:center; gap:0.4rem; margin-top:0.5rem; font-size:0.68rem; text-transform:uppercase; letter-spacing:0.05em; font-weight:600; color:#94a3b8; }
.kpi-tile.green  { --acc:#34d399; }
.kpi-tile.amber  { --acc:#fbbf24; }
.kpi-tile.indigo { --acc:#818cf8; }
.kpi-tile.rose   { --acc:#fb7185; }
.kpi-tile.sky    { --acc:#38bdf8; }
.kpi-tile:nth-child(1){animation-delay:.02s}
.kpi-tile:nth-child(2){animation-delay:.06s}
.kpi-tile:nth-child(3){animation-delay:.10s}
.kpi-tile:nth-child(4){animation-delay:.14s}
.kpi-tile:nth-child(5){animation-delay:.18s}

/* ============================================================
   KARTU KEPUTUSAN — aksen kiri berwarna per aksi (via :has)
   ============================================================ */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.acc-green)  > div { border-left:3px solid #10b981 !important; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(.acc-amber)  > div { border-left:3px solid #f59e0b !important; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(.acc-indigo) > div { border-left:3px solid #6366f1 !important; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(.acc-rose)   > div { border-left:3px solid #f43f5e !important; }

/* Katalis clamp — potong ~3 baris, klik untuk buka penuh */
.katalis-box { margin-top:0.35rem; font-size:0.81rem; color:#f1f5f9; line-height:1.5; }
.katalis-box > summary { display:block; cursor:pointer; outline:none; list-style:none; }
.katalis-box > summary::-webkit-details-marker { display:none; }
.katalis-box > summary::marker { content:""; }
.katalis-box > summary .k-clamp { display:-webkit-box; -webkit-box-orient:vertical; -webkit-line-clamp:3; overflow:hidden; }
.katalis-box[open] > summary .k-clamp { -webkit-line-clamp:unset; display:block; }
.katalis-lbl { color:#34d399; font-weight:700; }

/* Tooltip chart (Vega) — dark, samain dengan tema */
#vg-tooltip-element, #vg-tooltip-element.vg-tooltip {
    background-color:#0d121f !important;
    border:1px solid rgba(255,255,255,0.14) !important;
    border-radius:10px !important;
    color:#e2e8f0 !important;
    font-family:'Inter', sans-serif !important;
    box-shadow:0 10px 30px rgba(0,0,0,0.55) !important;
    padding:8px 11px !important;
}
#vg-tooltip-element .key { color:#94a3b8 !important; font-weight:500 !important; }
#vg-tooltip-element .value { color:#f1f5f9 !important; font-weight:600 !important; font-family:'JetBrains Mono', monospace !important; }

/* ============================================================
   KARTU POSISI — animasi bar terisi & baris mode ringkas
   ============================================================ */
.pos-bar-wrapper { animation: fadeUp 0.35s ease both; }
.pos-fill { animation: growX 0.6s cubic-bezier(.22,1,.36,1) both; transform-origin:left center; }
.pos-cur-dot { animation: fadeIn 0.5s ease 0.28s both; }
.pos-mode { margin-top:0.65rem; font-size:0.76rem; font-weight:600; padding:0.4rem 0.7rem; border-radius:8px; line-height:1.4; }
.pos-mode.locked { background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.22); color:#6ee7b7; }
.pos-mode.risk   { background:rgba(245,158,11,0.07); border:1px solid rgba(245,158,11,0.20); color:#fcd34d; }

/* ============================================================
   SIDEBAR — label seksi tegas (perbaiki header pudar)
   ============================================================ */
section[data-testid="stSidebar"] h6 {
    color:#e2e8f0 !important; font-size:0.7rem !important; text-transform:uppercase;
    letter-spacing:0.07em; font-weight:700; margin:0.1rem 0 0.5rem;
    display:flex; align-items:center; gap:0.45rem;
}
section[data-testid="stSidebar"] h6::before { content:''; width:3px; height:11px; background:#38bdf8; border-radius:2px; display:inline-block; }

/* Sidebar cockpit selalu tampil — cegah collapse yang bikin nyangkut (tombol expand ada di header yang di-hide) */
[data-testid="stSidebarCollapseButton"] { display: none !important; }
section[data-testid="stSidebar"] {
    transform: none !important;
    margin-left: 0 !important;
    visibility: visible !important;
}
section[data-testid="stSidebar"][aria-expanded="false"] {
    width: 300px !important;
    min-width: 300px !important;
}

/* ============================================================
   SIDEBAR NAV MENU — radio disulap jadi menu navigasi
   ============================================================ */
section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] { gap: 0.2rem; }
section[data-testid="stSidebar"] [data-testid="stRadioOption"] {
    width: 100%;
    padding: 0.55rem 0.75rem !important;
    margin: 0 !important;
    border-radius: 9px;
    cursor: pointer;
    transition: background 0.15s ease, box-shadow 0.15s ease;
}
section[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover { background: rgba(255,255,255,0.055); }
/* sembunyikan bulatan radio (sibling sebelum teks) */
section[data-testid="stSidebar"] [data-testid="stRadioOption"] div:has(> [data-testid="stMarkdownContainer"]) > div:first-child { display: none !important; }
section[data-testid="stSidebar"] [data-testid="stRadioOption"] [data-testid="stMarkdownContainer"] p {
    font-size: 0.9rem !important; font-weight: 600 !important; color: #94a3b8 !important; letter-spacing: 0.01em;
}
/* item aktif */
section[data-testid="stSidebar"] [data-testid="stRadioOption"]:has(input:checked) {
    background: rgba(56,189,248,0.13);
    box-shadow: inset 3px 0 0 #38bdf8;
}
section[data-testid="stSidebar"] [data-testid="stRadioOption"]:has(input:checked) [data-testid="stMarkdownContainer"] p {
    color: #f8fafc !important; font-weight: 700 !important;
}

details[data-testid="stExpander"] summary { font-size:0.8rem; font-weight:600; }

@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation:none !important; transition:none !important; } }
</style>
""")
st.markdown(DARK_FINTECH_CSS, unsafe_allow_html=True)


# Tema Altair global — samain font (Inter) & warna chart dengan design system dark
@alt.theme.register("trade_dark", enable=True)
def _trade_dark_theme():
    return {
        "config": {
            "background": "transparent",
            "font": "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
            "view": {"strokeWidth": 0},
            "axis": {
                "labelColor": "#cbd5e1",
                "titleColor": "#94a3b8",
                "labelFont": "Inter, sans-serif",
                "titleFont": "Inter, sans-serif",
                "labelFontSize": 12,
                "titleFontSize": 12,
                "titleFontWeight": 600,
                "gridColor": "rgba(255,255,255,0.06)",
                "domainColor": "rgba(255,255,255,0.10)",
                "tickColor": "rgba(255,255,255,0.10)",
            },
            "legend": {
                "labelColor": "#cbd5e1",
                "titleColor": "#94a3b8",
                "labelFont": "Inter, sans-serif",
                "titleFont": "Inter, sans-serif",
                "symbolType": "circle",
            },
            "title": {"color": "#f1f5f9", "font": "Inter, sans-serif", "fontSize": 14, "fontWeight": 700, "anchor": "start"},
        }
    }


# ==============================================================================
# 2. HELPER FUNCTIONS & DATA QUERIES
# ==============================================================================
@st.cache_data(ttl=300)
def q(sql: str, params=None) -> pd.DataFrame:
    """Eksekusi query SQLite dengan cache 5 menit."""
    try:
        return pd.read_sql_query(sql, get_connection(), params=params)
    except Exception:
        return pd.DataFrame()


def rp(v) -> str:
    """Format angka ke Rupiah bersih."""
    try:
        if v is None:
            return "—"
        return "Rp" + f"{int(round(float(v))):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def code(ticker: str) -> str:
    """'ANTM.JK' -> 'ANTM'."""
    return str(ticker or "").replace(".JK", "").strip().upper()


def calc_rr_ratio(entry: float, target: float, stop: float) -> tuple[float, str]:
    """Hitung Risk-to-Reward Ratio (R:R)."""
    if not (entry and target and stop and target > entry and entry > stop):
        return 0.0, "—"
    risk = entry - stop
    reward = target - entry
    if risk <= 0:
        return 0.0, "—"
    rr = reward / risk
    return rr, f"1 : {rr:.2f}"


def parse_claude_reason(text: str) -> tuple[str, str | None]:
    """Pisahkan narasi Claude menjadi (katalis_riil, risiko_caveat)."""
    text = (text or "").strip()
    split_words = [" TAPI ", " Tapi ", " namun ", " Namun ", " Hati-hati ", " Sayangnya "]
    for sw in split_words:
        if sw in text:
            parts = text.split(sw, 1)
            return parts[0].strip(), (sw.strip() + " " + parts[1].strip())
    if text.startswith("HINDARI") or "PUMP" in text or "ILUSI" in text:
        return "", text
    return text, None


def get_pipeline_status() -> dict:
    """Cek kesegaran data harian (di-refresh /analisa pas dipakai, bukan scheduler)."""
    status = {
        "ok": False,
        "label": "Data: Belum Sync Hari Ini",
        "detail": "Ketik /analisa — auto-refresh kalau basi",
        "class": "warning",
        "timestamp": None,
        "date_id": None,
    }
    try:
        conn = get_connection()
        row = conn.execute("SELECT MAX(asof), MAX(updated) FROM signals").fetchone()
        if row and row[0]:
            asof_date = str(row[0])[:10]
            updated_ts = str(row[1]) if row[1] else asof_date
            today_str = datetime.now().strftime("%Y-%m-%d")

            time_display = asof_date
            try:
                dt = datetime.fromisoformat(updated_ts.replace("Z", "+00:00"))
                dt_wib = dt.astimezone(timezone(timedelta(hours=7)))
                time_display = dt_wib.strftime("%d %b %Y, %H:%M WIB")
            except Exception:
                time_display = asof_date

            status["timestamp"] = time_display
            _bulan = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
                      "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            try:
                _y, _m, _d = asof_date.split("-")
                status["date_id"] = f"{int(_d)} {_bulan[int(_m)]} {_y}"
            except Exception:
                status["date_id"] = asof_date
            if asof_date == today_str:
                status["ok"] = True
                status["label"] = "Data: Segar Hari Ini"
                status["detail"] = f"Data mutakhir {time_display}"
                status["class"] = "success"
            else:
                status["label"] = f"Data Terakhir: {asof_date}"
                status["detail"] = f"Update terakhir {time_display} · ketik /analisa buat refresh"
                status["class"] = "warning"
    except Exception:
        pass
    return status


# ==============================================================================
# 3. LOAD DATA & SETTINGS
# ==============================================================================
analysis = {}
analysis_path = DATA_DIR / "analysis.json"
if analysis_path.exists():
    try:
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    except Exception:
        analysis = {}

modal_acuan = float(analysis.get("modal") or 1500000.0)
calls = analysis.get("calls", [])

signals_df = q("SELECT * FROM signals")
focus_count = len(q("SELECT ticker FROM focus_list")) if not signals_df.empty else 0
pipeline_stat = get_pipeline_status()

# Query Portofolio Jurnal untuk Sidebar Cockpit
journal_df = q("SELECT * FROM journal")
last_prices = q(
    """
    SELECT ticker, close FROM prices WHERE (ticker, date) IN
    (SELECT ticker, MAX(date) FROM prices GROUP BY ticker)
    """
)
px_map = dict(zip(last_prices["ticker"], last_prices["close"])) if not last_prices.empty else {}
sig_map = dict(zip(signals_df["ticker"], signals_df["action"])) if not signals_df.empty else {}
journal_records = journal_df.to_dict("records") if not journal_df.empty else []
j_summary = jsummary(journal_records, px_map)

# ==============================================================================
# 4. SIDEBAR COCKPIT (CONTROL PANEL & ACCOUNT HUD)
# ==============================================================================
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center;margin-top:-0.9rem;margin-bottom:1.1rem;">
            <div style="font-size:1.95rem;font-weight:800;letter-spacing:-0.01em;color:#f8fafc;line-height:1.1;">
                TRADE <span style="color:#38bdf8;">IDX</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Status data — badge tunggal (gabungan badge + caption lama)
    st.markdown(
        f"<div style='text-align:center;margin-bottom:0.3rem;'><span class='badge-pill {pipeline_stat['class']}'>Data: {pipeline_stat['date_id'] or '—'}</span></div>",
        unsafe_allow_html=True,
    )

    st.divider()

    # Navigasi utama (menu sidebar) — ganti tab horizontal
    menu = st.radio(
        "Navigasi",
        ["Beranda", "Sinyal Mesin", "Sentimen Berita", "Fundamental", "Chart Harga", "Paper Trading", "Jurnal Real"],
        label_visibility="collapsed",
        key="nav_menu",
    )

# ==============================================================================
# 5. MAIN COCKPIT: MACRO REGIME & SUMMARY KPI
# ==============================================================================
if menu == "Beranda":
    # Top Macro Regime Bar
    try:
        ms = macro_snapshot(get_connection())
        reg = ms.get("regime", {})
        if reg.get("level"):
            r_col = {"risk-on": "#34d399", "netral": "#fbbf24", "risk-off": "#fb7185"}.get(reg.get("regime"), "#94a3b8")
            ma200_str = f"{reg['ma200']:.0f}" if reg.get("ma200") else "—"

            with st.container(border=True):
                m_top1, m_top2 = st.columns([1.3, 2.7])
                with m_top1:
                    st.markdown(
                        f"<div style='font-size:0.74rem;font-weight:700;color:{r_col};text-transform:uppercase;letter-spacing:0.06em;'>"
                        f"REGIME MAKRO IHSG &nbsp;·&nbsp; <b>{reg.get('regime', '').upper()}</b></div>"
                        f"<div style='font-size:1.25rem;font-weight:800;color:#f8fafc;margin-top:2px;font-family:JetBrains Mono,monospace;'>"
                        f"IHSG {reg.get('level', 0):.0f} &nbsp;<span style='font-size:0.8rem;color:#94a3b8;font-weight:500;'>(MA200: {ma200_str})</span></div>",
                        unsafe_allow_html=True,
                    )
                    st.caption(reg.get("note", ""))

                with m_top2:
                    pills = []
                    for ind in ms.get("indikator", []):
                        if ind.get("ticker") == "^JKSE" or ind.get("chg1mo") is None:
                            continue
                        clr = "#34d399" if ind.get("arah") == "bagus" else "#fb7185"
                        pills.append(
                            f"<span class='badge-pill neutral'>{ind['label']}: <b style='color:{clr};font-family:JetBrains Mono,monospace;'>{ind['chg1mo']*100:+.1f}%</b></span>"
                        )
                    st.markdown("<div style='display:flex;justify-content:flex-end;gap:0.4rem;flex-wrap:wrap;margin-top:0.5rem;'>" + "".join(pills) + "</div>", unsafe_allow_html=True)

                # Analisis makro — full-width di bawah kolom, biar gak 'bolong'
                if analysis.get("macro"):
                    st.markdown(
                        f"<div style='margin-top:1.3rem;padding-top:1.15rem;border-top:1px solid rgba(255,255,255,0.08);'>"
                        f"<div style='font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:#38bdf8;margin-bottom:0.35rem;'>Analisis Makro Claude</div>"
                        f"<div style='font-size:0.83rem;color:#cbd5e1;line-height:1.65;'>{analysis.get('macro')}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
    except Exception:
        pass

    # Metric Strip (KPIs)
    nbeli = sum(1 for c in calls if str(c.get("action", "")).startswith("BELI") and c.get("flag") == "good")
    ncare = sum(1 for c in calls if str(c.get("action", "")).startswith("BELI") and c.get("flag") != "good")
    ntunggu = sum(1 for c in calls if "TUNGGU" in str(c.get("action", "")))
    nhindari = sum(1 for c in calls if c.get("action") == "HINDARI")

    kpi_defs = [
        ("green",  nbeli,       "dot-buy",     "BELI Aman",       "Rekomendasi aman, katalis nyata & valuasi sehat"),
        ("amber",  ncare,       "dot-caution", "BELI Spekulatif", "Katalis ada namun ada risiko arus asing lego / cyclical"),
        ("indigo", ntunggu,     "dot-wait",    "Tunggu Pullback", "Bagus tapi harga sudah kemahalan / overbought"),
        ("rose",   nhindari,    "dot-avoid",   "Hindari (Trap)",  "Red flag laporan keuangan atau pump buatan"),
        ("sky",    focus_count, "",            "Dipantau Fokus",  "Universe saham likuid aktif di radar sistem"),
    ]
    _tiles = []
    for cls, val, dot, lbl, tip in kpi_defs:
        dot_html = f"<span class='dot {dot}'></span>" if dot else ""
        _tiles.append(
            f"<div class='kpi-tile {cls}' title='{tip}'>"
            f"<div class='kpi-num'>{val}</div>"
            f"<div class='kpi-lbl'>{dot_html}{lbl}</div>"
            f"</div>"
        )
    st.markdown("<div class='kpi-row'>" + "".join(_tiles) + "</div>", unsafe_allow_html=True)

    # ==============================================================================
    # 6. HERO SECTION: KARTU KEPUTUSAN CLAUDE (KATALIS VS CAVEAT + R:R RATIO)
    # ==============================================================================
    st.markdown("---")
    h_top1, h_top2 = st.columns([1.5, 1.5])
    with h_top1:
        st.markdown(
            clean_html(f"""
            <div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:#94a3b8;">
                Acuan Modal
            </div>
            <div style="font-size:1.5rem;font-weight:800;color:#38bdf8;font-family:'JetBrains Mono',monospace;letter-spacing:-0.02em;line-height:1.15;">
                {rp(modal_acuan)}
            </div>
            """),
            unsafe_allow_html=True,
        )
    with h_top2:
        hero_filter = st.segmented_control(
            "Filter Rekomendasi",
            options=["Beli", "Tunggu", "Hindari"],
            default="Beli",
            label_visibility="collapsed",
        )

    filtered_calls = calls
    if hero_filter == "Beli":
        filtered_calls = [c for c in calls if str(c.get("action", "")).startswith("BELI")]
    elif hero_filter == "Tunggu":
        filtered_calls = [c for c in calls if "TUNGGU" in str(c.get("action", ""))]
    elif hero_filter == "Hindari":
        filtered_calls = [c for c in calls if str(c.get("action", "")) == "HINDARI"]

    if not filtered_calls:
        st.info("Belum ada analisa rekomendasi Claude aktif untuk filter ini.")
    else:
        for idx, c in enumerate(filtered_calls):
            target_col = st.container()  # 1 kolom — kartu melebar penuh
            action = str(c.get("action", ""))
            flag = c.get("flag", "neutral")
            t_code = code(c.get("ticker", ""))
            conviction = c.get("conviction", "-")

            entry = c.get("entry")
            target = c.get("target")
            stop = c.get("stop")

            # Badge aksi styling Linear Dark
            if action.startswith("BELI") and flag == "good":
                badge_action = f"<span class='badge-pill success'><span class='dot dot-buy'></span> {action}</span>"
                accent = "green"
            elif action.startswith("BELI"):
                badge_action = f"<span class='badge-pill warning'><span class='dot dot-caution'></span> {action}</span>"
                accent = "amber"
            elif "TUNGGU" in action:
                badge_action = f"<span class='badge-pill neutral'><span class='dot dot-wait'></span> {action}</span>"
                accent = "indigo"
            else:
                badge_action = f"<span class='badge-pill danger'><span class='dot dot-avoid'></span> {action}</span>"
                accent = "rose"

            with target_col:
                with st.container(border=True):
                    # Baris 1: Header Ticker + Badge + R:R Ratio
                    r1_a, r1_b = st.columns([1.3, 1])
                    r1_a.markdown(f"#### **{t_code}** &nbsp; {badge_action}<span class='acc-{accent}' style='display:none'>·</span>", unsafe_allow_html=True)

                    rr_num, rr_str = calc_rr_ratio(entry, target, stop)
                    rr_pill = f"<span class='badge-pill info' title='Risk to Reward Ratio'>R:R {rr_str}</span>" if rr_num > 0 else ""

                    r1_b.markdown(
                        f"<div style='text-align:right;font-size:0.75rem;color:#94a3b8;padding-top:4px;'>"
                        f"{rr_pill} &nbsp; Konviksi: <b>{conviction}</b></div>",
                        unsafe_allow_html=True,
                    )

                    # Baris 2: Tiga Metrik Harga Tabular
                    if entry and target and stop:
                        risk_pct = abs((entry - stop) / entry * 100)
                        reward_pct = abs((target - entry) / entry * 100)
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Entry", rp(entry))
                        m2.metric("Target", rp(target), f"+{reward_pct:.1f}%")
                        m3.metric("Rem Rugi", rp(stop), f"-{risk_pct:.1f}%", delta_color="inverse")
                    elif entry and target:
                        m1, m2 = st.columns(2)
                        m1.metric("Area Tunggu", rp(entry))
                        m2.metric("Target", rp(target))
                    else:
                        st.markdown(
                            "<div style='background:rgba(244,63,94,0.1);border:1px solid rgba(244,63,94,0.25);border-radius:8px;padding:0.4rem 0.75rem;font-size:0.78rem;color:#fb7185;font-weight:700;text-align:center;'>"
                            "NOL POSISI — Terdeteksi rekayasa keuangan / pump buatan</div>",
                            unsafe_allow_html=True,
                        )

                    # Baris 3: Sizing Box Khusus Modal Acuan
                    if action.startswith("BELI") and entry:
                        pos_calc = position_size(modal_acuan, entry, stop or (entry * 0.95))
                        suggested_lot = c.get("lot") if c.get("lot") is not None else pos_calc["lot"]

                        if suggested_lot > 0:
                            total_modal_trade = suggested_lot * 100 * entry
                            pct_of_capital = (total_modal_trade / modal_acuan) * 100
                            st.markdown(
                                f"<div style='background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);border-radius:8px;padding:0.4rem 0.7rem;font-size:0.78rem;color:#34d399;font-weight:600;display:flex;justify-content:space-between;align-items:center;margin:0.5rem 0;'>"
                                f"<span>Saran Sizing: <b>{suggested_lot} lot</b> ({rp(total_modal_trade)})</span>"
                                f"<span style='font-family:JetBrains Mono,monospace;'>{pct_of_capital:.0f}% modal</span></div>",
                                unsafe_allow_html=True,
                            )
                        else:
                            one_lot = 100 * entry
                            st.markdown(
                                f"<div style='background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.25);border-radius:8px;padding:0.4rem 0.7rem;font-size:0.78rem;color:#fbbf24;margin:0.5rem 0;'>"
                                f"1 lot ({rp(one_lot)}) kemahalan untuk modal {rp(modal_acuan)}. Disiplin: Lewatkan!</div>",
                                unsafe_allow_html=True,
                            )
                    elif "TUNGGU" in action:
                        st.markdown(
                            f"<div style='background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:0.4rem 0.7rem;font-size:0.78rem;color:#94a3b8;margin:0.5rem 0;'>"
                            f"Tunggu Pullback: Jangan kejar harga atas. Sabar antri di area ~{rp(entry)}.</div>",
                            unsafe_allow_html=True,
                        )

                    # Baris 4: Katalis vs Caveat (Split Analysis Claude)
                    katalis_text, risiko_text = parse_claude_reason(c.get("reason", ""))
                    if katalis_text:
                        if len(katalis_text) > 150:
                            st.markdown(
                                f"<details class='katalis-box'><summary><span class='k-clamp'>"
                                f"<span class='katalis-lbl'>KATALIS:</span> {katalis_text}"
                                f"</span></summary></details>",
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                f"<div class='katalis-box'>"
                                f"<span class='katalis-lbl'>KATALIS:</span> {katalis_text}</div>",
                                unsafe_allow_html=True,
                            )
                    if risiko_text:
                        st.markdown(
                            f"<div style='font-size:0.81rem;color:#fbbf24;line-height:1.45;margin-top:0.3rem;background:rgba(245,158,11,0.06);border-left:2px solid #f59e0b;padding:0.3rem 0.5rem;border-radius:4px;'>"
                            f"<span style='font-weight:700;'>RISIKO / CAVEAT:</span> {risiko_text}</div>",
                            unsafe_allow_html=True,
                        )

# ==============================================================================
# 7. HALAMAN NAVIGASI (konten per menu sidebar)
# ==============================================================================

# ------------------------------------------------------------------------------
# TAB 1: SINYAL MESIN (TEKNIKAL MURNI)
# ------------------------------------------------------------------------------
elif menu == "Sinyal Mesin":
    st.markdown(
        clean_html("""
        <div class="edu-box">
            <b>Filosofi Sinyal Mesin:</b> Indikator kuantitatif murni (Moving Average & RSI) sebagai radar awal.
            Mesin buta terhadap manipulasi berita atau laporan keuangan semu. Gunakan tab ini murni sebagai pembanding.
        </div>
        """),
        unsafe_allow_html=True,
    )

    if not signals_df.empty:
        top_buys = signals_df[signals_df["action"] == "BUY"].nlargest(15, "score").copy()
        top_buys["saham"] = top_buys["ticker"].map(code)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Sinyal BUY Mesin", len(signals_df[signals_df["action"] == "BUY"]))
        k2.metric("Rata-rata Skor", f"{signals_df['score'].mean():.2f}")
        k3.metric("Overbought (RSI > 70)", len(signals_df[signals_df["rsi"] > 70]), help="Saham yang sudah panas dan rawan koreksi")
        k4.metric("Total Terpantau", len(signals_df))

        # Chart Skor Mesin Altair Dark
        chart_mesin = (
            alt.Chart(top_buys)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
            .encode(
                x=alt.X("score:Q", title="Kekuatan Skor Sinyal (0 — 3.0)", axis=alt.Axis(gridColor="rgba(255,255,255,0.06)", labelColor="#94a3b8", titleColor="#cbd5e1")),
                y=alt.Y("saham:N", sort="-x", title=None, axis=alt.Axis(labelColor="#f8fafc")),
                color=alt.condition(
                    alt.datum.rsi > 70,
                    alt.value("#f59e0b"),
                    alt.value("#10b981"),
                ),
                tooltip=[
                    alt.Tooltip("saham", title="Saham"),
                    alt.Tooltip("score:Q", title="Skor Mesin", format=".2f"),
                    alt.Tooltip("rsi:Q", title="RSI", format=".0f"),
                    alt.Tooltip("sent:Q", title="Sentimen", format="+.2f"),
                    alt.Tooltip("close:Q", title="Harga Terakhir", format=",.0f"),
                ],
            )
            .properties(height=360, background="transparent")
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(chart_mesin, use_container_width=True, theme=None)
        st.caption("Hijau: Sinyal momentum sehat | Oranye: RSI > 70 (Sudah jenuh beli, rawan koreksi mendadak).")

        with st.expander("Tabel Seluruh Sinyal Mesin", icon=":material/table_chart:"):
            filter_acts = st.multiselect("Filter Status Aksi", ["BUY", "HOLD", "SELL"], default=["BUY"])
            filtered_sig = signals_df[signals_df["action"].isin(filter_acts)].copy().sort_values("score", ascending=False)
            filtered_sig["saham"] = filtered_sig["ticker"].map(code)

            st.dataframe(
                filtered_sig[["saham", "action", "score", "close", "rsi", "sent", "n_news", "stop", "target"]],
                hide_index=True,
                use_container_width=True,
                height=380,
                column_config={
                    "saham": "Kode Saham",
                    "action": "Aksi",
                    "score": st.column_config.ProgressColumn("Skor Mesin", min_value=0, max_value=3, format="%.2f"),
                    "close": st.column_config.NumberColumn("Harga", format="Rp %.0f"),
                    "rsi": st.column_config.NumberColumn("RSI", format="%.0f"),
                    "sent": st.column_config.NumberColumn("Sentimen", format="%+.2f"),
                    "n_news": "Berita",
                    "stop": st.column_config.NumberColumn("Batas Rem", format="Rp %.0f"),
                    "target": st.column_config.NumberColumn("Target Checkpoint", format="Rp %.0f"),
                },
            )
    else:
        st.info("Belum ada data sinyal di database. Jalankan scripts/generate_signals.py.")

# ------------------------------------------------------------------------------
# TAB 2: SENTIMEN BERITA (CROSS-CHECK CLAUDE)
# ------------------------------------------------------------------------------
elif menu == "Sentimen Berita":
    st.markdown(
        clean_html("""
        <div class="edu-box blue">
            <b>Filter Clickbait & Caveat Media:</b> Banyak judul berita sensasional seperti <i>'Laba Meroket 800%'</i>.
            Setelah dicek Claude, laba ternyata berasal dari penjualan aset (one-off) atau perusahaan justru merugi operasional.
            Claude memeriksa isi artikel asli untuk memastikan katalisnya nyata.
        </div>
        """),
        unsafe_allow_html=True,
    )

    since_date = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat(timespec="seconds")
    news_leaderboard = q(
        """
        SELECT n.ticker AS saham, i.name AS nama, COUNT(*) AS berita,
               ROUND(AVG(n.sent_score), 2) AS sentimen
        FROM news n
        JOIN instruments i ON i.ticker = n.ticker
        WHERE n.sent_score IS NOT NULL AND (n.published IS NULL OR n.published >= ?)
        GROUP BY n.ticker HAVING berita >= 3
        ORDER BY sentimen DESC
        """,
        (since_date,),
    )

    if not news_leaderboard.empty:
        chart_data = pd.concat([news_leaderboard.head(7), news_leaderboard.tail(7)]).drop_duplicates("saham").copy()
        chart_data["saham"] = chart_data["saham"].map(code)

        chart_sent = (
            alt.Chart(chart_data)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
            .encode(
                x=alt.X("sentimen:Q", title="Mood Berita (−1.0 Sangat Negatif … 0.0 Netral … +1.0 Sangat Positif)", axis=alt.Axis(gridColor="rgba(255,255,255,0.06)", labelColor="#94a3b8", titleColor="#cbd5e1")),
                y=alt.Y("saham:N", sort="-x", title=None, axis=alt.Axis(labelColor="#f8fafc")),
                color=alt.condition(alt.datum.sentimen > 0, alt.value("#10b981"), alt.value("#f43f5e")),
                tooltip=["saham", "nama", "berita", "sentimen"],
            )
            .properties(height=340, background="transparent")
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(chart_sent, use_container_width=True, theme=None)

        col_pos, col_neg = st.columns(2)
        cfg_sent = {"sentimen": st.column_config.NumberColumn("Skor Sentimen", format="%+.2f")}
        with col_pos:
            st.markdown("##### Top Sentimen Positif (14 Hari Terakhir)")
            st.dataframe(news_leaderboard.head(8), hide_index=True, use_container_width=True, column_config=cfg_sent)
        with col_neg:
            st.markdown("##### Top Sentimen Negatif / Waspada")
            st.dataframe(news_leaderboard.tail(8).iloc[::-1], hide_index=True, use_container_width=True, column_config=cfg_sent)

        # Interactive News Reader
        st.markdown("---")
        st.markdown("##### Baca Berita Asli Per Saham")
        selected_tk = st.selectbox("Pilih Saham untuk Ditinjau Beritanya:", sorted(signals_df["ticker"].unique()) if not signals_df.empty else [])
        if selected_tk:
            articles = q(
                """
                SELECT published AS terbit, sent_score AS skor, source AS sumber, title AS judul, link AS url
                FROM news WHERE ticker = ? ORDER BY published DESC LIMIT 20
                """,
                (selected_tk,),
            )
            if not articles.empty:
                st.dataframe(
                    articles,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "skor": st.column_config.NumberColumn("Skor", format="%+.2f"),
                        "url": st.column_config.LinkColumn("Tautan Asli"),
                    },
                )
            else:
                st.caption("Belum ada artikel berita tersimpan untuk saham ini.")
    else:
        st.info("Belum ada data berita atau scoring sentimen 14 hari terakhir.")

# ------------------------------------------------------------------------------
# TAB 3: FUNDAMENTAL (VALUASI & RASIO KUNCI)
# ------------------------------------------------------------------------------
elif menu == "Fundamental":
    st.markdown(
        clean_html("""
        <div class="edu-box">
            <b>Matrix Kuadran Fundamental (PER vs ROE):</b><br>
            • <b>Kuadran Idaman (Kiri-Atas):</b> PER Rendah (Murah) & ROE Tinggi (Sangat Untung) → Sweet Spot swing trader.<br>
            • <b>Kuadran Bahaya (Kanan-Bawah):</b> PER Tinggi (Mahal) & ROE Rendah (Kurang Untung / Boncos) → Wajib hindari!
        </div>
        """),
        unsafe_allow_html=True,
    )

    fund_df = q("SELECT * FROM fundamentals")
    if not fund_df.empty:
        records = fund_df.to_dict("records")
        clean_fund = pd.DataFrame([sanitize(r) for r in records])
        clean_fund["bendera_merah"] = ["; ".join(red_flags(r)) for r in records]
        clean_fund["saham"] = clean_fund["ticker"].map(code)

        for p_col in ["roe", "div_yield", "margin"]:
            clean_fund[p_col] = pd.to_numeric(clean_fund[p_col], errors="coerce") * 100

        plot_data = clean_fund.dropna(subset=["per", "roe"]).copy()
        plot_data = plot_data[(plot_data["per"] > 0) & (plot_data["per"] < 60) & (plot_data["roe"] > -15) & (plot_data["roe"] < 80)]

        scatter_fund = (
            alt.Chart(plot_data)
            .mark_circle(size=85, opacity=0.7)
            .encode(
                x=alt.X("per:Q", title="PER (Price to Earnings) — Makin ke Kiri Makin Murah", axis=alt.Axis(gridColor="rgba(255,255,255,0.06)", labelColor="#94a3b8", titleColor="#cbd5e1")),
                y=alt.Y("roe:Q", title="ROE % (Return on Equity) — Makin ke Atas Makin Untung", axis=alt.Axis(gridColor="rgba(255,255,255,0.06)", labelColor="#94a3b8", titleColor="#cbd5e1")),
                color=alt.condition(
                    (alt.datum.per < 15) & (alt.datum.roe > 15),
                    alt.value("#34d399"),
                    alt.value("#94a3b8"),
                ),
                tooltip=[
                    alt.Tooltip("saham", title="Saham"),
                    alt.Tooltip("per:Q", title="PER", format=".1f"),
                    alt.Tooltip("roe:Q", title="ROE %", format=".1f"),
                    alt.Tooltip("margin:Q", title="Net Margin %", format=".1f"),
                    alt.Tooltip("bendera_merah:N", title="Bendera Merah"),
                ],
            )
            .properties(height=380, background="transparent")
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(scatter_fund, use_container_width=True, theme=None)
        st.caption("Titik hijau = Saham ideal (PER < 15 & ROE > 15%).")

        with st.expander("Tabel Rasio Lengkap & Detektor Bendera Merah", icon=":material/table_chart:"):
            st.dataframe(
                clean_fund[["saham", "per", "pbv", "roe", "der", "div_yield", "margin", "bendera_merah"]],
                hide_index=True,
                use_container_width=True,
                height=400,
                column_config={
                    "saham": "Saham",
                    "per": st.column_config.NumberColumn("PER", format="%.1f"),
                    "pbv": st.column_config.NumberColumn("PBV", format="%.2f"),
                    "roe": st.column_config.NumberColumn("ROE %", format="%.1f"),
                    "der": st.column_config.NumberColumn("DER %", format="%.0f"),
                    "div_yield": st.column_config.NumberColumn("Div Yield %", format="%.2f"),
                    "margin": st.column_config.NumberColumn("Margin %", format="%.1f"),
                    "bendera_merah": "Bendera Merah (Red Flags)",
                },
            )
    else:
        st.info("Data fundamental belum terisi. Jalankan scripts/fetch_fundamentals.py mingguan.")

# ------------------------------------------------------------------------------
# TAB 4: CHART HARGA
# ------------------------------------------------------------------------------
elif menu == "Chart Harga":
    st.markdown(
        clean_html("""
        <div class="edu-box">
            <b>Analisis Pergerakan Harga:</b> Pantau posisi harga terhadap Moving Average (MA20 untuk tren pendek, MA50 untuk tren menengah).
            Saham yang bertengger di atas MA20 & MA50 memiliki probabilitas kenaikan swing yang jauh lebih sehat.
        </div>
        """),
        unsafe_allow_html=True,
    )

    available_tickers = sorted(signals_df["ticker"].unique()) if not signals_df.empty else []
    if available_tickers:
        sel_col1, sel_col2 = st.columns([1, 3])
        with sel_col1:
            picked_ticker = st.selectbox("Pilih Saham", available_tickers, key="chart_ticker_select")
            days_range = st.select_slider("Rentang Hari", options=[60, 90, 180, 365], value=180)

        px_df = q("SELECT date, close FROM prices WHERE ticker = ? ORDER BY date", (picked_ticker,))
        if not px_df.empty:
            px_df["MA20"] = px_df["close"].rolling(20).mean()
            px_df["MA50"] = px_df["close"].rolling(50).mean()
            chart_slice = px_df.tail(days_range).copy()

            cur_price = chart_slice["close"].iloc[-1]
            ma20_val = chart_slice["MA20"].iloc[-1]
            ma50_val = chart_slice["MA50"].iloc[-1]

            m_col1, m_col2, m_col3 = st.columns(3)
            m_col1.metric("Harga Terakhir", rp(cur_price))
            m_col2.metric("MA20 (Tren Pendek)", rp(ma20_val), f"{(cur_price - ma20_val)/ma20_val*100:+.1f}% vs MA20")
            m_col3.metric("MA50 (Tren Menengah)", rp(ma50_val), f"{(cur_price - ma50_val)/ma50_val*100:+.1f}% vs MA50")

            chart_melt = chart_slice.melt(id_vars=["date"], value_vars=["close", "MA20", "MA50"],
                                          var_name="Indikator", value_name="Harga")

            line_plot = (
                alt.Chart(chart_melt)
                .mark_line(strokeWidth=2)
                .encode(
                    x=alt.X("date:T", title="Tanggal", axis=alt.Axis(format="%d %b", gridColor="rgba(255,255,255,0.06)", labelColor="#94a3b8", titleColor="#cbd5e1")),
                    y=alt.Y("Harga:Q", scale=alt.Scale(zero=False), title="Harga (Rp)", axis=alt.Axis(gridColor="rgba(255,255,255,0.06)", labelColor="#94a3b8", titleColor="#cbd5e1")),
                    color=alt.Color(
                        "Indikator:N",
                        scale=alt.Scale(
                            domain=["close", "MA20", "MA50"],
                            range=["#f8fafc", "#10b981", "#f59e0b"],
                        ),
                        legend=alt.Legend(orient="top", title=None, labelColor="#cbd5e1"),
                    ),
                    tooltip=[alt.Tooltip("date:T", title="Tanggal"), alt.Tooltip("Harga:Q", format=",.0f")],
                )
                .properties(height=380, background="transparent")
                .configure_view(strokeWidth=0)
            )
            st.altair_chart(line_plot, use_container_width=True, theme=None)

            active_call = next((c for c in calls if c.get("ticker") == picked_ticker), None)
            if active_call and active_call.get("entry"):
                st.info(
                    f"Level Kunci Rekomendasi Claude: Entry {rp(active_call.get('entry'))} · "
                    f"Target Checkpoint {rp(active_call.get('target'))} · "
                    f"Batas Rem Rugi {rp(active_call.get('stop'))}"
                )
    else:
        st.info("Belum ada data harga saham di database.")

# ------------------------------------------------------------------------------
# TAB 5: PAPER TRADING (SIMULASI BEBAS RISIKO)
# ------------------------------------------------------------------------------
elif menu == "Paper Trading":
    st.markdown(
        clean_html("""
        <div class="edu-box">
            <b>Simulasi Portofolio Bebas Risiko:</b> Uji ketahanan strategi trading tanpa mempertaruhkan modal riil.
            Gunakan paper trading untuk memastikan sistem memiliki keunggulan statistik (<i>Edge</i>) sebelum menaikkan modal.
        </div>
        """),
        unsafe_allow_html=True,
    )

    paper_csv = DATA_DIR / "paper_open_positions.csv"
    if paper_csv.exists():
        try:
            pp_df = pd.read_csv(paper_csv)
            pp_df["saham"] = pp_df["ticker"].map(code)
            pp_df["return_pct"] = pd.to_numeric(pp_df["current_ret"], errors="coerce") * 100

            wins = sum(pp_df["return_pct"] > 0)
            losses = sum(pp_df["return_pct"] <= 0)

            c1, c2, c3 = st.columns(3)
            c1.metric("Posisi Paper Terbuka", len(pp_df))
            c2.metric("Posisi Untung", f"{wins} saham ({(wins/len(pp_df)*100):.0f}%)")
            c3.metric("Posisi Rugi", f"{losses} saham")

            pp_chart = (
                alt.Chart(pp_df)
                .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
                .encode(
                    x=alt.X("return_pct:Q", title="Untung / Rugi Berjalan (%)", axis=alt.Axis(gridColor="rgba(255,255,255,0.06)", labelColor="#94a3b8", titleColor="#cbd5e1")),
                    y=alt.Y("saham:N", sort="-x", title=None, axis=alt.Axis(labelColor="#f8fafc")),
                    color=alt.condition(alt.datum.return_pct > 0, alt.value("#10b981"), alt.value("#f43f5e")),
                    tooltip=[
                        alt.Tooltip("saham", title="Saham"),
                        alt.Tooltip("return_pct:Q", title="Return %", format="+.1f"),
                        alt.Tooltip("entry:Q", title="Entry", format=",.0f"),
                        alt.Tooltip("entry_date:N", title="Tgl Masuk"),
                    ],
                )
                .properties(height=340, background="transparent")
                .configure_view(strokeWidth=0)
            )
            st.altair_chart(pp_chart, use_container_width=True, theme=None)

            with st.expander("Rincian Posisi Terbuka Paper Trading", icon=":material/table_chart:"):
                st.dataframe(
                    pp_df[["saham", "entry_date", "entry", "return_pct", "outcome"]],
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "saham": "Saham",
                        "entry_date": "Tanggal Masuk",
                        "entry": st.column_config.NumberColumn("Harga Entry", format="Rp %.0f"),
                        "return_pct": st.column_config.NumberColumn("Return Berjalan %", format="%+.2f"),
                        "outcome": "Status Exit",
                    },
                )
        except Exception as err:
            st.warning(f"Gagal membaca data paper positions: {err}")
    else:
        st.info("Belum ada file paper open positions (data/paper_open_positions.csv).")

# ------------------------------------------------------------------------------
# TAB 6: JURNAL REAL (FASE 5: VALIDASI MODAL KECIL ~RP1,5JT)
# ------------------------------------------------------------------------------
elif menu == "Jurnal Real":
    st.markdown(
        clean_html("""
        <div class="edu-box">
            <b>Jurnal Disiplin Psikologi:</b> Pada modal kecil (~Rp1,5 juta), tujuan utama adalah melatih konsistensi eksekusi:
            patuh pada <b>Rem Rugi</b> saat salah, dan sabar menikmati <b>Kunci Cuan</b> saat benar.
            Catatan ini murni evaluasi mandiri — bukan eksekusi otomatis.
        </div>
        """),
        unsafe_allow_html=True,
    )

    # Form Pencatatan Trade
    recom_buys = [c for c in calls if str(c.get("action", "")).startswith("BELI") and c.get("entry")]
    with st.expander("Catat Transaksi Baru (Saham yang Sudah Dibeli di Broker)", icon=":material/add_circle:", expanded=journal_df.empty):
        if recom_buys:
            st.markdown("##### Pilih Langsung dari Rekomendasi Claude Hari Ini:")
            buy_options = {
                f"{code(c['ticker'])} — Saran: {int(c.get('lot') or 1)} lot @ {rp(c['entry'])}": c
                for c in recom_buys
            }
            picked_recom = st.selectbox("Pilih Saham Rekomendasi", list(buy_options), key="j_quick_select")
            rc = buy_options[picked_recom]

            c_f1, c_f2 = st.columns(2)
            actual_price = c_f1.number_input(
                "Harga Beli Nyata di Broker (Rp)",
                min_value=0.0,
                value=float(rc["entry"]),
                step=5.0,
                format="%.0f",
                key=f"act_px_{rc['ticker']}",
                help="Harga nyata yang Anda dapatkan saat order dieksekusi di broker.",
            )
            actual_lots = c_f2.number_input(
                "Jumlah Lot yang Dibeli",
                min_value=1,
                value=int(rc.get("lot") or 1),
                step=1,
                key=f"act_lot_{rc['ticker']}",
            )

            st.caption(f"Stop awal {rp(rc.get('stop'))} · Target checkpoint {rp(rc.get('target'))} otomatis dihubungkan dari Claude.")

            if st.button(f"Simpan {code(rc['ticker'])} ({actual_lots} lot @ {rp(actual_price)}) ke Jurnal", icon=":material/check:", type="primary", use_container_width=True):
                if actual_price > 0 and actual_lots > 0:
                    add_trade(
                        get_connection(),
                        rc["ticker"],
                        actual_price,
                        actual_lots,
                        stop=rc.get("stop"),
                        target=rc.get("target"),
                        thesis=f"Ikut rekomendasi Claude ({rc['action']})",
                    )
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("Masukkan harga beli dan jumlah lot yang valid.")
            st.divider()

        with st.form("manual_journal_form", clear_on_submit=True):
            st.markdown("##### Atau Catat Manual (Di luar rekomendasi Claude):")
            m1, m2, m3 = st.columns(3)
            f_code = m1.text_input("Kode Saham (mis. BBRI)")
            f_entry = m2.number_input("Harga Beli (Rp)", min_value=0.0, step=5.0, format="%.0f")
            f_lot = m3.number_input("Berapa Lot", min_value=1, value=1, step=1)

            m4, m5, m6 = st.columns(3)
            f_stop = m4.number_input("Batas Rem Rugi (Rp)", min_value=0.0, step=5.0, format="%.0f")
            f_target = m5.number_input("Target Checkpoint (Rp)", min_value=0.0, step=5.0, format="%.0f")
            f_thesis = m6.text_input("Alasan Beli (Tesis)")

            if st.form_submit_button("Simpan Transaksi Manual", icon=":material/save:", use_container_width=True):
                if f_code.strip() and f_entry > 0 and f_lot > 0:
                    add_trade(
                        get_connection(),
                        f_code,
                        f_entry,
                        f_lot,
                        stop=f_stop or None,
                        target=f_target or None,
                        thesis=f_thesis or "Trade manual",
                    )
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("Mohon lengkapi kode saham, harga beli, dan lot.")

    # Tampilan Portofolio & Posisi Terbuka
    if journal_df.empty:
        st.info("Jurnal transaksi Anda masih kosong. Mulai catat posisi pertama Anda di atas!")
    else:
        open_trades = [r for r in journal_records if r["status"] == "open"]
        closed_trades = [r for r in journal_records if r["status"] == "closed"]

        if open_trades:
            st.markdown(
                clean_html("""
                <div style="font-size:1.15rem;font-weight:800;color:#f8fafc;margin:1.4rem 0 0.8rem 0;">
                    Posisi Terbuka Anda (Visualisasi Rem Rugi vs Kunci Cuan)
                </div>
                """),
                unsafe_allow_html=True,
            )

            with st.expander("Cara baca bar ini — Rem Rugi (Stop Loss) vs Kunci Cuan (Trailing Lock)"):
                st.markdown(
                    clean_html("""
                    <div style='font-size:0.83rem;color:#cbd5e1;line-height:1.65;'>
                    <b style='color:#fcd34d;'>REM RUGI (Stop Loss)</b> — garis jual masih di <b>bawah modal</b>. Fungsinya membatasi kerugian: kalau harga jatuh dan kena garis jual, rugi Anda mentok di angka itu, tidak makin dalam.<br>
                    <b style='color:#6ee7b7;'>KUNCI CUAN (Trailing Lock)</b> — begitu harga naik melampaui modal, garis jual ikut naik ke <b>atas modal</b>. Sekarang meski kena garis jual, Anda <b>tetap untung</b>. Biarkan pemenang lari, jangan buru-buru jual.
                    </div>
                    """),
                    unsafe_allow_html=True,
                )

            positions_map = {p["ticker"]: p for p in analysis.get("positions", [])}

            for tr in open_trades:
                c_px = px_map.get(tr["ticker"])
                p_info = jpl(tr, c_px)
                trail_info = trailing_stop_level(get_connection(), tr["ticker"], tr["entry_date"], tr["stop"])
                tr_level = trail_info["trail"]

                try:
                    days_held = (datetime.now() - datetime.strptime(str(tr["entry_date"])[:10], "%Y-%m-%d")).days
                except Exception:
                    days_held = None

                # Logic visual bar
                entry_val = float(tr["entry"])
                cur_val = float(c_px) if c_px else entry_val
                trail_val = float(tr_level) if tr_level else entry_val * 0.95

                lo = min(trail_val, entry_val * 0.92)
                hi = max(cur_val, entry_val) + max(cur_val - trail_val, cur_val * 0.03) * 0.3
                span = (hi - lo) or 1.0

                def clamp(pct):
                    return max(2.0, min(98.0, pct))

                ent_pct = clamp((entry_val - lo) / span * 100)
                cur_pct = clamp((cur_val - lo) / span * 100)
                trail_pct = clamp((trail_val - lo) / span * 100)

                fill_color = "#10b981" if cur_val >= entry_val else "#f43f5e"
                bar_left = min(ent_pct, cur_pct)
                bar_width = max(ent_pct, cur_pct) - bar_left

                cushion = cur_val - trail_val
                if cur_val < trail_val:
                    stat_text = "<span class='badge-pill danger'><span class='dot dot-avoid'></span> JUAL — Menembus batas trailing stop</span>"
                elif cushion / cur_val < 0.03:
                    stat_text = f"<span class='badge-pill warning'><span class='dot dot-caution'></span> WASPADA — Tinggal {rp(cushion)} ({cushion/cur_val*100:.1f}%) di atas garis jual</span>"
                else:
                    stat_text = f"<span class='badge-pill success'><span class='dot dot-buy'></span> AMAN — {rp(cushion)} ({cushion/cur_val*100:.1f}%) di atas garis jual</span>"

                locked = trail_val >= entry_val
                sell_pct = (trail_val - entry_val) / entry_val * 100 if entry_val else 0.0

                if locked:
                    mode_box = (
                        f"<div class='pos-mode locked'><b>KUNCI CUAN AKTIF</b> · garis jual di atas modal — "
                        f"kena garis sekarang pun Anda tetap untung {sell_pct:+.1f}%. Biarkan lari.</div>"
                    )
                else:
                    mode_box = (
                        f"<div class='pos-mode risk'><b>REM RUGI AKTIF</b> · garis jual di bawah modal — "
                        f"rugi dibatasi maksimal {sell_pct:+.1f}%. Naik terus otomatis jadi Kunci Cuan.</div>"
                    )

                ret_val = p_info["gross_pct"]
                ret_str = f"{ret_val*100:+.2f}%" if ret_val is not None else "—"
                ret_color = "#34d399" if (ret_val is not None and ret_val >= 0) else "#fb7185"
                trail_badge = f"<b style='color:{'#34d399' if locked else '#fb7185'};'>({sell_pct:+.1f}% dr modal)</b>"

                verdict_data = positions_map.get(tr["ticker"])
                verdict_html = ""
                if verdict_data and verdict_data.get("verdict"):
                    vc = {"JUAL": "#fb7185", "WASPADA": "#fbbf24", "TAHAN": "#34d399"}.get(verdict_data["verdict"], "#94a3b8")
                    verdict_html = (
                        f"<div style='margin-top:0.5rem;padding-top:0.5rem;border-top:1px dashed rgba(255,255,255,0.1);font-size:0.82rem;color:#cbd5e1;'>"
                        f"<b>Keputusan Claude: <span style='color:{vc};'>{verdict_data['verdict']}</span></b> — {verdict_data.get('reason', '')}</div>"
                    )

                bar_card_html = clean_html(f"""
                <div class="pos-bar-wrapper">
                    <div style="display:flex;justify-content:space-between;align-items:baseline;">
                        <div>
                            <span style="font-size:1.18rem;font-weight:800;color:#f8fafc;">{code(tr['ticker'])}</span>
                            <span style="font-size:0.76rem;color:#94a3b8;margin-left:0.4rem;">{tr['lot']:g} lot · {days_held or '—'} hari dipegang · sinyal {sig_map.get(tr['ticker'], '—')}</span>
                        </div>
                        <div style="font-size:1.25rem;font-weight:800;color:{ret_color};font-family:JetBrains Mono,monospace;">{ret_str}</div>
                    </div>
                    <div class="pos-track">
                        <div class="pos-fill" style="left:{bar_left}%; width:{bar_width}%; background:{fill_color};"></div>
                        <div class="pos-stop-line" style="left:{trail_pct}%;"></div>
                        <div class="pos-entry-line" style="left:{ent_pct}%;"></div>
                        <div class="pos-cur-dot" style="left:{cur_pct}%; background:{fill_color};"></div>
                    </div>
                    <div class="pos-scale">
                        <span style="color:#fb7185;font-weight:700;">Garis Jual {rp(trail_val)} {trail_badge}</span>
                        <span>Modal {rp(entry_val)}</span>
                        <span style="color:#f8fafc;font-weight:700;">Harga Saat Ini {rp(cur_val)}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:0.5rem;">
                        <div>{stat_text}</div>
                        <div style="font-size:0.86rem;font-weight:800;color:#f8fafc;font-family:JetBrains Mono,monospace;">P/L: {rp(p_info['pl_rp'])}</div>
                    </div>
                    {mode_box}
                    {verdict_html}
                </div>
                """)

                st.markdown(bar_card_html, unsafe_allow_html=True)

            # Tutup Posisi Workflow
            with st.expander("Tutup Posisi (Realisasi Trade)", icon=":material/done_all:"):
                trade_opts = {
                    f"#{t['id']} · {code(t['ticker'])} (Beli @ {rp(t['entry'])}, {t['lot']:g} lot)": t["id"]
                    for t in open_trades
                }
                picked_close = st.selectbox("Pilih Posisi yang Sudah Anda Jual di Broker:", list(trade_opts))
                close_id = trade_opts[picked_close]

                cl_c1, cl_c2 = st.columns([2, 1])
                exit_price = cl_c1.number_input("Harga Jual Nyata di Broker (Rp)", min_value=0.0, step=5.0, format="%.0f", key="exit_px_in")
                if cl_c2.button("Tutup & Simpan Hasil Trade", icon=":material/check:", type="primary", use_container_width=True):
                    if exit_price > 0:
                        close_trade(get_connection(), close_id, exit_price)
                        st.success(f"Posisi berhasil ditutup pada {rp(exit_price)}.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.warning("Mohon masukkan harga jual.")

        if closed_trades:
            st.markdown("---")
            st.markdown("##### Histori Trade Tertutup (Evaluasi Hasil & Disiplin)")
            closed_rows = []
            for ct in closed_trades:
                p_close = jpl(ct, None)
                closed_rows.append({
                    "Saham": code(ct["ticker"]),
                    "Lot": ct["lot"],
                    "Harga Masuk": ct["entry"],
                    "Harga Keluar": p_close["px"],
                    "Return %": (p_close["gross_pct"] * 100 if p_close["gross_pct"] is not None else None),
                    "Realisasi P/L": p_close["pl_rp"],
                    "Tgl Masuk": ct["entry_date"],
                    "Tgl Keluar": ct.get("exit_date", "—"),
                })
            st.dataframe(
                pd.DataFrame(closed_rows),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Harga Masuk": st.column_config.NumberColumn("Harga Masuk", format="Rp %.0f"),
                    "Harga Keluar": st.column_config.NumberColumn("Harga Keluar", format="Rp %.0f"),
                    "Return %": st.column_config.NumberColumn("Return %", format="%+.2f"),
                    "Realisasi P/L": st.column_config.NumberColumn("Realisasi P/L", format="Rp %.0f"),
                },
            )
