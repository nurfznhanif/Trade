"""Tarik daftar SEMUA saham (US + IDX) -> simpan ke tabel instruments."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from trade.db import get_connection, init_db, upsert_instruments_bulk   # noqa: E402
from trade.universe import fetch_idx_universe, fetch_us_universe         # noqa: E402


def main():
    conn = get_connection()
    init_db(conn)

    print("🌐 Ambil universe saham (daftar + metadata)...\n")

    print("  IDX (IDX resmi via cloudscraper)...", flush=True)
    idx = fetch_idx_universe()
    print(f"     ✓ {len(idx)} saham IDX")

    print("  US  (Nasdaq + NYSE/AMEX)...", flush=True)
    us = fetch_us_universe()
    print(f"     ✓ {len(us)} saham US (setelah buang ETF/warrant/test)")

    n = upsert_instruments_bulk(conn, idx + us)

    total = conn.execute("SELECT COUNT(*) FROM instruments").fetchone()[0]
    print(f"\n💾 Disimpan/diupdate: {n}.  Total instrumen di DB: {total}")
    print("   Rincian:")
    for market, cnt in conn.execute(
        "SELECT market, COUNT(*) AS cnt FROM instruments GROUP BY market ORDER BY cnt DESC"
    ):
        print(f"     {market:4s}: {cnt}")

    print("\nSelesai. 🚀  (langkah berat berikutnya: backfill harga)")


if __name__ == "__main__":
    main()
