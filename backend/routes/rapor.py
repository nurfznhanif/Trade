"""Tab Rapor: uji coba otomatis — portofolio uji (ikut Slicing Modal tiap pagi) + rapor saran BELI.
Dihitung ulang tiap diminta dari arsip analisa + harga asli (trade/rapor.py). Jurnal asli gak disentuh."""
from __future__ import annotations

from contextlib import closing

from fastapi import APIRouter

from trade import rapor
from trade.db import get_connection

router = APIRouter()


@router.get("/rapor")
def get_rapor():
    with closing(get_connection(readonly=True)) as conn:
        return rapor.build(conn)
