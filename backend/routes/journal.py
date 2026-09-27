"""Tab Jurnal: jurnal trading real — lihat, catat beli, tutup posisi, hapus catatan."""
from __future__ import annotations

from contextlib import closing
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from trade import journal as jr
from trade.db import get_connection, norm_ticker

router = APIRouter()


class TradeIn(BaseModel):
    ticker: str
    entry: float
    lot: int
    stop: float | None = None
    target: float | None = None
    thesis: str | None = None
    entry_date: str | None = None


class CloseIn(BaseModel):
    exit: float
    exit_date: str | None = None


def _iso_date(s: str | None, label: str) -> str | None:
    """'2026-09-25' -> dicek formatnya & gak boleh masa depan. Kosong -> None (= hari ini)."""
    if not s or not s.strip():
        return None
    try:
        d = date.fromisoformat(s.strip())
    except ValueError:
        raise HTTPException(400, f"{label} harus format TTTT-BB-HH (mis. 2026-09-25).")
    if d > date.today():
        raise HTTPException(400, f"{label} gak boleh di masa depan.")
    return d.isoformat()


@router.get("/journal")
def get_journal():
    """Isi jurnal + P/L (posisi terbuka pakai close terakhir) + garis jual trailing."""
    with closing(get_connection(readonly=True)) as conn:
        return jr.report(conn)


@router.post("/journal")
def add_journal(t: TradeIn):
    """Catat posisi baru (yang UDAH dibeli di broker)."""
    tk = norm_ticker(t.ticker)
    if t.entry <= 0 or t.lot <= 0:
        raise HTTPException(400, "Harga beli & jumlah lot harus lebih dari 0.")
    if t.stop and t.stop >= t.entry:
        raise HTTPException(400, "Stop (rem rugi) harus di BAWAH harga beli.")
    if t.target and t.target <= t.entry:
        raise HTTPException(400, "Target harus di ATAS harga beli.")
    entry_date = _iso_date(t.entry_date, "Tanggal beli")
    with closing(get_connection()) as conn:
        if not conn.execute("SELECT 1 FROM prices WHERE ticker=? LIMIT 1", (tk,)).fetchone():
            raise HTTPException(400, f"Kode {tk.replace('.JK', '')} gak dikenal (gak ada data harganya).")
        new_id = jr.add_trade(conn, tk, t.entry, t.lot, entry_date, t.stop or None,
                              t.target or None, (t.thesis or "").strip() or None)
    return {"ok": True, "id": new_id}


@router.post("/journal/{trade_id}/close")
def close_journal(trade_id: int, c: CloseIn):
    """Tutup posisi (udah dijual di broker) -> jadi realized P/L."""
    if c.exit <= 0:
        raise HTTPException(400, "Harga jual harus lebih dari 0.")
    exit_date = _iso_date(c.exit_date, "Tanggal jual")
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT entry_date FROM journal WHERE id=? AND status='open'", (trade_id,)).fetchone()
        if not row:
            raise HTTPException(404, f"Posisi #{trade_id} gak ketemu atau udah ditutup.")
        if exit_date and exit_date < row["entry_date"][:10]:
            raise HTTPException(400, "Tanggal jual gak boleh sebelum tanggal beli.")
        jr.close_trade(conn, trade_id, c.exit, exit_date)
    return {"ok": True}


@router.delete("/journal/{trade_id}")
def delete_journal(trade_id: int):
    """Hapus catatan (salah input / dobel). Permanen."""
    with closing(get_connection()) as conn:
        n = jr.delete_trade(conn, trade_id)
    if not n:
        raise HTTPException(404, f"Catatan #{trade_id} gak ketemu.")
    return {"ok": True}
