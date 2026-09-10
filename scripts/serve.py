"""serve.py — nyalain BACKEND + TUNNEL sekali jalan buat app mobile.

Pakai (jalanin pas mau pakai app):
    .venv/Scripts/python.exe scripts/serve.py

Skrip ini:
  1. nyalain backend FastAPI di :8000
  2. nyalain tunnel cloudflared -> URL publik
  3. NYETAK URL-nya (tempel di app: Pengaturan -> Alamat Backend)
Tekan Ctrl+C buat matiin dua-duanya.

Butuh cloudflared di tools/cloudflared.exe (download sekali:
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe)
"""
from __future__ import annotations

import re
import subprocess
import sys
import threading
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CF = BASE / "tools" / "cloudflared.exe"


def main() -> None:
    procs: list[subprocess.Popen] = []

    print("• Nyalain backend (uvicorn) di :8000 …")
    procs.append(subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=str(BASE)))
    time.sleep(3)

    if not CF.exists():
        print(f"! cloudflared gak ketemu di {CF}")
        print("  Download sekali dari: https://github.com/cloudflare/cloudflared/releases/latest/"
              "download/cloudflared-windows-amd64.exe  -> taruh di tools/cloudflared.exe")
    else:
        print("• Nyalain tunnel (cloudflared) …")
        tun = subprocess.Popen([str(CF), "tunnel", "--url", "http://localhost:8000"],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        procs.append(tun)
        found: dict[str, str] = {}

        def drain(pipe):
            for line in pipe:                     # terus baca biar cloudflared gak macet
                if "url" not in found:
                    m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
                    if m:
                        found["url"] = m.group(0)

        threading.Thread(target=drain, args=(tun.stdout,), daemon=True).start()
        for _ in range(40):
            if "url" in found:
                break
            time.sleep(1)

        if "url" in found:
            print("\n" + "=" * 60)
            print("  ALAMAT BACKEND — tempel di app (Pengaturan → Alamat Backend):")
            print("  " + found["url"])
            print("=" * 60 + "\n")
        else:
            print("! Tunnel belum dapet URL (cek koneksi). Backend tetap jalan di http://localhost:8000")

    print("Backend + tunnel JALAN. Biarin jendela ini kebuka. Ctrl+C buat matiin.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nMatiin backend + tunnel …")
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    main()
