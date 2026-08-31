"""Dump BRIEF HARIAN — satu file ringkas berisi semua yang dibutuhin buat nyusun
`data/analysis.json` (keputusan beli/jual ala Claude), tanpa harus query DB tangan.

Gabungin per kandidat: sinyal mesin + teknikal (high/low 20d & 60d, %1bulan, jarak
ke high) + fundamental + bendera merah + sentimen + 3 headline terbaru, plus daftar
posisi paper terbuka. Juga sorot 'pump watch' (naik ekstrem sebulan / PER absurd).

Jalanin:
    python scripts/brief.py                 # cetak + tulis data/brief_<tgl>.md
    python scripts/brief.py --top 15        # ambil 15 kandidat teratas
    python scripts/brief.py --quiet         # cuma tulis file, gak cetak panjang
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pandas as pd  # noqa: E402

from trade.config import DATA_DIR  # noqa: E402
from trade.db import get_connection  # noqa: E402
from trade.fundamentals import red_flags, sanitize  # noqa: E402

PUMP_1MO = 0.60      # naik >60% sebulan = wajib curiga pump
PUMP_PER = 200.0     # PER absurd = cangkang / tanpa laba
HOT_1MO = 0.25       # naik >25% sebulan = "hot", ukuran posisi kecil


def _rp(v):
    try:
        return f"{int(round(float(v))):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def _pct(v):
    return "—" if v is None else f"{v*100:+.1f}%"


def _f(v, nd=2):
    try:
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return "—"


def _tech(conn, ticker):
    """Konteks teknikal dari harga mentah: high/low 20d & 60d, %1bulan, jarak ke high."""
    px = pd.read_sql_query(
        "SELECT date, high, low, close FROM prices WHERE ticker=? ORDER BY date DESC LIMIT 65",
        conn, params=(ticker,))
    if px.empty:
        return {}
    px = px.iloc[::-1].reset_index(drop=True)      # urut lama->baru
    close = pd.to_numeric(px["close"], errors="coerce")
    high = pd.to_numeric(px["high"], errors="coerce")
    low = pd.to_numeric(px["low"], errors="coerce")
    last = float(close.iloc[-1])
    hi20 = float(high.tail(20).max())
    lo20 = float(low.tail(20).min())
    hi60 = float(high.tail(60).max())
    lo60 = float(low.tail(60).min())
    chg1mo = None
    if len(close) >= 22 and close.iloc[-22] > 0:
        chg1mo = last / float(close.iloc[-22]) - 1.0
    to_hi20 = (hi20 / last - 1.0) if last else None       # +% berarti masih di bawah high
    return {"last": last, "hi20": hi20, "lo20": lo20, "hi60": hi60, "lo60": lo60,
            "chg1mo": chg1mo, "to_hi20": to_hi20, "asof": px["date"].iloc[-1][:10]}


def _headlines(conn, ticker, n=3):
    rows = conn.execute(
        "SELECT published, sent_score, title, source FROM news "
        "WHERE ticker=? AND title IS NOT NULL ORDER BY published DESC LIMIT ?",
        (ticker, n)).fetchall()
    out = []
    for r in rows:
        d = (r["published"] or "")[:10]
        sc = r["sent_score"]
        sc = f"{sc:+.2f}" if isinstance(sc, (int, float)) else " ?  "
        out.append(f"      [{d} {sc}] {r['title']} — {r['source'] or '?'}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=12, help="jumlah kandidat teratas (skor)")
    ap.add_argument("--quiet", action="store_true", help="jangan cetak brief panjang ke layar")
    args = ap.parse_args()

    conn = get_connection()

    asof = conn.execute("SELECT MAX(date) FROM prices").fetchone()[0]
    n_focus = conn.execute("SELECT COUNT(*) FROM focus_list").fetchone()[0]
    names = {r["ticker"]: r["name"] for r in conn.execute("SELECT ticker, name FROM instruments")}
    funds = {r["ticker"]: dict(r) for r in conn.execute("SELECT * FROM fundamentals")}

    sig = pd.read_sql_query("SELECT * FROM signals", conn)
    if sig.empty:
        print("signals kosong — jalanin scripts/generate_signals.py dulu.")
        return
    sig = sig.sort_values("score", ascending=False).reset_index(drop=True)
    cand = sig.head(args.top)

    lines: list[str] = []
    w = lines.append
    w(f"# BRIEF HARIAN — data per {asof}")
    w(f"_generated {datetime.now():%Y-%m-%d %H:%M} · {n_focus} saham dipantau · "
      f"{len(sig)} sinyal · fokus IDX_")
    w("")
    w("> Isi `macro` di analysis.json manual (IHSG, USD/IDR, tema sektor) — itu dari "
      "berita/luar DB. Brief ini nyediain bahan PER-SAHAM buat entry/target/stop.")
    w("")
    w("## Kandidat teratas (urut skor mesin)")
    w("")

    pump, hot = [], []
    for _, s in cand.iterrows():
        tk = s["ticker"]
        t = _tech(conn, tk)
        f = funds.get(tk, {})
        fs = sanitize(f) if f else {}          # buang rasio ngaco + betulin satuan div_yield
        rf = red_flags(f) if f else []
        chg = t.get("chg1mo")
        per = fs.get("per")

        tags = []
        if chg is not None and chg >= PUMP_1MO:
            tags.append("🚩PUMP?")
            pump.append(tk)
        elif chg is not None and chg >= HOT_1MO:
            tags.append("🔥HOT")
            hot.append(tk)
        if per is not None and per >= PUMP_PER:
            tags.append(f"🚩PER {per:.0f}")
            if tk not in pump:
                pump.append(tk)
        if rf:
            tags.append("⚠" + "/".join(rf))
        tagstr = ("   " + "  ".join(tags)) if tags else ""

        w(f"### {tk}  ·  {names.get(tk, '')}  ·  [{s['action']} skor {_f(s['score'])}]"
          f"{tagstr}")
        w(f"    Harga  {_rp(t.get('last'))}   "
          f"MA20 {_rp(s['ma20'])}  MA50 {_rp(s['ma50'])}   "
          f"RSI {_f(s['rsi'], 0)}   1bln {_pct(chg)}")
        w(f"    Range  20d {_rp(t.get('lo20'))}–{_rp(t.get('hi20'))}   "
          f"60d {_rp(t.get('lo60'))}–{_rp(t.get('hi60'))}   "
          f"(ke high20: {_pct(t.get('to_hi20'))})")
        w(f"    Mesin  stop {_rp(s['stop'])}  target {_rp(s['target'])}   "
          f"sentimen {_f(s['sent'])} ({int(s['n_news'] or 0)} berita)")
        if f:
            w(f"    Fund   PER {_f(per)}  PBV {_f(fs.get('pbv'))}  "
              f"ROE {_pct(fs.get('roe'))}  DER {_f(fs.get('der'), 0)}  "
              f"margin {_pct(fs.get('margin'))}  divyield {_pct(fs.get('div_yield'))}")
        else:
            w("    Fund   (belum ada data fundamental)")
        hl = _headlines(conn, tk)
        if hl:
            w("    Berita:")
            lines.extend(hl)
        w("")

    if pump:
        w(f"## ⚠️ PUMP WATCH — jangan dikejar / verifikasi dulu: {', '.join(pump)}")
        w("")
    if hot:
        w(f"## 🔥 HOT (naik >25% sebulan — ukuran posisi kecil): {', '.join(hot)}")
        w("")

    op = DATA_DIR / "paper_open_positions.csv"
    if op.exists():
        w("## Posisi paper terbuka")
        w("")
        try:
            pdf = pd.read_csv(op)
            for _, r in pdf.sort_values("current_ret", ascending=False).iterrows():
                w(f"    {r['ticker']:<10} masuk {r['entry_date']} @ {_rp(r['entry'])}   "
                  f"→ {_pct(float(r['current_ret']))}")
        except Exception as e:
            w(f"    (gagal baca csv: {e})")
        w("")

    w("---")
    w("## Cara nyusun analysis.json")
    w("Untuk tiap kandidat kuat: action (BELI/TUNGGU PULLBACK/HINDARI), conviction, "
      "flag (good/neutral/caution/danger), entry/target/stop, reason 1–2 kalimat.")
    w("Aturan: entry dekat harga sekarang / area support; target ke high berikutnya; "
      "stop di bawah support 20d. PUMP WATCH → HINDARI (flag danger). "
      "RSI>70 & sudah HOT → TUNGGU PULLBACK.")

    text = "\n".join(lines)
    out = DATA_DIR / f"brief_{asof}.md"
    out.write_text(text, encoding="utf-8")
    latest = DATA_DIR / "brief_latest.md"
    latest.write_text(text, encoding="utf-8")

    if not args.quiet:
        print(text)
    print(f"\n💾 brief → {out}  (+ {latest.name})")


if __name__ == "__main__":
    main()
