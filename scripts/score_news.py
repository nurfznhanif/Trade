"""Skor sentimen semua berita di DB yang belum di-skor (atau semua kalau --all)."""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from trade.db import get_connection, init_db, update_news_sentiment_bulk  # noqa: E402
from trade.sentiment import get_scorer, strip_html                        # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="skor ulang semua (bukan cuma yang kosong)")
    ap.add_argument("--scorer", default="lexicon", help="lexicon (ringan) / indobert (NLP Indonesia)")
    args = ap.parse_args()

    conn = get_connection()
    init_db(conn)
    scorer = get_scorer(args.scorer)

    where = "" if args.all else "WHERE sent_scorer IS NULL"
    rows = conn.execute(f"SELECT id, title, summary FROM news {where}").fetchall()
    print(f"🧠 Skor {len(rows)} berita pakai scorer '{scorer.name}'...\n", flush=True)

    updates = []
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    CHUNK = 200
    for i in range(0, len(rows), CHUNK):
        chunk = rows[i:i + CHUNK]
        texts = [f"{r['title'] or ''}. {strip_html(r['summary'])}" for r in chunk]
        for r, res in zip(chunk, scorer.score_many(texts)):
            counts[res["label"]] += 1
            updates.append((res["label"], res["score"], res["scorer"], r["id"]))
        if len(rows) > CHUNK:
            print(f"  ...{min(i + CHUNK, len(rows))}/{len(rows)}", flush=True)

    n = update_news_sentiment_bulk(conn, updates)

    print(f"✓ {n} berita di-skor.")
    if n:
        print(f"   positif : {counts['positive']}")
        print(f"   netral  : {counts['neutral']}")
        print(f"   negatif : {counts['negative']}")

    # contoh hasil paling positif & paling negatif
    print("\n  Contoh PALING POSITIF:")
    for r in conn.execute(
        "SELECT ticker, sent_score, title FROM news "
        "WHERE sent_score IS NOT NULL ORDER BY sent_score DESC LIMIT 3"
    ):
        print(f"    [{r['sent_score']:+.2f}] {r['ticker']:9s} {(r['title'] or '')[:58]}")
    print("\n  Contoh PALING NEGATIF:")
    for r in conn.execute(
        "SELECT ticker, sent_score, title FROM news "
        "WHERE sent_score IS NOT NULL ORDER BY sent_score ASC LIMIT 3"
    ):
        print(f"    [{r['sent_score']:+.2f}] {r['ticker']:9s} {(r['title'] or '')[:58]}")


if __name__ == "__main__":
    main()
