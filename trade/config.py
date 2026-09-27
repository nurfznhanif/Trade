"""Konfigurasi pusat: lokasi file data + baca/tulis .env."""
from __future__ import annotations

import os
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent   # root repo
# TRADE_DATA_DIR = pakai folder data lain, mis. SALINAN trade.db buat ngetes (jurnal asli gak kesentuh)
DATA_DIR = pathlib.Path(os.environ.get("TRADE_DATA_DIR") or BASE_DIR / "data")
DB_PATH = DATA_DIR / "trade.db"
ANALYSIS_PATH = DATA_DIR / "analysis.json"   # hasil analisa LLM terbaru (dibaca app)
BRIEF_PATH = DATA_DIR / "brief_latest.md"    # bahan analisa (ditulis scripts/brief.py)
ENV_PATH = BASE_DIR / ".env"                 # API key LLM + kunci akses server (gitignored)


def ensure_dirs() -> None:
    """Bikin folder data kalau belum ada."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def read_env() -> dict[str, str]:
    """Isi .env jadi dict (loader mini, gak butuh python-dotenv)."""
    env: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def write_env(updates: dict[str, str | None]) -> None:
    """Ubah baris .env. Nilai None = baris itu DIHAPUS. Baris lain (komentar dll) gak disentuh."""
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    done, out = set(), []
    for line in lines:
        s = line.strip()
        k = s.split("=", 1)[0].strip() if "=" in s and not s.startswith("#") else None
        if k in updates:
            done.add(k)
            if updates[k] is not None:
                out.append(f"{k}={updates[k]}")
        else:
            out.append(line)
    out += [f"{k}={v}" for k, v in updates.items() if k not in done and v is not None]
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
