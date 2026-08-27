"""Paper trading — simulasi portfolio maju ke depan (duit bohongan).

Reuse mesin sinyal/backtest buat hasilin KANDIDAT trade, terus di sini diterapin
batasan PORTFOLIO nyata: modal terbatas, jumlah posisi terbatas (slot), equal-weight.
Event-driven: posisi lama keluar dulu -> slot bebas -> baru bisa masuk yang baru.

Trade dgn outcome 'EOD' (mentok data terakhir) = posisi yang MASIH TERBUKA sekarang
(belum kena stop/target), jadi dihitung unrealized (mark-to-market harga terakhir).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PaperParams:
    start_capital: float = 100_000_000    # Rp 100 juta
    max_positions: int = 10               # maksimal posisi barengan (slot)


def simulate_portfolio(trades: list[dict], pp: PaperParams) -> dict:
    """trades: butuh keys entry_ord, exit_ord, ret, outcome, ticker, entry_date, exit_date.
    (ret = return net per-trade dari backtest.) Return ringkasan portfolio."""
    trades = sorted(trades, key=lambda t: t["entry_ord"])
    alloc = pp.start_capital / pp.max_positions

    open_pos: list[dict] = []
    taken: list[dict] = []
    slots = pp.max_positions

    for t in trades:
        # bebasin slot posisi yang udah keluar sebelum entry ini
        keep = []
        for p in open_pos:
            if p["exit_ord"] <= t["entry_ord"]:
                slots += 1
            else:
                keep.append(p)
        open_pos = keep

        if slots > 0:                     # ada slot -> ambil trade
            slots -= 1
            open_pos.append(t)
            taken.append(t)
        # kalau penuh -> sinyal dilewat (realita portfolio)

    realized = unreal = 0.0
    closed, still_open = [], []
    for t in taken:
        pnl = alloc * t["ret"]
        if t["outcome"] == "EOD":         # masih kebuka sekarang
            unreal += pnl
            still_open.append(t)
        else:
            realized += pnl
            closed.append(t)

    equity = pp.start_capital + realized + unreal
    wins = [t for t in closed if t["ret"] > 0]
    return {
        "start": pp.start_capital, "equity": equity,
        "ret_pct": equity / pp.start_capital - 1.0,
        "realized": realized, "unreal": unreal, "alloc": alloc,
        "n_taken": len(taken), "n_closed": len(closed), "n_open": len(still_open),
        "win_rate": (len(wins) / len(closed)) if closed else 0.0,
        "open_positions": still_open, "closed_trades": closed,
    }
