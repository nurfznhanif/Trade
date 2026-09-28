"""Tab Analisa: hasil analisa LLM, strip angka makro, chart harga di kartu BELI, slicing modal."""
from __future__ import annotations

import json
from contextlib import closing
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from trade.config import ANALYSIS_PATH
from trade.db import get_connection, norm_ticker
from trade.macro import latest as macro_latest
from trade.risk import allocate, is_risk_off
from trade.ticks import round_levels

router = APIRouter()


@router.get("/analysis")
def get_analysis():
    """Hasil analisa terbaru (data/analysis.json, ditulis scripts/auto_analisa.py tiap pagi)."""
    if not ANALYSIS_PATH.exists():
        raise HTTPException(404, "Belum ada analisa. Tunggu jadwal analisa pagi (Senin-Jumat 05:00 WIB).")
    a = round_levels(json.loads(ANALYSIS_PATH.read_text(encoding="utf-8")))   # Entry/Target/Stop = fraksi BEI
    if not a.get("generated_at"):   # analisa lama belum nyatet jam -> pakai waktu file
        mtime = ANALYSIS_PATH.stat().st_mtime
        a["generated_at"] = datetime.fromtimestamp(mtime, timezone.utc).isoformat(timespec="seconds")
    return a


@router.get("/macro")
def get_macro():
    """Angka makro/komoditas terakhir + perubahan harian. Emas & minyak dalam Rupiah."""
    with closing(get_connection(readonly=True)) as conn:
        return {"items": macro_latest(conn)}


@router.get("/prices")
def get_prices(ticker: str, days: int = 90):
    """Harga harian (OHLC) buat chart di kartu saham BELI."""
    t = norm_ticker(ticker)
    with closing(get_connection(readonly=True)) as conn:
        rows = conn.execute("SELECT date,open,high,low,close FROM prices WHERE ticker=? ORDER BY date DESC LIMIT ?",
                            (t, days)).fetchall()
    if not rows:
        raise HTTPException(404, f"Gak ada data harga buat {t}")
    series = [dict(r) for r in reversed(rows)]   # urut lama -> baru
    last, first = series[-1]["close"], series[0]["close"]
    return {"ticker": t, "days": len(series), "last": last,
            "chg_pct": round((last / first - 1) * 100, 1) if first else None, "series": series}


class SlicingIn(BaseModel):
    modal: int


@router.post("/slicing")
def slicing(q: SlicingIn):
    """SLICING MODAL: bagi modal ke saham BELI analisa terbaru. Hitungan aturan risiko (trade.risk.allocate),
    BUKAN LLM -> instan & gratis. Regime RISK-OFF -> risiko per saham dipotong setengah (sisa jadi kas)."""
    if q.modal < 100_000:
        raise HTTPException(400, "Modal minimal Rp100.000.")
    a = get_analysis()
    risk_off = is_risk_off(a)
    out = allocate(q.modal, a.get("calls", []), risk_pct=0.01 if risk_off else 0.02)
    out["risk_off"] = risk_off
    return out
