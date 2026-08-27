"""Tarik berita via Google News RSS.

Gratis, tanpa API key. Jalan buat bahasa Inggris (en) & Indonesia (id),
jadi satu sumber nutup dua pasar (US + IDX) buat Fase 0.
"""
from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone

import feedparser

# Setting locale Google News per bahasa
_LOCALE = {
    "en": {"hl": "en-US", "gl": "US", "ceid": "US:en"},
    "id": {"hl": "id",    "gl": "ID", "ceid": "ID:id"},
}


def _rss_url(query: str, lang: str = "en") -> str:
    loc = _LOCALE.get(lang, _LOCALE["en"])
    q = urllib.parse.quote(query)
    return (
        f"https://news.google.com/rss/search?q={q}"
        f"&hl={loc['hl']}&gl={loc['gl']}&ceid={loc['ceid']}"
    )


def fetch_news(query: str, lang: str = "en", limit: int = 20) -> list[dict]:
    """Ambil berita terbaru buat sebuah query. Return list of dict."""
    feed = feedparser.parse(_rss_url(query, lang))

    items: list[dict] = []
    for entry in feed.entries[:limit]:
        items.append({
            "published": _to_iso(entry.get("published_parsed")),
            "title": entry.get("title"),
            "link": entry.get("link"),
            "source": _source_of(entry),
            "summary": entry.get("summary"),
        })
    return items


def build_news_query(ticker: str, name: str, market: str) -> tuple[str, str]:
    """Bikin (query, lang) otomatis dari nama emiten. Buat saham yang gak diset manual."""
    clean = (name or "").split(" - ")[0].strip()   # buang ekor '- Common Stock' dll
    if market == "IDX":
        code = ticker.replace(".JK", "")
        clean = clean.replace("Tbk.", "").replace("Tbk", "").strip()
        return f"{clean} {code} saham".strip(), "id"
    return f"{clean} {ticker} stock".strip(), "en"


def _source_of(entry):
    """Google News nyimpen nama media di <source>."""
    src = entry.get("source")
    if isinstance(src, dict):
        return src.get("title")
    return getattr(src, "title", None)


def _to_iso(time_struct):
    """time.struct_time (UTC) -> ISO string."""
    if not time_struct:
        return None
    try:
        return datetime(*time_struct[:6], tzinfo=timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return None
