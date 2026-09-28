"""Tugas terjadwal kecil yang jalan DI DALAM backend (backend nyala 24 jam di server, jadi jadwal
baru gak perlu bikin timer systemd sebagai root).

Update harga sore: Senin-Jumat jam 17.00 WIB (bursa tutup 16.00) tarik harga penutupan hari itu
+ IHSG & makro -> hasil hari itu (Rapor: kebeli/kejual, Jurnal: P/L & garis jual, chart) udah
kelihatan sore, gak nunggu pipeline 05.00 besoknya. Sekali sehari; kalau backend baru nyala
lewat jam 17.00, langsung dikejar. Gagal (mis. internet) = dicoba lagi hari bursa berikutnya.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

from trade.config import BASE_DIR, DATA_DIR

WIB = timezone(timedelta(hours=7))
JAM_SORE = (17, 0)
STEPS = [
    ["backfill_prices.py", "--focus", "--refresh", "--period", "5d"],   # harga saham dipantau
    ["fetch_macro.py"],                                                 # IHSG (pembanding Rapor) + makro
]


def _last_run_file():
    return DATA_DIR / ".harga_sore"   # isinya tanggal terakhir update sore


def due(now: datetime) -> bool:
    """Udah waktunya update sore hari ini dan belum jalan?"""
    if now.weekday() >= 5 or (now.hour, now.minute) < JAM_SORE:
        return False
    f = _last_run_file()
    return not (f.exists() and f.read_text(encoding="utf-8").strip() == now.date().isoformat())


def run_once(now: datetime | None = None) -> bool:
    """Jalanin update sore kalau udah waktunya. Return True kalau jalan."""
    now = now or datetime.now(WIB)
    if not due(now):
        return False
    _last_run_file().write_text(now.date().isoformat(), encoding="utf-8")   # tandai dulu: gak dobel
    env = {**os.environ, "TRADE_DATA_DIR": str(DATA_DIR)}                  # script nulis ke DB yang sama
    for step in STEPS:
        r = subprocess.run([sys.executable, str(BASE_DIR / "scripts" / step[0]), *step[1:]],
                           cwd=BASE_DIR, env=env, timeout=900, check=False)
        print(f"[update sore] {step[0]} selesai (exit {r.returncode})", flush=True)
    return True


def start() -> None:
    """Cek tiap menit di thread latar (daemon: ikut mati bareng backend)."""
    def loop() -> None:
        while True:
            try:
                run_once()
            except Exception as e:   # jangan sampai thread mati gara-gara 1 kegagalan
                print(f"[update sore] gagal: {e}", flush=True)
            time.sleep(60)

    threading.Thread(target=loop, name="update-sore", daemon=True).start()
