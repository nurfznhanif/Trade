"""Cadangan jurnal asli: isi tabel journal -> data/backup/jurnal_<tanggal>.json, simpan 30 terakhir.
Langkah pertama daily.py (tiap pagi). Kecil (cuma catatan trade), jadi aman disimpan sebulan.

  python scripts/backup_jurnal.py
  python scripts/backup_jurnal.py --restore data/backup/jurnal_2026-10-01.json   # cuma kalau jurnal kosong
"""
import _bootstrap  # noqa: F401  (path repo + UTF-8)

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from trade import journal
from trade.config import DATA_DIR
from trade.db import get_connection, init_db

KEEP = 30


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--restore", help="file cadangan yang mau dipulihkan (jurnal harus kosong)")
    args = ap.parse_args()

    conn = get_connection()
    init_db(conn)

    if args.restore:
        data = json.loads(Path(args.restore).read_text(encoding="utf-8"))
        print(f"Dipulihkan {journal.restore(conn, data['trades'])} catatan dari {args.restore}")
        return

    folder = DATA_DIR / "backup"
    folder.mkdir(parents=True, exist_ok=True)
    rows = journal.export_rows(conn)
    now = datetime.now(timezone.utc)
    out = folder / f"jurnal_{now.date().isoformat()}.json"
    out.write_text(json.dumps({"created": now.isoformat(timespec="seconds"), "count": len(rows), "trades": rows},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    old = sorted(folder.glob("jurnal_*.json"))[:-KEEP]
    for f in old:
        f.unlink()
    print(f"Cadangan jurnal: {len(rows)} catatan -> {out.name} ({len(old)} cadangan lama dibuang, simpan {KEEP})")


if __name__ == "__main__":
    main()
