"""Tarik daftar saham sesuai config MARKETS -> simpan ke instruments + buang pasar lain."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from trade.config import MARKETS                                     # noqa: E402
from trade.db import (get_connection, init_db, prune_to_markets,     # noqa: E402
                      upsert_instruments_bulk)
from trade.universe import fetch_idx_universe, fetch_us_universe     # noqa: E402


def main():
    conn = get_connection()
    init_db(conn)

    print(f"🌐 Universe buat pasar: {', '.join(MARKETS)}\n")
    items = []
    if "IDX" in MARKETS:
        print("  IDX (IDX resmi via cloudscraper)...", flush=True)
        idx = fetch_idx_universe()
        print(f"     ✓ {len(idx)} saham IDX")
        items += idx
    if "US" in MARKETS:
        print("  US (Nasdaq + NYSE/AMEX)...", flush=True)
        us = fetch_us_universe()
        print(f"     ✓ {len(us)} saham US")
        items += us

    n = upsert_instruments_bulk(conn, items)
    dropped = prune_to_markets(conn, MARKETS)

    total = conn.execute("SELECT COUNT(*) FROM instruments").fetchone()[0]
    print(f"\n💾 Disimpan/diupdate: {n}. Instrumen pasar lain dibuang: {dropped}.")
    print(f"   Total instrumen sekarang: {total}")
    for market, cnt in conn.execute(
        "SELECT market, COUNT(*) AS cnt FROM instruments GROUP BY market ORDER BY cnt DESC"
    ):
        print(f"     {market:4s}: {cnt}")


if __name__ == "__main__":
    main()
