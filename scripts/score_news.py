"""Skor sentimen (lexicon) berita di DB yang belum diskor — atau semua kalau --all. Langkah daily.py."""
import _bootstrap  # noqa: F401  (path repo + UTF-8)

import argparse

from trade.db import get_connection, init_db, update_news_sentiment_bulk
from trade.sentiment import LexiconScorer, strip_html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="skor ulang semua (bukan cuma yang kosong)")
    args = ap.parse_args()

    conn = get_connection()
    init_db(conn)
    scorer = LexiconScorer()

    where = "" if args.all else "WHERE sent_scorer IS NULL"
    rows = conn.execute(f"SELECT id, title, summary FROM news {where}").fetchall()
    print(f"Skor {len(rows)} berita pakai scorer '{scorer.name}'...\n", flush=True)

    updates = []
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    for r in rows:
        res = scorer.score(f"{r['title'] or ''}. {strip_html(r['summary'])}")
        counts[res["label"]] += 1
        updates.append((res["label"], res["score"], res["scorer"], r["id"]))
    n = update_news_sentiment_bulk(conn, updates)

    print(f"OK {n} berita diskor.")
    if n:
        print(f"   positif : {counts['positive']}")
        print(f"   netral  : {counts['neutral']}")
        print(f"   negatif : {counts['negative']}")

    for label, order in (("PALING POSITIF", "DESC"), ("PALING NEGATIF", "ASC")):
        print(f"\n  Contoh {label}:")
        for r in conn.execute("SELECT ticker, sent_score, title FROM news WHERE sent_score IS NOT NULL "
                              f"ORDER BY sent_score {order} LIMIT 3"):
            print(f"    [{r['sent_score']:+.2f}] {r['ticker']:9s} {(r['title'] or '')[:58]}")


if __name__ == "__main__":
    main()
