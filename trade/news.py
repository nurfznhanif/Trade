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


_scraper = None


def _get_scraper():
    """Satu cloudscraper dipakai ulang (cookie Cloudflare kesimpen -> call berikut cepat)."""
    global _scraper
    if _scraper is None:
        import cloudscraper
        _scraper = cloudscraper.create_scraper(browser={"browser": "chrome", "platform": "windows"})
    return _scraper


def fetch_idx_disclosures(code: str, limit: int = 12) -> list[dict]:
    """⚠️ NONAKTIF (Agu 2026): idx.co.id di belakang Cloudflare — bahkan homepage balikin
    403 'Just a moment' ke cloudscraper (challenge JS nggak ketembus tanpa browser sungguhan).
    Fungsi disimpen buat revive nanti (butuh Playwright/undetected-chromedriver atau layanan
    anti-bot). Sementara Google News RSS udah nutup beritanya, jadi tier ini DILEPAS dari
    pipeline harian (lihat scripts/fetch_news_focus.py).

    Pengumuman/keterbukaan resmi IDX per emiten (event: dividen, RUPS, suspensi, dll).
    `code` = kode emiten tanpa .JK (mis. 'BBCA').
    """
    url = ("https://www.idx.co.id/primary/ListedCompany/GetAnnouncement"
           f"?indexFrom=1&pageSize={limit}&dateFrom=&dateTo=&lang=id&keyword=&KodeEmiten={code}")
    r = _get_scraper().get(url, timeout=40)
    r.raise_for_status()

    out: list[dict] = []
    for rep in r.json().get("Replies", []):
        p = rep.get("pengumuman") or {}
        title = (p.get("JudulPengumuman") or "").strip()
        if not title:
            continue
        uid = str(p.get("Id2") or p.get("NoPengumuman") or title).strip()
        out.append({
            "published": p.get("TglPengumuman"),          # "2026-08-27T20:18:28"
            "title": title,
            "link": f"idx-disc://{uid}",
            "source": "IDX Disclosure",
            "summary": (p.get("PerihalPengumuman") or "").strip(),
        })
    return out


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
