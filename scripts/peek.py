"""Intip isi database: harga terbaru + contoh berita per saham."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from trade.db import get_connection   # noqa: E402


def main():
    conn = get_connection()
    tickers = [r["ticker"] for r in
               conn.execute("SELECT ticker FROM instruments ORDER BY market, ticker")]

    print("=" * 72)
    print(" HARGA TERBARU")
    print("=" * 72)
    for tk in tickers:
        n = conn.execute("SELECT COUNT(*) FROM prices WHERE ticker=?", (tk,)).fetchone()[0]
        last = conn.execute(
            "SELECT date, close FROM prices WHERE ticker=? ORDER BY date DESC LIMIT 1", (tk,)
        ).fetchone()
        if last:
            print(f"  {tk:10s} {last['date']}  close={last['close']:<12}  ({n} baris)")

    print("\n" + "=" * 72)
    print(" CONTOH BERITA (3 terbaru per saham)")
    print("=" * 72)
    for tk in tickers:
        print(f"\n  [{tk}]")
        for r in conn.execute(
            "SELECT published, title, source FROM news "
            "WHERE ticker=? ORDER BY published DESC LIMIT 3", (tk,)
        ):
            pub = (r["published"] or "----------")[:10]
            print(f"    {pub}  {(r['title'] or '')[:66]}")


if __name__ == "__main__":
    main()
