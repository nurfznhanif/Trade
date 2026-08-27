"""Bikin database + daftarin semua saham dari watchlist."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")   # biar emoji gak error di Windows
except Exception:
    pass

from trade.config import load_watchlist          # noqa: E402
from trade.db import get_connection, init_db, upsert_instrument  # noqa: E402


def main():
    conn = get_connection()
    init_db(conn)

    wl = load_watchlist()
    for ins in wl:
        upsert_instrument(conn, ins.ticker, ins.name, ins.market)

    print(f"✓ Database siap. {len(wl)} instrumen terdaftar:")
    for ins in wl:
        print(f"   • {ins.ticker:10s} {ins.name}  [{ins.market}]")


if __name__ == "__main__":
    main()
