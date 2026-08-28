"""SQLite storage layer: skema + helper simpan data."""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from typing import Iterable

from .config import DB_PATH, ensure_dirs

SCHEMA = """
CREATE TABLE IF NOT EXISTS instruments (
    ticker    TEXT PRIMARY KEY,
    name      TEXT,
    market    TEXT,
    exchange  TEXT,
    board     TEXT,
    updated   TEXT
);

CREATE TABLE IF NOT EXISTS prices (
    ticker  TEXT NOT NULL,
    date    TEXT NOT NULL,        -- ISO date YYYY-MM-DD
    open    REAL,
    high    REAL,
    low     REAL,
    close   REAL,
    volume  INTEGER,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS news (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker      TEXT NOT NULL,
    published   TEXT,             -- ISO datetime (UTC)
    title       TEXT,
    link        TEXT,
    source      TEXT,
    summary     TEXT,
    fetched_at  TEXT,
    sent_label  TEXT,             -- positive / negative / neutral
    sent_score  REAL,             -- -1..1
    sent_scorer TEXT,             -- nama scorer yang dipakai (lexicon/finbert/...)
    title_key   TEXT,             -- judul dinormalisasi (buat dedup lintas sumber)
    UNIQUE (ticker, link)         -- cegah berita dobel (link sama)
);

CREATE TABLE IF NOT EXISTS focus_list (
    ticker        TEXT PRIMARY KEY,
    market        TEXT,
    last_close    REAL,
    avg_turnover  REAL,          -- rata2 nilai transaksi harian (close*volume)
    avg_volume    REAL,
    ndays         INTEGER,
    rank          INTEGER,
    updated       TEXT
);

CREATE TABLE IF NOT EXISTS signals (
    ticker  TEXT PRIMARY KEY,
    market  TEXT,
    asof    TEXT,          -- tanggal harga terakhir yang dipakai
    action  TEXT,          -- BUY / HOLD / SELL
    score   REAL,
    close   REAL,
    ma20    REAL,
    ma50    REAL,
    rsi     REAL,
    sent    REAL,
    n_news  INTEGER,
    stop    REAL,
    target  REAL,
    reasons TEXT,          -- JSON list alasan
    updated TEXT
);

CREATE TABLE IF NOT EXISTS paper_state (
    id             INTEGER PRIMARY KEY CHECK (id = 1),
    inception_date TEXT,      -- tanggal mulai paper trading (dikunci sekali)
    start_capital  REAL,
    created        TEXT
);

CREATE TABLE IF NOT EXISTS fundamentals (
    ticker      TEXT PRIMARY KEY,
    per         REAL,      -- Price/Earnings
    pbv         REAL,      -- Price/Book
    roe         REAL,      -- Return on Equity
    der         REAL,      -- Debt/Equity
    div_yield   REAL,
    margin      REAL,      -- profit margin
    market_cap  REAL,
    updated     TEXT
);

CREATE INDEX IF NOT EXISTS idx_prices_ticker_date ON prices (ticker, date);
CREATE INDEX IF NOT EXISTS idx_news_ticker_pub    ON news   (ticker, published);
"""


