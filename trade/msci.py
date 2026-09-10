"""Penanda musim rebalancing MSCI — biar /analisa otomatis ngingetin kalau dekat.

MSCI review indeks tiap Feb, Mei, Agu, Nov:
  - SAIR (Mei & Nov) = review BESAR: bisa masuk/keluar konstituen.
  - QIR  (Feb & Agu) = review kecil: mostly penyesuaian bobot.
Perubahan EFEKTIF di penutupan hari bursa TERAKHIR bulan itu (hari rebalancing =
volume jumbo di closing); pengumuman ~2 minggu sebelumnya. Arus dana pasif (index
fund/ETF yang ngikut MSCI) sering bikin saham likuid/big cap lonjak/tertekan
mendadak — itu TEKNIKAL (flow), bukan tanda tesis fundamental rusak.

Catatan: tanggal efektif dihitung sebagai hari kerja terakhir (Sen–Jum) bulan
review; libur bursa IDX diabaikan, jadi anggap ±1 hari (cukup buat pengingat).
"""
from __future__ import annotations

from datetime import date, timedelta

# bulan review -> tipe
REVIEW_MONTHS = {2: "QIR", 5: "SAIR", 8: "QIR", 11: "SAIR"}


def _last_business_day(year: int, month: int) -> date:
    """Hari kerja terakhir (Sen–Jum) di bulan itu — perkiraan tanggal efektif MSCI."""
    if month == 12:
        d = date(year, 12, 31)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)
    while d.weekday() >= 5:  # 5=Sabtu, 6=Minggu
        d -= timedelta(days=1)
    return d


def next_review(today: date) -> tuple[date, str]:
    """Tanggal efektif rebalancing MSCI berikutnya (>= hari ini) + tipenya."""
    for off in range(0, 14):
        y = today.year + (today.month - 1 + off) // 12
        m = (today.month - 1 + off) % 12 + 1
        if m in REVIEW_MONTHS:
            eff = _last_business_day(y, m)
            if eff >= today:
                return eff, REVIEW_MONTHS[m]
    return _last_business_day(today.year + 1, 2), "QIR"  # fallback (harusnya nggak kepakai)


def msci_status(today: date | None = None, warn_days: int = 15) -> dict:
    """Status musim MSCI relatif hari ini.

    Return dict: {near, effective, days, type, note}.
    near=True kalau <= warn_days menuju tanggal efektif (± masuk masa pengumuman
    s/d hari rebalancing) — saat arus asing paling ramai.
    """
    today = today or date.today()
    eff, typ = next_review(today)
    days = (eff - today).days
    near = days <= warn_days
    label = "BESAR (SAIR — bisa masuk/keluar indeks)" if typ == "SAIR" else "kecil (QIR — setel bobot)"
    if near:
        note = (f"MUSIM MSCI: {days} hari lagi ke rebalancing {typ} ({eff.isoformat()}), "
                f"review {label}. Arus asing di saham likuid/big cap bisa lonjak/tertekan "
                f"mendadak — itu flow teknikal, JANGAN panik jual cuma gara-gara ini.")
    else:
        note = (f"MSCI aman: rebalancing berikutnya {eff.isoformat()} ({typ}), "
                f"{days} hari lagi — belum musim.")
    return {"near": near, "effective": eff.isoformat(), "days": days, "type": typ, "note": note}
