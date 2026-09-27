"""Tab Pengaturan: pilih otak analisa (provider + model LLM) & kelola API key per provider.

API key disimpan di .env server (LLM_KEY_<PROVIDER>) dan gak pernah dikirim balik ke app.
"""
from __future__ import annotations

from contextlib import closing

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from trade import llm
from trade.config import read_env, write_env
from trade.db import get_connection

router = APIRouter()


class LLMChoice(BaseModel):
    provider: str
    model: str
    api_key: str | None = None


class ModelsQuery(BaseModel):
    provider: str
    api_key: str | None = None


def _provider(name: str) -> dict:
    p = llm.PROVIDERS.get(name)
    if not p:
        raise HTTPException(400, "Provider gak dikenal.")
    return p


def _env_with(provider: str, model: str | None = None, api_key: str | None = None) -> dict:
    """Salinan .env buat provider/model/key yang lagi DIPILIH di app (belum disimpan)."""
    env = read_env()
    env["LLM_PROVIDER"] = provider
    if model:
        env["LLM_MODEL"] = model
    if api_key:
        env[llm.key_var(provider)] = api_key
    return env


@router.get("/config/llm")
def get_llm():
    """Provider/model aktif + daftar provider + provider mana aja yang udah punya key (key-nya TIDAK dikirim)."""
    env = read_env()
    c = llm.resolve(env)
    return {
        "provider": c["provider"], "model": c["model"],
        "keys": {k: bool(env.get(llm.key_var(k))) for k in llm.PROVIDERS},
        "providers": {k: {"label": v["label"], "models": v["models"]} for k, v in llm.PROVIDERS.items()},
    }


@router.post("/config/llm")
def set_llm(cfg: LLMChoice):
    """Jadiin provider/model ini otak analisa. Key baru (kalau diisi) disimpan per provider."""
    p = _provider(cfg.provider)
    key = (cfg.api_key or "").strip()
    if not key and not read_env().get(llm.key_var(cfg.provider)):
        raise HTTPException(400, f"API key {p['label']} belum ada.")
    upd = {"LLM_PROVIDER": cfg.provider, "LLM_MODEL": cfg.model}
    if key:
        upd[llm.key_var(cfg.provider)] = key
    write_env(upd)
    return {"ok": True}


@router.delete("/config/llm/key/{provider}")
def delete_llm_key(provider: str):
    """Hapus API key 1 provider. Key yang lagi dipakai analisa gak boleh dihapus."""
    _provider(provider)
    if provider == read_env().get("LLM_PROVIDER"):
        raise HTTPException(400, "Key ini lagi dipakai analisa. Ganti provider dulu, baru hapus.")
    write_env({llm.key_var(provider): None})
    return {"ok": True}


@router.get("/config/llm/status")
def llm_status():
    """Status otak analisa aktif — GRATIS (cuma cek key ke provider, gak nyuruh LLM nulis, 0 token).
    DeepSeek: + sisa saldo (USD & kira-kira Rupiah pakai kurs terakhir)."""
    env = read_env()
    ok = llm.check_key(env)
    usd = llm.balance_usd(env) if ok else None
    rp = None
    if usd is not None:
        with closing(get_connection(readonly=True)) as conn:
            fx = conn.execute("SELECT close FROM macro WHERE ticker='IDR=X' ORDER BY date DESC LIMIT 1").fetchone()
        rp = round(usd * fx["close"]) if fx else None
    return {"ok": ok, "balance_usd": usd, "balance_rp": rp}


@router.post("/config/llm/test")
def test_llm(cfg: LLMChoice):
    """Tes provider/model/key yang lagi DIPILIH di app (belum disimpan). LLM beneran dipanggil."""
    ok, msg = llm.test_connection(_env_with(cfg.provider, cfg.model, cfg.api_key))
    return {"ok": ok, "message": msg}


@router.post("/config/llm/models")
def llm_models(q: ModelsQuery):
    """Daftar model chat ASLI dari provider (biar dropdown gak basi pas model lama pensiun).
    Tanpa key / gagal / kegedean (>40) -> daftar bawaan."""
    p = _provider(q.provider)
    env = _env_with(q.provider, api_key=q.api_key)
    live = llm.list_models(env) if llm.resolve(env)["key"] else []
    if 0 < len(live) <= 40:
        return {"models": live, "live": True}
    return {"models": p["models"], "live": False}
