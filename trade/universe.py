"""Ambil 'universe' — daftar SEMUA saham yang bisa ditradingkan.

US  : file simbol resmi nasdaqtrader (nasdaqlisted + otherlisted). Gratis, HTTP biasa.
IDX : endpoint resmi IDX, ditembus pakai cloudscraper (di balik Cloudflare).

Catatan: ini cuma narik DAFTAR + metadata (cepat, sekali jalan).
Harga per saham ditarik terpisah (lihat scripts/backfill_prices.py) karena berat.
"""
from __future__ import annotations

import cloudscraper
import requests

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Karakter yang nandain simbol non-common (warrant/unit/preferred/right/class)
_WEIRD_CHARS = set(".$+=^ /\\")


def fetch_idx_universe() -> list[dict]:
    """Semua saham tercatat di IDX. Ticker dikasih suffix .JK biar cocok yfinance."""
    url = ("https://www.idx.co.id/primary/StockData/GetSecuritiesStock"
           "?start=0&length=10000&code=&sector=&board=&language=en-us")
    scraper = cloudscraper.create_scraper(browser={"browser": "chrome", "platform": "windows"})
    r = scraper.get(url, timeout=60)
    r.raise_for_status()

    out: list[dict] = []
    for row in r.json().get("data", []):
        code = (row.get("Code") or "").strip()
        if not code:
            continue
        out.append({
            "ticker": f"{code}.JK",
            "name": (row.get("Name") or "").strip(),
            "market": "IDX",
            "exchange": "IDX",
            "board": row.get("ListingBoard"),   # Main / Development / Acceleration
        })
    return out


def fetch_us_universe() -> list[dict]:
    """Semua common stock Nasdaq + NYSE/AMEX. Buang ETF, test issue, warrant, dll."""
    return _parse_nasdaqlisted() + _parse_otherlisted()


def _get_lines(url: str) -> list[str]:
    r = requests.get(url, headers=_UA, timeout=30)
    r.raise_for_status()
    return r.text.splitlines()


def _is_common(symbol: str) -> bool:
    """Heuristik ringan: buang simbol yang mengandung karakter kelas/warrant."""
    return bool(symbol) and not any(c in _WEIRD_CHARS for c in symbol)


def _parse_nasdaqlisted() -> list[dict]:
    # Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares
    out: list[dict] = []
    for line in _get_lines("https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt")[1:]:
        if line.startswith("File Creation Time"):
            continue
        f = line.split("|")
        if len(f) < 8:
            continue
        symbol, name, test_issue, etf = f[0].strip(), f[1].strip(), f[3], f[6]
        if test_issue == "Y" or etf == "Y" or not _is_common(symbol):
            continue
        out.append({"ticker": symbol, "name": name, "market": "US",
                    "exchange": "NASDAQ", "board": None})
    return out


def _parse_otherlisted() -> list[dict]:
    # ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol
    exch_map = {"A": "NYSE American", "N": "NYSE", "P": "NYSE Arca", "Z": "Cboe BZX", "V": "IEX"}
    out: list[dict] = []
    for line in _get_lines("https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt")[1:]:
        if line.startswith("File Creation Time"):
            continue
        f = line.split("|")
        if len(f) < 8:
            continue
        symbol, name, exch, etf, test_issue = f[0].strip(), f[1].strip(), f[2], f[4], f[6]
        if test_issue == "Y" or etf == "Y" or not _is_common(symbol):
            continue
        out.append({"ticker": symbol, "name": name, "market": "US",
                    "exchange": exch_map.get(exch, exch), "board": None})
    return out
