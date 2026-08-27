"""Central config: paths + watchlist loading."""
from __future__ import annotations

import pathlib
from dataclasses import dataclass

import yaml

# Project root = folder yang berisi package `trade/`
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
WATCHLIST_PATH = CONFIG_DIR / "watchlist.yaml"
DB_PATH = DATA_DIR / "trade.db"


@dataclass
class Instrument:
    """Satu saham di watchlist."""
    ticker: str
    name: str
    market: str        # "US" atau "IDX"
    news_query: str
    news_lang: str     # "en" atau "id"


def load_watchlist(path: pathlib.Path | None = None) -> list[Instrument]:
    """Baca watchlist.yaml jadi list Instrument."""
    path = path or WATCHLIST_PATH
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    instruments: list[Instrument] = []
    for item in raw.get("instruments", []):
        name = item.get("name", item["ticker"])
        instruments.append(
            Instrument(
                ticker=item["ticker"],
                name=name,
                market=item.get("market", "US"),
                news_query=item.get("news_query", name),
                news_lang=item.get("news_lang", "en"),
            )
        )
    return instruments


def ensure_dirs() -> None:
    """Bikin folder runtime kalau belum ada."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
