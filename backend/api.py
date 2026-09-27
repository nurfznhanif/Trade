"""api.py — backend FastAPI buat app HP Trade IDX. Endpoint dikelompokin per tab app di routes/.

Server cloud jalanin `uvicorn backend.api:app` (systemd, lihat deploy/setup_server.sh) —
JANGAN pindah/rename file ini, nanti server mati sampai unit systemd-nya diedit manual.

KUNCI AKSES: kalau TRADE_API_TOKEN diisi di .env (WAJIB di server), semua endpoint kecuali
/health minta header `X-Token`. Kosong = bebas (buat ngetes di PC).

Jalanin di PC:  .venv/Scripts/python.exe -m uvicorn backend.api:app --port 8000
"""
from __future__ import annotations

import os
import secrets
import subprocess

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from trade.config import ANALYSIS_PATH, BASE_DIR, read_env
from trade.llm import migrate_env

from .routes import analysis, journal, news, rapor, settings

migrate_env()   # .env format lama (LLM_API_KEY dll) -> LLM_KEY_<PROVIDER>
API_TOKEN = os.environ.get("TRADE_API_TOKEN") or read_env().get("TRADE_API_TOKEN", "")


def require_token(request: Request) -> None:
    """Server publik: tanpa kunci, orang lain bisa hapus jurnal / ganti API key LLM."""
    if not API_TOKEN or request.url.path == "/health":
        return
    if not secrets.compare_digest(request.headers.get("x-token", ""), API_TOKEN):
        raise HTTPException(401, "Kunci akses salah atau kosong. Isi 'Kunci Akses' di Pengaturan app.")


def _git_version() -> str:
    """Commit kode yang lagi jalan (biar kelihatan server udah auto-update apa belum)."""
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=BASE_DIR,
                              capture_output=True, text=True, timeout=5).stdout.strip() or "?"
    except Exception:
        return "?"


VERSION = _git_version()

app = FastAPI(title="Trade IDX API", dependencies=[Depends(require_token)])
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
for module in (analysis, news, journal, rapor, settings):
    app.include_router(module.router)


@app.get("/health")
def health():
    return {"ok": True, "analysis_ready": ANALYSIS_PATH.exists(), "version": VERSION}
