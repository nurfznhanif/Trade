"""Screener likuiditas: saring universe (ribuan saham) -> focus list yang layak-trade.

Prinsip corong: kita cuma mau ngeluarin tenaga (berita+sentimen) buat saham yang
LIKUID & bukan gorengan. Ukuran utama: *turnover* harian rata2 = harga x volume.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScreenParams:
    lookback: int = 20                 # jumlah hari terakhir buat hitung rata2
    min_ndays: int = 15                # minimal hari data (buang yg terlalu sepi/baru)

    us_min_price: float = 2.0                   # USD
    us_min_turnover: float = 5_000_000          # USD/hari

    idx_min_price: float = 100.0                # IDR
    idx_min_turnover: float = 5_000_000_000     # IDR/hari (5 miliar)
    idx_skip_boards: tuple = ("Acceleration",)  # papan startup mini -> skip


_METRIC_SQL = """
WITH ranked AS (
    SELECT ticker, date, close, volume,
           ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn
    FROM prices
)
SELECT ticker,
       COUNT(*)                              AS ndays,
       MAX(CASE WHEN rn = 1 THEN close END)  AS last_close,
       AVG(close * volume)                   AS avg_turnover,
       AVG(volume)                           AS avg_volume
FROM ranked
WHERE rn <= ?
GROUP BY ticker
"""


def screen(conn, p: ScreenParams | None = None) -> list[dict]:
    """Kembalikan daftar saham yang lolos, terurut turnover terbesar dulu."""
    p = p or ScreenParams()

    metrics = conn.execute(_METRIC_SQL, (p.lookback,)).fetchall()
    meta = {r["ticker"]: r for r in conn.execute(
        "SELECT ticker, name, market, board FROM instruments")}

    passed: list[dict] = []
    for r in metrics:
        m = meta.get(r["ticker"])
        if not m:
            continue

        last_close = r["last_close"]
        turnover = r["avg_turnover"] or 0.0
        if last_close is None or r["ndays"] < p.min_ndays:
            continue

        market = m["market"]
        if market == "US":
            if last_close < p.us_min_price or turnover < p.us_min_turnover:
                continue
        elif market == "IDX":
            if (m["board"] in p.idx_skip_boards
                    or last_close < p.idx_min_price
                    or turnover < p.idx_min_turnover):
                continue
        else:
            continue

        passed.append({
            "ticker": r["ticker"], "name": m["name"], "market": market,
            "board": m["board"], "last_close": last_close,
            "avg_turnover": turnover, "avg_volume": r["avg_volume"],
            "ndays": r["ndays"],
        })

    passed.sort(key=lambda x: x["avg_turnover"], reverse=True)
    return passed
