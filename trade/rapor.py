"""Rapor: ngukur saran analisa LLM pakai harga ASLI sesudah saran keluar.

Dua ukuran, DIHITUNG ULANG tiap diminta dari arsip analisa harian + tabel harga — gak ada saldo /
posisi tersimpan yang bisa melenceng, dan kalau aturan diubah hasilnya ikut dihitung ulang:
  1. Portofolio uji — modal MODAL_UJI diikutin persis sesuai Slicing Modal tiap pagi.
  2. Rapor saran    — tiap saran BELI: kebeli di Entry? kena Target atau Stop duluan?
                      + rata-rata hasil BELI / TUNGGU / HINDARI dibanding IHSG.
Aturan eksekusi sengaja KONSERVATIF (lihat RULES) biar hasil uji gak lebih manis dari kenyataan.

Arsip diisi scripts/auto_analisa.py tiap pagi (archive()). Terpisah total dari jurnal asli.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from .db import init_db
from .indicators import atr
from .risk import LOT, TRAIL_MULT, allocate, is_risk_off
from .ticks import round_levels, round_tick

MODAL_UJI = 1_500_000
FEE_BUY, FEE_SELL = 0.0015, 0.0025   # beli = sama dengan Slicing; jual = fee + pajak
MAX_POS = 6
WIB = timezone(timedelta(hours=7))

RULES = {
    "portofolio": [
        "Tiap pagi habis analisa (05.00), uang kas yang nganggur dimasukin ke Slicing Modal — aturannya sama "
        "persis dengan tombol Hitung di app (maks 6 saham, maks 25% modal per saham, rugi di Stop dijaga ±2% "
        "modal, setengahnya kalau pasar RISK-OFF).",
        "Beli di harga Entry, berlaku 1 hari. Kebeli cuma kalau hari itu harga sempat turun sampai Entry "
        "(kalau buka di bawah Entry, dapat harga buka). Gak kesentuh = batal, uangnya balik ke kas.",
        "Kalau harga buka udah di bawah Stop, gak jadi beli. Kalau di hari beli harga sempat nyentuh Stop, "
        "dianggap langsung kejual di Stop — anggapan paling jelek, biar hasil uji gak kemanisan.",
        "Jual kalau harga nyentuh garis jual, rumusnya sama dengan menu Jurnal: mulai dari Stop, lalu naik "
        "ngikutin harga tertinggi sejak beli dikurangi 3x rata-rata gerak harian. Kena Target gak langsung "
        "dijual (biarin lari).",
        "Biaya dihitung: beli 0,15%, jual 0,25%. Posisi yang masih kebuka dinilai pakai harga penutupan "
        "terakhir dikurangi biaya jual.",
        "Harga penutupan masuk tiap sore jam 17.00 (bursa tutup jam 16.00), jadi hasil hari ini udah "
        "kelihatan sorenya. Ini swing trading: posisi ditahan beberapa hari sampai minggu, bukan beli-jual "
        "dalam sehari.",
    ],
    "saran": [
        "Tiap saran BELI dicek pakai level dari saran itu sendiri: kebeli kalau harga nyentuh Entry di hari "
        "saran keluar, lalu mana duluan yang kesentuh — Target (menang) atau Stop (kalah). Kalau di hari yang "
        "sama dua-duanya kesentuh, dihitung kena Stop.",
        "Saran BELI yang diulang tiap hari buat saham yang sama dihitung satu, selama saran sebelumnya belum "
        "selesai.",
        "Entry, Target, dan Stop dibulatkan ke kelipatan harga yang sah di bursa (fraksi harga BEI, mis. "
        "2.991 jadi 2.990), jadi angkanya bisa langsung dipasang di broker.",
        "Rata-rata hasil = perubahan harga dari penutupan sebelum saran pertama keluar sampai penutupan "
        "terakhir (belum dipotong biaya). Saran yang bagus: BELI paling tinggi, HINDARI paling rendah.",
    ],
}


@dataclass
class Bar:
    date: str
    open: float
    high: float
    low: float
    close: float


def group(action: str) -> str:
    """BELI / BELI (tenang) / BELI (spekulatif) -> beli; HINDARI -> hindari; sisanya (TUNGGU PULLBACK) -> tunggu."""
    a = (action or "").upper()
    return "beli" if a.startswith("BELI") else "hindari" if a.startswith("HINDARI") else "tunggu"


# ------------------------------------------------------------------ arsip
def archive(conn, analysis: dict, now: datetime | None = None) -> str:
    """Simpan analisa ke arsip, 1 per tanggal WIB (jalan ulang di hari yang sama = ditimpa)."""
    init_db(conn)
    d = (now or datetime.now(WIB)).astimezone(WIB).date().isoformat()
    conn.execute("INSERT OR REPLACE INTO analysis_archive (date, generated_at, json) VALUES (?, ?, ?)",
                 (d, analysis.get("generated_at"), json.dumps(analysis, ensure_ascii=False)))
    conn.commit()
    return d


def _load_archive(conn) -> list[tuple[str, dict]]:
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='analysis_archive'").fetchone():
        return []
    return [(r[0], round_levels(json.loads(r[1])))
            for r in conn.execute("SELECT date, json FROM analysis_archive ORDER BY date")]


def _load_bars(conn, tickers, since: str) -> dict[str, list[Bar]]:
    return {t: [Bar(*r) for r in conn.execute(
        "SELECT date, open, high, low, close FROM prices WHERE ticker=? AND date>=? AND open IS NOT NULL "
        "AND high IS NOT NULL AND low IS NOT NULL AND close IS NOT NULL ORDER BY date", (t, since))]
        for t in tickers}


# ------------------------------------------------------------------ hitungan bersama
def _trail(rows: list[Bar], i: int, stop: float, entry_i: int) -> float:
    """Garis jual yang berlaku di hari ke-i (pakai data s/d hari i-1) — rumus sama dengan menu Jurnal:
    max(stop awal, harga tertinggi sejak beli - 3 x ATR14)."""
    past = rows[:i]
    hh = max((b.high for b in rows[entry_i:i]), default=None)
    a = atr([b.high for b in past], [b.low for b in past], [b.close for b in past], 14) if len(past) > 15 else None
    if hh is None or a is None:
        return stop
    return round_tick(max(stop, hh - TRAIL_MULT * a))   # harga sah di broker, sama dengan menu Jurnal


def _net(shares: float, buy: float, sell: float) -> dict:
    cost, got = shares * buy * (1 + FEE_BUY), shares * sell * (1 - FEE_SELL)
    return {"pl_rp": round(got - cost), "pl_pct": got / cost - 1}


def _close_on_or_before(series: dict[str, float], d: str) -> tuple[str, float] | None:
    keys = [k for k in series if k <= d]
    return (max(keys), series[max(keys)]) if keys else None


def _plan(a: dict, cash: float, held: list[str]) -> list[dict]:
    """Order pagi itu = Slicing Modal pakai kas nganggur, saham yang udah dipegang dilewati."""
    slots = MAX_POS - len(held)
    if cash < 100_000 or slots <= 0:
        return []
    calls = [c for c in a.get("calls", []) if c.get("ticker") not in held]
    return allocate(cash, calls, risk_pct=0.01 if is_risk_off(a) else 0.02, max_pos=slots)["picks"]


# ------------------------------------------------------------------ 1. portofolio uji
def _simulate(days: list[str], by_day: dict[str, dict], pending: dict | None,
              bars: dict[str, list[Bar]], modal: float) -> dict:
    idx = {t: {b.date: i for i, b in enumerate(rows)} for t, rows in bars.items()}
    cash = float(modal)
    held: list[dict] = []
    closed: list[dict] = []
    missed: list[dict] = []
    curve: list[dict] = []

    def sell(p: dict, px: float, d: str, why: str) -> None:
        nonlocal cash
        cash += p["shares"] * px * (1 - FEE_SELL)
        closed.append({"ticker": p["ticker"], "lot": p["lot"], "buy_date": p["buy_date"], "buy_px": p["buy_px"],
                       "sell_date": d, "sell_px": round(px, 2), "why": why, "hit_target": p["hit_target"],
                       **_net(p["shares"], p["buy_px"], px)})

    for t in days:
        # order dipasang jam 05.00, SEBELUM ada yang kejual hari itu -> pakai kas & posisi awal hari
        picks = _plan(by_day[t], cash, [p["ticker"] for p in held]) if t in by_day else []

        for p in list(held):                               # posisi lama: cek garis jual
            i = idx[p["ticker"]].get(t)
            if i is None:
                continue
            bar = bars[p["ticker"]][i]
            line = _trail(bars[p["ticker"]], i, p["stop"], p["entry_i"])
            p["hit_target"] = p["hit_target"] or bool(p["target"] and bar.high >= p["target"])
            if bar.open <= line:
                held.remove(p)
                sell(p, bar.open, t, "harga buka di bawah garis jual")
            elif bar.low <= line:
                held.remove(p)
                sell(p, line, t, "kena garis jual")

        for pk in picks:                                   # order baru: kebeli gak?
            tk, entry, stop = pk["ticker"], pk["entry"], pk["stop"]
            i = idx.get(tk, {}).get(t)
            if i is None:
                missed.append({"ticker": tk, "date": t, "why": "gak ada data harga"})
                continue
            bar = bars[tk][i]
            if bar.open < stop:
                missed.append({"ticker": tk, "date": t, "why": f"harga buka {bar.open:,.0f} udah di bawah Stop"})
                continue
            if bar.low > entry:
                missed.append({"ticker": tk, "date": t, "why": f"Entry {entry:,.0f} gak kesentuh (terendah {bar.low:,.0f})"})
                continue
            px = min(bar.open, entry)
            p = {"ticker": tk, "lot": pk["lot"], "shares": pk["lot"] * LOT, "buy_date": t, "buy_px": px,
                 "stop": stop, "target": pk["target"], "entry_i": i,
                 "hit_target": bool(pk["target"] and bar.high >= pk["target"])}
            cash -= p["shares"] * px * (1 + FEE_BUY)
            if bar.low <= stop:
                sell(p, stop, t, "kena Stop di hari beli")
            else:
                held.append(p)

        value = 0.0
        for p in held:
            rows = [b for b in bars[p["ticker"]] if b.date <= t]
            value += p["shares"] * rows[-1].close * (1 - FEE_SELL)
        curve.append({"date": t, "equity": round(cash + value)})

    positions = []
    for p in held:
        rows = bars[p["ticker"]]
        last = rows[-1]
        positions.append({"ticker": p["ticker"], "lot": p["lot"], "buy_date": p["buy_date"], "buy_px": p["buy_px"],
                          "stop": p["stop"], "target": p["target"], "hit_target": p["hit_target"],
                          "last": last.close, "last_date": last.date,
                          "trail": _trail(rows, len(rows), p["stop"], p["entry_i"]),
                          **_net(p["shares"], p["buy_px"], last.close)})

    value = sum(p["lot"] * LOT * p["last"] * (1 - FEE_SELL) for p in positions)
    equity = cash + value
    today = []
    if pending is not None:
        today = [{k: pk[k] for k in ("ticker", "lot", "entry", "stop", "target", "value")}
                 for pk in _plan(pending["analysis"], cash, [p["ticker"] for p in held])]
    return {"modal": modal, "cash": round(cash), "value": round(value), "equity": round(equity),
            "pl_rp": round(equity - modal), "pl_pct": equity / modal - 1,
            "open": positions, "closed": closed[::-1], "missed": missed[::-1], "curve": curve,
            "today": today, "today_date": pending["date"] if pending else None}


# ------------------------------------------------------------------ 2. rapor saran
def _outcome(c: dict, rows: list[Bar], t0: str | None) -> tuple[str, float | None, str | None]:
    """Nasib 1 saran BELI: (hasil, % dari harga beli, tanggal selesai).
    hasil: 'target' | 'stop' | 'jalan' (belum kena dua-duanya) | 'miss' (gak kebeli) | 'wait' (harga belum ada)."""
    entry, stop, target = c.get("entry"), c.get("stop"), c.get("target")
    start = next((i for i, b in enumerate(rows) if b.date == t0), None) if t0 else None
    if start is None:
        return "wait", None, None
    b0 = rows[start]
    if b0.open < stop or b0.low > entry:
        return "miss", None, t0
    px = min(b0.open, entry)
    for b in rows[start:]:
        if b.low <= stop:                                  # Stop dicek duluan (anggapan paling jelek)
            return "stop", min(b.open, stop) / px - 1, b.date
        if target and b.high >= target:
            return "target", target / px - 1, b.date
    return "jalan", rows[-1].close / px - 1, None


def _grade(entries: list[tuple[str, dict, str | None]], bars: dict[str, list[Bar]], ihsg: dict[str, float]) -> dict:
    count = {"n": 0, "target": 0, "stop": 0, "jalan": 0, "miss": 0, "wait": 0}
    busy: dict[str, str | None] = {}                          # ticker -> tanggal selesai saran BELI terakhir
    items: list[dict] = []
    first_seen: dict[tuple[str, str], tuple[str, str]] = {}   # (grup, ticker) -> (tanggal saran, t0)
    for d, a, t0 in entries:
        for c in a.get("calls", []):
            tk, g = c.get("ticker"), group(c.get("action"))
            first_seen.setdefault((g, tk), (d, t0))
            if g != "beli" or not c.get("entry") or not c.get("stop"):
                continue
            if tk in busy and (busy[tk] is None or t0 is None or busy[tk] >= t0):
                continue                                   # saran sebelumnya buat saham ini masih jalan hari itu
            res, ret, end = _outcome(c, bars.get(tk, []), t0)
            busy[tk] = end
            count["n"] += 1
            count[res] += 1
            items.append({"date": d, "ticker": tk, "action": c.get("action"), "entry": c.get("entry"),
                          "target": c.get("target"), "stop": c.get("stop"), "result": res, "ret": ret})

    # rata-rata hasil per kelompok: dari penutupan sebelum saran PERTAMA sampai penutupan terakhir
    rets: dict[str, list[float]] = {"beli": [], "tunggu": [], "hindari": []}
    ih: list[float] = []
    for (g, tk), (d, t0) in first_seen.items():
        rows = bars.get(tk, [])
        if not t0 or not rows or rows[-1].date < t0:
            continue
        ref = next((b for b in reversed(rows) if b.date < t0), None)
        if not ref:
            continue
        rets[g].append(rows[-1].close / ref.close - 1)
        a0, a1 = _close_on_or_before(ihsg, ref.date), _close_on_or_before(ihsg, rows[-1].date)
        if a0 and a1:
            ih.append(a1[1] / a0[1] - 1)
    avg = {g: (sum(v) / len(v) if v else None) for g, v in rets.items()}
    avg["ihsg"] = sum(ih) / len(ih) if ih else None
    done = count["target"] + count["stop"]
    return {"beli": count, "hit_rate": count["target"] / done if done else None, "avg": avg,
            "n": {g: len(v) for g, v in rets.items()}, "items": items[::-1]}


# ------------------------------------------------------------------ rapor lengkap (dipanggil backend)
def build(conn, modal: float = MODAL_UJI) -> dict:
    arch = _load_archive(conn)
    if not arch:
        return {"ready": False, "modal": modal, "rules": RULES}
    start = arch[0][0]
    since = (date.fromisoformat(start) - timedelta(days=90)).isoformat()
    tickers = sorted({c["ticker"] for _, a in arch for c in a.get("calls", []) if c.get("ticker")})
    bars = _load_bars(conn, tickers, since)
    ihsg = {r[0]: r[1] for r in conn.execute("SELECT date, close FROM macro WHERE ticker='^JKSE' AND date>=?",
                                              (since,))}

    # kalender bursa = tanggal harga yang ada sejak analisa pertama; analisa tanggal d berlaku di hari bursa >= d
    days = sorted({b.date for rows in bars.values() for b in rows if b.date >= start})
    by_day: dict[str, dict] = {}
    entries: list[tuple[str, dict, str | None]] = []
    pending = None
    for d, a in arch:
        t0 = next((t for t in days if t >= d), None)
        entries.append((d, a, t0))
        if t0:
            by_day[t0] = a                                 # 2 analisa jatuh ke hari bursa sama -> yang terakhir
        else:
            pending = {"date": d, "analysis": a}           # analisa hari ini, harga penutupannya belum ada

    sim = _simulate(days, by_day, pending, bars, modal)
    sim["ihsg_pct"] = None
    if days:
        a0 = _close_on_or_before(ihsg, (date.fromisoformat(days[0]) - timedelta(days=1)).isoformat())
        a1 = _close_on_or_before(ihsg, days[-1])
        if a0 and a1:
            sim["ihsg_pct"] = a1[1] / a0[1] - 1
    return {"ready": True, "start": start, "asof": days[-1] if days else None, "n_analyses": len(arch),
            "modal": modal, "sim": sim, "calls": _grade(entries, bars, ihsg), "rules": RULES}
