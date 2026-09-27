"""Tarik berita saham IDX via Google News RSS (gratis, tanpa API key).

Catatan: keterbukaan informasi resmi idx.co.id gak dipakai — situsnya di belakang Cloudflare
(403 walau pakai cloudscraper). Google News udah nutup beritanya.
"""
from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone

import feedparser

_RSS = "https://news.google.com/rss/search?q={q}&hl=id&gl=ID&ceid=ID:id"


def fetch_news(query: str, limit: int = 20) -> list[dict]:
    """Berita terbaru (bahasa Indonesia) buat satu query."""
    feed = feedparser.parse(_RSS.format(q=urllib.parse.quote(query)))
    return [{
        "published": _to_iso(e.get("published_parsed")),
        "title": e.get("title"),
        "link": e.get("link"),
        "source": _source_of(e),
        "summary": e.get("summary"),
    } for e in feed.entries[:limit]]


def build_news_query(ticker: str, name: str) -> str:
    """'BBCA.JK' + 'Bank Central Asia Tbk.' -> 'Bank Central Asia BBCA saham'."""
    clean = (name or "").split(" - ")[0].replace("Tbk.", "").replace("Tbk", "").strip()
    return f"{clean} {ticker.replace('.JK', '')} saham".strip()


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
