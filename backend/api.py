"""api.py — backend FastAPI buat app mobile Trade IDX.

Nyediain: hasil analisa terbaru, jalanin auto_analisa on-demand, dan atur LLM
(bongkar-pasang provider + key). Badan artikel dibaca lokal (trafilatura) — jadi
satu-satunya API eksternal = LLM yang dipilih di /config/llm.

Jalanin:
  .venv/Scripts/python.exe -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
ANALYSIS = BASE / "data" / "analysis.json"
ENV = BASE / ".env"

from trade import llm  # noqa: E402

app = FastAPI(title="Trade IDX API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ---------------------------------------------------------------- .env helpers
def read_env() -> dict:
    d: dict[str, str] = {}
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                d[k.strip()] = v.strip()
    return d


def write_env(updates: dict) -> None:
    lines = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    done, out = set(), []
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s and s.split("=", 1)[0].strip() in updates:
            k = s.split("=", 1)[0].strip()
            out.append(f"{k}={updates[k]}")
            done.add(k)
        else:
            out.append(line)
    for k, v in updates.items():
        if k not in done:
            out.append(f"{k}={v}")
    ENV.write_text("\n".join(out) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- endpoints
@app.get("/health")
def health():
    return {"ok": True, "analysis_ready": ANALYSIS.exists()}


@app.get("/analysis")
def get_analysis():
    """Hasil analisa terbaru (data/analysis.json)."""
    if not ANALYSIS.exists():
        raise HTTPException(404, "Belum ada analisa. POST /analisa dulu.")
    return json.loads(ANALYSIS.read_text(encoding="utf-8"))


@app.post("/analisa")
def run_analisa(modal: str | None = None):
    """Jalanin auto_analisa (baca data+berita -> LLM -> tulis analysis.json). ~1-2 menit."""
    cmd = [sys.executable, str(BASE / "scripts" / "auto_analisa.py"), "--out", str(ANALYSIS)]
    if modal:
        cmd += ["--modal", modal]
    try:
        p = subprocess.run(cmd, cwd=str(BASE), capture_output=True, text=True, timeout=420)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "auto_analisa timeout (>7 menit).")
    if p.returncode != 0:
        raise HTTPException(500, f"auto_analisa gagal: {(p.stderr or p.stdout)[-600:]}")
    return json.loads(ANALYSIS.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- config LLM
class LLMConfig(BaseModel):
    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None


@app.get("/config/llm")
def get_llm():
    """Config LLM aktif + daftar provider (buat menu Pengaturan di app). Key TIDAK dibocorin."""
    env = read_env()
    c = llm.resolve(env)
    return {
        "provider": c["provider"], "model": c["model"], "label": c["label"],
        "base_url": env.get("LLM_BASE_URL", ""), "has_key": bool(c["key"]),
        "providers": {k: {"label": v["label"], "models": v["models"],
                          "key_url": v["key_url"], "openai": v["openai"]}
                      for k, v in llm.PROVIDERS.items()},
    }


@app.post("/config/llm")
def set_llm(cfg: LLMConfig):
    upd = {"LLM_PROVIDER": cfg.provider, "LLM_MODEL": cfg.model}
    if cfg.api_key is not None:
        upd["LLM_API_KEY"] = cfg.api_key
    if cfg.base_url is not None:
        upd["LLM_BASE_URL"] = cfg.base_url
    write_env(upd)
    return {"ok": True}


@app.post("/config/llm/test")
def test_llm():
    ok, msg = llm.test_connection(read_env())
    return {"ok": ok, "message": msg}