def get_connection(db_path=None) -> sqlite3.Connection:
    """Buka koneksi SQLite (bikin folder data/ dulu kalau perlu)."""
    ensure_dirs()
    conn = sqlite3.connect(str(db_path or DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Bikin tabel-tabel kalau belum ada, + migrasi kolom baru."""
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.commit()


def _migrate(conn: sqlite3.Connection) -> None:
    """Tambah kolom yang belum ada di DB lama (biar gak perlu hapus DB)."""
    _add_columns(conn, "instruments", {"exchange": "TEXT", "board": "TEXT"})
    _add_columns(conn, "news",
                 {"sent_label": "TEXT", "sent_score": "REAL", "sent_scorer": "TEXT",
                  "title_key": "TEXT"})


def _add_columns(conn: sqlite3.Connection, table: str, cols: dict) -> None:
    have = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    for name, typ in cols.items():
        if name not in have:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def upsert_instrument(conn, ticker: str, name: str, market: str) -> None:
    conn.execute(
        "INSERT INTO instruments (ticker, name, market, updated) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(ticker) DO UPDATE SET "
        "name=excluded.name, market=excluded.market, updated=excluded.updated",
        (ticker, name, market, _now_iso()),
    )
    conn.commit()


def upsert_instruments_bulk(conn, items: Iterable[dict]) -> int:
    """Simpan/update banyak instrumen sekaligus (buat universe ribuan saham)."""
    now = _now_iso()
    rows = [
        (it["ticker"], it.get("name"), it.get("market"),
         it.get("exchange"), it.get("board"), now)
        for it in items
    ]
    if not rows:
        return 0
    conn.executemany(
        "INSERT INTO instruments (ticker, name, market, exchange, board, updated) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(ticker) DO UPDATE SET "
        "name=excluded.name, market=excluded.market, exchange=excluded.exchange, "
        "board=excluded.board, updated=excluded.updated",
        rows,
    )
    conn.commit()
    return len(rows)


def upsert_prices(conn, ticker: str, rows: Iterable[tuple]) -> int:
    """rows: iterable of (date, open, high, low, close, volume). Return jumlah baris."""
    data = [(ticker, *r) for r in rows]
    if not data:
        return 0
    conn.executemany(
        "INSERT OR REPLACE INTO prices "
        "(ticker, date, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
        data,
    )
    conn.commit()
    return len(data)


_TK_RE = re.compile(r"[^a-z0-9 ]+")


def title_key(title: str | None) -> str | None:
    """Normalisasi judul buat dedup lintas sumber (buang ' - Publisher', simbol, dll)."""
    if not title:
        return None
    base = title.rsplit(" - ", 1)[0].lower()   # buang ekor ' - Nama Media'
    base = " ".join(_TK_RE.sub(" ", base).split())
    return base[:90] or None


def insert_news(conn, ticker: str, items: Iterable[dict]) -> int:
    """Simpan berita. Dedup 2 lapis: link sama (UNIQUE) + JUDUL mirip (title_key),
    biar berita sama dari beda sumber gak kehitung dobel. Return baris BARU."""
    existing = {r[0] for r in conn.execute(
        "SELECT title_key FROM news WHERE ticker = ? AND title_key IS NOT NULL", (ticker,))}
    seen = set(existing)

    rows = []
    for it in items:
        tk = title_key(it.get("title"))
        if tk and tk in seen:
            continue                      # judul udah ada (sumber lain / batch ini)
        if tk:
            seen.add(tk)
        rows.append((ticker, it.get("published"), it.get("title"), it.get("link"),
                     it.get("source"), it.get("summary"), _now_iso(), tk))
    if not rows:
        return 0

    before = conn.total_changes
    conn.executemany(
        "INSERT OR IGNORE INTO news "
        "(ticker, published, title, link, source, summary, fetched_at, title_key) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return conn.total_changes - before


def upsert_fundamentals_bulk(conn, items) -> int:
    """Simpan/update rasio fundamental per saham."""
    now = _now_iso()
    rows = [(it["ticker"], it.get("per"), it.get("pbv"), it.get("roe"), it.get("der"),
             it.get("div_yield"), it.get("margin"), it.get("market_cap"), now)
            for it in items]
    if not rows:
        return 0
    conn.executemany(
        "INSERT INTO fundamentals "
        "(ticker, per, pbv, roe, der, div_yield, margin, market_cap, updated) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(ticker) DO UPDATE SET "
        "per=excluded.per, pbv=excluded.pbv, roe=excluded.roe, der=excluded.der, "
        "div_yield=excluded.div_yield, margin=excluded.margin, "
        "market_cap=excluded.market_cap, updated=excluded.updated",
        rows,
    )
    conn.commit()
    return len(rows)


def get_or_init_paper_state(conn, inception_date: str, start_capital: float):
    """Ambil state paper trading; kalau belum ada, kunci inception + modal awal."""
    conn.execute(
        "INSERT OR IGNORE INTO paper_state (id, inception_date, start_capital, created) "
        "VALUES (1, ?, ?, ?)", (inception_date, start_capital, _now_iso()))
    conn.commit()
    return conn.execute("SELECT * FROM paper_state WHERE id = 1").fetchone()


def backfill_title_keys(conn) -> int:
    """Isi title_key buat baris lama yang masih kosong (sekali jalan)."""
    rows = conn.execute("SELECT id, title FROM news WHERE title_key IS NULL").fetchall()
    ups = [(title_key(r["title"]), r["id"]) for r in rows]
    ups = [(k, i) for k, i in ups if k]
    if ups:
        conn.executemany("UPDATE news SET title_key = ? WHERE id = ?", ups)
        conn.commit()
    return len(ups)


def replace_focus_list(conn, items) -> int:
    """Ganti total isi focus_list dengan hasil screener terbaru (items sudah terurut)."""
    now = _now_iso()
    conn.execute("DELETE FROM focus_list")
    conn.executemany(
        "INSERT INTO focus_list "
        "(ticker, market, last_close, avg_turnover, avg_volume, ndays, rank, updated) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [(it["ticker"], it["market"], it["last_close"], it["avg_turnover"],
          it["avg_volume"], it["ndays"], i + 1, now)
         for i, it in enumerate(items)],
    )
    conn.commit()
    return len(items)


def update_news_sentiment_bulk(conn, rows) -> int:
    """rows: iterable of (sent_label, sent_score, sent_scorer, news_id)."""
    rows = list(rows)
    if not rows:
        return 0
    conn.executemany(
        "UPDATE news SET sent_label=?, sent_score=?, sent_scorer=? WHERE id=?", rows
    )
    conn.commit()
    return len(rows)


def replace_signals(conn, items) -> int:
    """Ganti total isi tabel signals dengan hasil generate terbaru."""
    now = _now_iso()
    conn.execute("DELETE FROM signals")
    conn.executemany(
        "INSERT INTO signals "
        "(ticker, market, asof, action, score, close, ma20, ma50, rsi, sent, "
        " n_news, stop, target, reasons, updated) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(it["ticker"], it["market"], it["asof"], it["action"], it["score"],
          it["close"], it["ma20"], it["ma50"], it["rsi"], it["sent"],
          it["n_news"], it["stop"], it["target"], it["reasons"], now)
         for it in items],
    )
    conn.commit()
    return len(items)


def prune_to_markets(conn, markets) -> int:
    """Hapus SEMUA data (harga/berita/focus/sinyal/instrumen) buat pasar di luar `markets`.
    Return jumlah instrumen yang dibuang. Reversible: tinggal load_universe + backfill lagi."""
    ph = ",".join("?" * len(markets))
    drop = f"(SELECT ticker FROM instruments WHERE market NOT IN ({ph}))"
    conn.execute(f"DELETE FROM prices WHERE ticker IN {drop}", markets)
    conn.execute(f"DELETE FROM news   WHERE ticker IN {drop}", markets)
    conn.execute(f"DELETE FROM focus_list WHERE market NOT IN ({ph})", markets)
    conn.execute(f"DELETE FROM signals    WHERE market NOT IN ({ph})", markets)
    cur = conn.execute(f"DELETE FROM instruments WHERE market NOT IN ({ph})", markets)
    conn.commit()
    return cur.rowcount
