"""Jurnal trading (Fase 5) — catat trade REAL, lihat P/L + bandingin sama sistem.

  # catat posisi baru (1 lot = 100 lembar)
  python scripts/journal.py add BBCA --price 6475 --lot 2 --stop 6240 --target 6900 --note "ikut /analisa"

  # tutup posisi (pakai id dari report)
  python scripts/journal.py close 1 --price 6800

  # laporan (default kalau tanpa argumen)
  python scripts/journal.py

BUKAN nasihat / eksekusi — alat catat & evaluasi disiplin. P/L pakai model biaya IDX.
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from trade.db import get_connection, init_db            # noqa: E402
from trade.journal import add_trade, close_trade, norm_ticker, pl, summary  # noqa: E402


def _rp(x):
    try:
        return "Rp" + f"{int(round(float(x))):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def _pct(x):
    return "—" if x is None else f"{x*100:+.2f}%"


def _latest_prices(conn):
    return {r[0]: r[1] for r in conn.execute(
        "SELECT ticker, close FROM prices WHERE (ticker, date) IN "
        "(SELECT ticker, MAX(date) FROM prices GROUP BY ticker)")}


def cmd_add(conn, a):
    tid = add_trade(conn, a.ticker, a.price, a.lot, a.date, a.stop, a.target, a.note)
    extra = f"  stop {_rp(a.stop)}" if a.stop else ""
    print(f"✅ dicatat #{tid}: {norm_ticker(a.ticker)}  {a.lot:g} lot @ {_rp(a.price)}{extra}")


def cmd_close(conn, a):
    n = close_trade(conn, a.id, a.price, a.date)
    print(f"✅ trade #{a.id} ditutup @ {_rp(a.price)}" if n
          else f"⚠️  #{a.id} gak ketemu / udah closed")


def cmd_report(conn, _a):
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM journal ORDER BY entry_date DESC, id DESC")]
    if not rows:
        print("Jurnal masih kosong.\n  Catat: python scripts/journal.py add TICKER --price P --lot N")
        return

    price_of = _latest_prices(conn)
    sig = {r[0]: r[1] for r in conn.execute("SELECT ticker, action FROM signals")}
    op = [r for r in rows if r["status"] == "open"]
    cl = [r for r in rows if r["status"] == "closed"]

    if op:
        print("\n📌 POSISI TERBUKA")
        for r in op:
            cur = price_of.get(r["ticker"])
            p = pl(r, cur)
            warn = "  ⚠️ DI BAWAH STOP" if (r["stop"] and cur and cur < r["stop"]) else ""
            print(f"  #{r['id']:<3} {r['ticker']:11} {r['lot']:>4g} lot @ {_rp(r['entry'])}"
                  f"  → now {_rp(cur):>9}  {_pct(p['net_pct']):>8}  P/L {_rp(p['pl_rp']):>12}"
                  f"   [sistem: {sig.get(r['ticker'], '-')}]{warn}")

    if cl:
        print("\n✅ SUDAH DITUTUP")
        for r in cl:
            p = pl(r)
            print(f"  #{r['id']:<3} {r['ticker']:11} {_rp(r['entry'])} → {_rp(r['exit'])}"
                  f"  {_pct(p['net_pct']):>8}  P/L {_rp(p['pl_rp']):>12}"
                  f"   ({r['entry_date']} → {r['exit_date']})")

    s = summary(rows, price_of)
    print("\n" + "=" * 60)
    print(f"  Realized : {_rp(s['realized']):>14}   ({s['closed']} closed, "
          f"win {s['win_rate']*100:.0f}%)")
    print(f"  Open P/L : {_rp(s['unreal']):>14}   ({s['open']} posisi terbuka)")
    print(f"  TOTAL    : {_rp(s['total']):>14}")
    print("=" * 60)
    print("  P/L pakai model biaya IDX. Bukan nasihat — alat catat & evaluasi disiplin.")


def main():
    ap = argparse.ArgumentParser(description="Jurnal trading Fase 5")
    sub = ap.add_subparsers(dest="cmd")

    a = sub.add_parser("add", help="catat posisi baru")
    a.add_argument("ticker")
    a.add_argument("--price", type=float, required=True, help="harga masuk")
    a.add_argument("--lot", type=float, required=True, help="jumlah lot (1 lot=100 lembar)")
    a.add_argument("--stop", type=float)
    a.add_argument("--target", type=float)
    a.add_argument("--date", help="tanggal masuk YYYY-MM-DD (default: hari ini)")
    a.add_argument("--note", help="alasan/thesis masuk")

    c = sub.add_parser("close", help="tutup posisi")
    c.add_argument("id", type=int)
    c.add_argument("--price", type=float, required=True, help="harga keluar")
    c.add_argument("--date", help="tanggal keluar (default: hari ini)")

    sub.add_parser("report", help="laporan (default)")

    args = ap.parse_args()
    conn = get_connection()
    init_db(conn)
    {"add": cmd_add, "close": cmd_close, "report": cmd_report,
     None: cmd_report}[args.cmd](conn, args)


if __name__ == "__main__":
    main()
