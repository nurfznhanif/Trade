"""Jurnal trading REAL (Fase 5) — catat entry/exit manual, hitung P/L, bandingin
sama sinyal & keputusan sistem.

BUKAN eksekusi order & BUKAN nasihat beli/jual — cuma PENCATAT + evaluator disiplin
(apakah kamu ngikutin sinyal? nahan stop? konsisten?).

IDX: 1 lot = 100 lembar. P/L KOTOR = literal (lot*100*(exit-entry)); 'net%' pakai
model biaya sistem (net_return) biar apple-to-apple sama paper trading & backtest.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from .backtest import BTParams, net_return

LOT = 100          # 1 lot IDX = 100 lembar
_BT = BTParams()   # model biaya default (fee beli 0.15%, jual 0.25%, slippage 0.10%/sisi)


def norm_ticker(t: str) -> str:
    """'bbca' / 'BBCA' -> 'BBCA.JK'. Yang udah ada '.' dibiarin."""
    t = (t or "").strip().upper()
    return t if "." in t else t + ".JK"


def add_trade(conn, ticker, entry, lot, entry_date=None, stop=None, target=None,
              thesis=None) -> int:
    """Catat 1 posisi baru (status open). Return id."""
    cur = conn.execute(
        "INSERT INTO journal (ticker, entry_date, entry, lot, stop, target, thesis, "
        "status, created) VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?)",
        (norm_ticker(ticker), entry_date or date.today().isoformat(), float(entry),
         float(lot), _f(stop), _f(target), thesis,
         datetime.now(timezone.utc).isoformat(timespec="seconds")))
    conn.commit()
    return cur.lastrowid


def close_trade(conn, trade_id, exit_price, exit_date=None) -> int:
    """Tutup posisi. Return jumlah baris keupdate (0 = gak ketemu / udah closed)."""
    n = conn.execute(
        "UPDATE journal SET exit=?, exit_date=?, status='closed' "
        "WHERE id=? AND status='open'",
        (float(exit_price), exit_date or date.today().isoformat(), trade_id)).rowcount
    conn.commit()
    return n


def pl(row, current=None) -> dict:
    """Hitung P/L satu trade. row: dict journal. current: harga sekarang (buat open trade).

    Balikin: px (harga penutup/ sekarang), gross_pct, net_pct (setelah biaya),
    pl_rp (literal Rupiah), value (nilai posisi), shares, closed.
    """
    entry = float(row["entry"])
    shares = float(row["lot"]) * LOT
    closed = row.get("status") == "closed" and row.get("exit") is not None
    px = float(row["exit"]) if closed else (float(current) if current else None)
    if px is None:
        return {"px": None, "gross_pct": None, "net_pct": None, "pl_rp": None,
                "value": entry * shares, "shares": shares, "closed": closed}
    gross = px / entry - 1.0
    return {"px": px, "gross_pct": gross, "net_pct": net_return(gross, _BT),
            "pl_rp": (px - entry) * shares, "value": px * shares,
            "shares": shares, "closed": closed}


def summary(rows, price_of=None) -> dict:
    """Agregat jurnal. rows: list dict journal. price_of: {ticker: harga_skrg} buat open."""
    price_of = price_of or {}
    realized = unreal = 0.0
    wins = closed = openn = 0
    rets = []
    for r in rows:
        p = pl(r, price_of.get(r["ticker"]))
        if p["pl_rp"] is None:
            continue
        if p["closed"]:
            realized += p["pl_rp"]
            closed += 1
            rets.append(p["net_pct"])
            wins += p["net_pct"] > 0
        else:
            unreal += p["pl_rp"]
            openn += 1
    return {"realized": realized, "unreal": unreal, "total": realized + unreal,
            "closed": closed, "open": openn, "wins": wins,
            "win_rate": wins / closed if closed else 0.0,
            "avg_ret": sum(rets) / len(rets) if rets else 0.0}


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
