"""Jurnal trading REAL — catat beli/jual yang udah dieksekusi di broker, hitung P/L.

BUKAN eksekusi order & BUKAN nasihat — cuma pencatat + evaluator disiplin (nahan stop? konsisten?).
IDX: 1 lot = 100 lembar. P/L KOTOR = literal (lot*100*(jual-beli)); 'net%' pakai model biaya
backtest (net_return) biar apple-to-apple sama paper trading & backtest.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from .backtest import BTParams, net_return
from .db import norm_ticker
from .risk import LOT, trailing_stop_level

_BT = BTParams()   # model biaya default (fee beli 0.15%, jual 0.25%, slippage 0.10%/sisi)


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


def delete_trade(conn, trade_id) -> int:
    """Hapus 1 catatan (salah input / dobel). Return jumlah baris kehapus (0 = gak ketemu)."""
    n = conn.execute("DELETE FROM journal WHERE id=?", (trade_id,)).rowcount
    conn.commit()
    return n


def pl(row, current=None) -> dict:
    """Hitung P/L satu trade. row: dict journal. current: harga sekarang (buat open trade).

    Balikin: px (harga jual / sekarang), gross_pct, net_pct (setelah biaya),
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


def report(conn) -> dict:
    """Isi jurnal lengkap: tiap trade + P/L, posisi terbuka dinilai pakai close terakhir
    + garis jual trailing. Urutan: yang terbuka dulu, lalu terbaru. conn: row_factory Row."""
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM journal "
        "ORDER BY status='closed', COALESCE(exit_date, entry_date) DESC, id DESC")]
    px: dict[str, float] = {}
    px_date: dict[str, str] = {}
    trail: dict[int, float | None] = {}
    for r in rows:
        if r["status"] != "open":
            continue
        if r["ticker"] not in px:
            last = conn.execute("SELECT close, date FROM prices WHERE ticker=? ORDER BY date DESC LIMIT 1",
                                (r["ticker"],)).fetchone()
            if last:
                px[r["ticker"]], px_date[r["ticker"]] = last["close"], last["date"]
        trail[r["id"]] = trailing_stop_level(conn, r["ticker"], r["entry_date"], r["stop"])["trail"]
    trades = [{**r, **pl(r, px.get(r["ticker"])),
               "px_date": px_date.get(r["ticker"]), "trail": trail.get(r["id"])} for r in rows]
    return {"trades": trades, "summary": summary(rows, px)}


# kolom yang dicadangkan (isi asli jurnal; P/L & garis jual dihitung ulang dari harga)
BACKUP_FIELDS = ("id", "ticker", "entry_date", "entry", "lot", "stop", "target", "thesis",
                 "exit_date", "exit", "status", "created")


def export_rows(conn) -> list[dict]:
    """Isi asli jurnal buat dicadangkan."""
    return [{k: r[k] for k in BACKUP_FIELDS} for r in conn.execute("SELECT * FROM journal ORDER BY id")]


def restore(conn, rows: list[dict]) -> int:
    """Pulihkan jurnal dari cadangan — CUMA kalau jurnal sekarang kosong (biar gak pernah dobel / ketimpa).
    Baris yang gak lengkap dilewati. Return jumlah baris yang dipulihkan."""
    if conn.execute("SELECT COUNT(*) FROM journal").fetchone()[0]:
        raise ValueError("Jurnal di server udah ada isinya, pemulihan dibatalin biar gak dobel.")
    clean = []
    for r in rows:
        if not r.get("ticker") or _f(r.get("entry")) is None or _f(r.get("lot")) is None or not r.get("entry_date"):
            continue
        status = "closed" if r.get("status") == "closed" and _f(r.get("exit")) is not None else "open"
        clean.append((r.get("id") if isinstance(r.get("id"), int) else None, norm_ticker(r["ticker"]),
                      str(r["entry_date"])[:10], _f(r["entry"]), _f(r["lot"]), _f(r.get("stop")),
                      _f(r.get("target")), r.get("thesis"), (str(r["exit_date"])[:10] if r.get("exit_date") else None),
                      _f(r.get("exit")) if status == "closed" else None, status, r.get("created")))
    conn.executemany(f"INSERT INTO journal ({', '.join(BACKUP_FIELDS)}) VALUES ({', '.join('?' * len(BACKUP_FIELDS))})",
                     clean)
    conn.commit()
    return len(clean)


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
