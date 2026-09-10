"""newsbody.py — baca ISI artikel berita TANPA API berbayar (pengganti Tavily).

Alur: shell Google News (udah tersimpan di DB) -> decode URL media asli
      (googlenewsdecoder) -> tarik + bersihin badan artikel (trafilatura).
Fallback kalau kosong: cari via ddgs (DuckDuckGo, keyless).

100% lokal, NOL API/kredit. Satu-satunya dependency eksternal yang tersisa = LLM.
"""
from __future__ import annotations

import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def resolve_url(shell: str | None) -> str | None:
    """Shell Google News -> URL media asli. None kalau gagal.
    URL yang bukan cangkang Google dikembalikan apa adanya."""
    if not shell:
        return None
    if "news.google.com" not in shell:
        return shell
    try:
        from googlenewsdecoder import gnewsdecoder
        d = gnewsdecoder(shell, interval=0.4)
        return d.get("decoded_url") if d.get("status") else None
    except Exception:
        return None


def fetch_body(url: str | None, max_chars: int = 1600) -> str | None:
    """Tarik + sabut badan artikel (teks bersih). None kalau gagal/kosong."""
    if not url:
        return None
    try:
        import trafilatura
        r = requests.get(url, timeout=12, headers={"User-Agent": _UA})
        if r.status_code != 200 or not r.text:
            return None
        txt = trafilatura.extract(r.text, include_comments=False, include_tables=False,
                                  favor_precision=True)
        if not txt:
            return None
        return re.sub(r"\s+", " ", txt).strip()[:max_chars]
    except Exception:
        return None


def ddg_urls(query: str, n: int = 1) -> list[str]:
    """Cadangan: cari URL media via DuckDuckGo (keyless)."""
    try:
        from ddgs import DDGS
        res = DDGS().text(query, region="id-id", max_results=n + 4)
        bad = ("google.", "youtube.", "facebook.", "tradingview.", "investing.com",
               "finance.yahoo", "pluang.com", "ajaib.co")
        out = [r.get("href") for r in res
               if r.get("href") and not any(b in r["href"] for b in bad)]
        return out[:n]
    except Exception:
        return []


def _article_body(shell: str) -> str | None:
    return fetch_body(resolve_url(shell))


def bodies_for(conn: sqlite3.Connection, tickers: list[str], per: int = 2,
               days: int = 12, workers: int = 4) -> str:
    """Blok '## BADAN ARTIKEL' untuk dicolok ke prompt LLM.

    Per ticker ambil `per` berita terbaru dari DB -> decode -> sabut badan (paralel).
    Ticker yang kosong -> fallback cari via ddgs."""
    conn.row_factory = sqlite3.Row
    names = {r["ticker"]: r["name"] for r in conn.execute("SELECT ticker, name FROM instruments")}
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    tasks: list[tuple[str, str, str]] = []  # (ticker, title, shell)
    for t in tickers:
        for r in conn.execute(
                "SELECT title, link FROM news WHERE ticker=? AND title IS NOT NULL "
                "AND (published IS NULL OR published>=?) ORDER BY published DESC LIMIT ?",
                (t, since, per)):
            if r["link"]:
                tasks.append((t, r["title"], r["link"]))

    with ThreadPoolExecutor(max_workers=workers) as ex:
        bodies = list(ex.map(lambda x: _article_body(x[2]), tasks))

    per_ticker: dict[str, list[tuple[str, str]]] = {}
    for (t, title, _), body in zip(tasks, bodies):
        if body and len(body) > 120:
            per_ticker.setdefault(t, []).append((title, body))

    # fallback ddgs buat ticker yang belum dapet badan
    for t in tickers:
        if per_ticker.get(t):
            continue
        short = t.replace(".JK", "")
        for u in ddg_urls(f"{names.get(t, short)} {short} saham berita terbaru", 1):
            b = fetch_body(u)
            if b and len(b) > 120:
                per_ticker.setdefault(t, []).append((f"(pencarian) {short}", b))
                break

    out = ["## BADAN ARTIKEL (isi berita, dibaca LOKAL tanpa API) — WAJIB cross-check judul vs isi"]
    got = 0
    for t in tickers:
        arts = per_ticker.get(t)
        if not arts:
            continue
        got += 1
        out.append(f"### {t}")
        for title, body in arts:
            out.append(f"  [{title[:85]}]")
            out.append(f"  ISI: {body}")
    print(f"  Baca badan artikel: {got}/{len(tickers)} saham (decode + trafilatura, no API)")
    return "\n".join(out) if got else ""
