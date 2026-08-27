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
from trade.sentiment import LexiconScorer, strip_html                     # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="skor ulang semua (bukan cuma yang kosong)")
    args = ap.parse_args()

    conn = get_connection()
    init_db(conn)
    scorer = LexiconScorer()

    where = "" if args.all else "WHERE sent_scorer IS NULL"
    rows = conn.execute(f"SELECT id, title, summary FROM news {where}").fetchall()
    print(f"🧠 Skor {len(rows)} berita pakai scorer '{scorer.name}'...\n")

    updates = []
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    for r in rows:
        text = f"{r['title'] or ''}. {strip_html(r['summary'])}"
        res = scorer.score(text)
        counts[res["label"]] += 1
        updates.append((res["label"], res["score"], res["scorer"], r["id"]))

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
