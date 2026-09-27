"""Tab Berita: berita terbaru + skor sentimen (lexicon) + saham paling positif / negatif."""
from __future__ import annotations

from contextlib import closing

from fastapi import APIRouter

from trade.db import get_connection

router = APIRouter()


@router.get("/news")
def get_news(limit: int = 40):
    """Berita terbaru, plus rata-rata sentimen per saham 14 hari terakhir (min 2 berita) -> top +/-.
    Jendela 14 hari = sama dengan yang dipakai sinyal (generate_signals --sent-days)."""
    with closing(get_connection(readonly=True)) as conn:
        items = conn.execute(
            "SELECT ticker,published,title,source,link,sent_label,sent_score "
            "FROM news WHERE title IS NOT NULL ORDER BY published DESC LIMIT ?", (limit,)).fetchall()
        agg = conn.execute(
            "SELECT ticker, AVG(sent_score) avg_s, COUNT(*) n "
            "FROM news WHERE published >= date('now','-14 days') AND sent_score IS NOT NULL "
            "GROUP BY ticker HAVING n >= 2 ORDER BY avg_s DESC").fetchall()
    movers = [{"ticker": a["ticker"], "avg": round(a["avg_s"], 3), "n": a["n"]} for a in agg]
    return {
        "items": [dict(r) for r in items],
        "positif": movers[:5],
        "negatif": [m for m in reversed(movers) if m["avg"] < 0][:5],
    }
