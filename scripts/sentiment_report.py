"""Leaderboard sentimen: saham dengan berita paling POSITIF / NEGATIF belakangan.

Ini rangkuman Fase 1 — nunjukin sentimen tiap saham (rata2 skor berita terbaru).
"""
import argparse
import pathlib
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from trade.db import get_connection, init_db   # noqa: E402

_Q = """
SELECT n.ticker, i.name, i.market,
       COUNT(*)                                        AS n_news,
       AVG(n.sent_score)                               AS avg_sent,
       SUM(CASE WHEN n.sent_label='positive' THEN 1 ELSE 0 END) AS npos,
       SUM(CASE WHEN n.sent_label='negative' THEN 1 ELSE 0 END) AS nneg
FROM news n
JOIN instruments i ON i.ticker = n.ticker
WHERE n.sent_score IS NOT NULL
  AND (n.published IS NULL OR n.published >= ?)
GROUP BY n.ticker
HAVING n_news >= ?
"""


def _flag(market):
    return "🇮🇩" if market == "IDX" else "🇺🇸"


def _line(r):
    return (f"    {_flag(r['market'])} {r['ticker']:10s} {r['avg_sent']:+.2f}  "
            f"({r['n_news']:>2} berita: {r['npos']}+/{r['nneg']}-)  {(r['name'] or '')[:30]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--min-news", type=int, default=3)
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args()

    conn = get_connection()
    init_db(conn)
    since = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat(timespec="seconds")

    rows = conn.execute(_Q, (since, args.min_news)).fetchall()
    rows = [r for r in rows if r["avg_sent"] is not None]
    rows.sort(key=lambda r: r["avg_sent"], reverse=True)

    print("=" * 68)
    print(f" LEADERBOARD SENTIMEN  ({args.days} hari, min {args.min_news} berita/saham)")
    print("=" * 68)
    print(f"  Saham dengan sentimen terhitung: {len(rows)}\n")

    print(f"  🟢 PALING POSITIF (top {args.top}):")
    for r in rows[:args.top]:
        print(_line(r))

    print(f"\n  🔴 PALING NEGATIF (top {args.top}):")
    for r in rows[-args.top:][::-1]:
        print(_line(r))


if __name__ == "__main__":
    main()
