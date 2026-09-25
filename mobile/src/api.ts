// Klien backend Trade IDX. Alamat backend (= PC yang jalanin run_backend.bat) DICARI OTOMATIS
// lewat loadApiBase(); isi manual di Pengaturan cuma kalau gagal:
//   - web / emulator di laptop : http://127.0.0.1:8000
//   - HP via hotspot / LAN     : http://<IP-laptop>:8000   (mis. 192.168.x.x)
//   - HP via tunnel            : URL cloudflare (berubah tiap restart)
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Analysis } from "./analysis";

const BASE_KEY = "trade_api_base";
const TOKEN_KEY = "trade_api_token";
export let API_BASE = "http://127.0.0.1:8000";
// kunci akses server cloud (header X-Token). Server di PC rumah gak butuh.
export let API_TOKEN = process.env.EXPO_PUBLIC_API_TOKEN || "";

const norm = (u: string) => u.trim().replace(/\/+$/, "");

export function setApiBase(url: string) {
  API_BASE = norm(url);
}

// server cloud (VPS, nyala 24 jam) = sumber data UTAMA — jurnal hidup di sini
const CLOUD = "https://149-129-251-217.sslip.io";
// ditulis scripts/serve.py ke mobile/.env.local tiap backend nyala (ke-bake pas bundle/build)
const ENV_RUMAH = process.env.EXPO_PUBLIC_API_BASE;
const ENV_LUAR = process.env.EXPO_PUBLIC_API_BASE_LUAR;

async function ping(base: string, ms = 3000): Promise<boolean> {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), ms);
  try {
    const r = await fetch(`${base}/health`, { signal: ctl.signal });
    return r.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(t);
  }
}

// Cari backend OTOMATIS (panggil pas app start): coba semua kandidat barengan, ambil yang
// nyaut sesuai urutan prioritas, simpan. Return alamat yang ketemu, atau null kalau PC mati.
//   1. alamat tersimpan (terakhir berhasil / diisi manual)
//   2. server cloud (utama)
//   3. ALAMAT RUMAH dari serve.py (LAN IP PC) — cadangan kalau cloud gak nyaut
//   4. PC ini sendiri (app versi web di laptop)
//   5. ALAMAT LUAR dari serve.py (tunnel, buat beda WiFi)
export async function loadApiBase(): Promise<string | null> {
  let saved: string | null = null;
  try {
    saved = await AsyncStorage.getItem(BASE_KEY);
    const tok = await AsyncStorage.getItem(TOKEN_KEY);
    if (tok) API_TOKEN = tok;
  } catch {}
  const host = typeof window !== "undefined" ? window.location?.hostname : undefined;
  const cands = [saved, CLOUD, ENV_RUMAH, host ? `http://${host}:8000` : null, "http://127.0.0.1:8000", ENV_LUAR]
    .filter((c): c is string => !!c)
    .map(norm);
  const uniq = Array.from(new Set(cands));
  const ok = await Promise.all(uniq.map((c) => ping(c)));
  const hit = uniq.find((_, i) => ok[i]) ?? null;
  if (hit) {
    API_BASE = hit;
    if (hit !== saved) AsyncStorage.setItem(BASE_KEY, hit).catch(() => {});
  } else {
    API_BASE = norm(saved || CLOUD);
  }
  return hit;
}

// set + simpan permanen
export async function saveApiBase(url: string): Promise<void> {
  API_BASE = norm(url);
  try {
    await AsyncStorage.setItem(BASE_KEY, API_BASE);
  } catch {}
}

export async function saveApiToken(tok: string): Promise<void> {
  API_TOKEN = tok.trim();
  try {
    await AsyncStorage.setItem(TOKEN_KEY, API_TOKEN);
  } catch {}
}

async function req(path: string, init?: RequestInit) {
  const headers = { ...((init?.headers as Record<string, string>) || {}) };
  if (API_TOKEN) headers["X-Token"] = API_TOKEN;
  const r = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!r.ok) {
    const t = await r.text().catch(() => "");
    // backend kirim pesan ramah di {"detail": "..."} — tampilin itu, bukan JSON mentah
    let detail = "";
    try {
      const d = JSON.parse(t).detail;
      if (typeof d === "string") detail = d;
    } catch {}
    throw new Error(detail || `HTTP ${r.status}${t ? " · " + t.slice(0, 120) : ""}`);
  }
  return r.json();
}

export const getAnalysis = (): Promise<Analysis> => req("/analysis");

export const runAnalisa = (modal?: string): Promise<Analysis> =>
  req(`/analisa${modal ? `?modal=${encodeURIComponent(modal)}` : ""}`, { method: "POST" });

export interface LlmInfo {
  provider: string;
  model: string;
  label: string;
  base_url: string;
  has_key: boolean;
  keys: Record<string, boolean>; // provider mana aja yang udah punya API key tersimpan
  providers: Record<string, { label: string; models: string[]; key_url: string; openai: boolean }>;
}
export const getLlmConfig = (): Promise<LlmInfo> => req("/config/llm");

export const deleteLlmKey = (provider: string) =>
  req(`/config/llm/key/${encodeURIComponent(provider)}`, { method: "DELETE" });

export const setLlmConfig = (cfg: {
  provider: string; model: string; api_key?: string; base_url?: string;
}) => req("/config/llm", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(cfg),
});

// daftar model ASLI dari provider (pakai key); live=false -> daftar bawaan
export const getLlmModels = (q: {
  provider: string; api_key?: string; base_url?: string;
}): Promise<{ models: string[]; live: boolean }> => req("/config/llm/models", json("POST", q));

// tes provider/model yang lagi DIPILIH (belum perlu disimpan)
export const testLlm = (cfg?: {
  provider: string; model: string; api_key?: string; base_url?: string;
}): Promise<{ ok: boolean; message: string }> =>
  req("/config/llm/test", cfg ? json("POST", cfg) : { method: "POST" });

// ---- Sinyal mesin (tab Sinyal) ----
export interface Signal {
  ticker: string;
  action: string;
  score: number;
  close: number;
  ma20: number | null;
  ma50: number | null;
  rsi: number | null;
  sent: number | null;
  n_news: number;
  stop: number | null;
  target: number | null;
  reasons: string[];
}
export const getSignals = (limit = 40): Promise<{ asof: string; signals: Signal[] }> =>
  req(`/signals?limit=${limit}`);

// ---- Berita + sentimen (tab Berita) ----
export interface NewsItem {
  ticker: string;
  published: string | null;
  title: string;
  source: string | null;
  link: string | null;
  sent_label: string;
  sent_score: number | null;
}
export interface Mover {
  ticker: string;
  avg: number;
  n: number;
}
export const getNews = (
  ticker?: string,
  limit = 40,
): Promise<{ items: NewsItem[]; positif: Mover[]; negatif: Mover[] }> =>
  req(`/news?limit=${limit}${ticker ? `&ticker=${encodeURIComponent(ticker)}` : ""}`);

// ---- Harga (tab Chart) ----
export interface Bar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
}
export interface Prices {
  ticker: string;
  days: number;
  last: number;
  chg_pct: number | null;
  series: Bar[];
  levels: { ma20?: number; ma50?: number; stop?: number; target?: number };
  signal: { action: string; score: number; rsi: number; sent: number; n_news: number } | null;
}
export const getPrices = (ticker: string, days = 90): Promise<Prices> =>
  req(`/prices?ticker=${encodeURIComponent(ticker)}&days=${days}`);

// ---- Angka makro/komoditas (strip di card Makro) ----
export interface MacroItem {
  ticker: string;
  label: string;
  unit: string; // "$" prefix, "%" suffix, atau ""
  last: number;
  chg: number;
  date: string;
}
export const getMacro = (): Promise<{ items: MacroItem[] }> => req("/macro");

// ---- Jurnal real (tab Jurnal): catat / tutup / hapus ----
export interface JournalTrade {
  id: number;
  ticker: string;
  entry_date: string;
  entry: number;
  lot: number;
  stop: number | null;
  target: number | null;
  thesis: string | null;
  exit_date: string | null;
  exit: number | null;
  status: "open" | "closed";
  px: number | null; // closed: harga jual · open: close terakhir
  px_date: string | null;
  gross_pct: number | null;
  net_pct: number | null; // setelah fee + slippage
  pl_rp: number | null;
  trail: number | null; // garis jual trailing (posisi terbuka)
}
export interface JournalSummary {
  realized: number;
  unreal: number;
  total: number;
  closed: number;
  open: number;
  wins: number;
  win_rate: number;
  avg_ret: number;
}
export const getJournal = (): Promise<{ trades: JournalTrade[]; summary: JournalSummary }> =>
  req("/journal");

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const addTrade = (t: {
  ticker: string; entry: number; lot: number; stop?: number | null; target?: number | null;
  thesis?: string | null; entry_date?: string | null;
}) => req("/journal", json("POST", t));

export const closeTrade = (id: number, exit: number, exit_date?: string | null) =>
  req(`/journal/${id}/close`, json("POST", { exit, exit_date }));

export const deleteTrade = (id: number) => req(`/journal/${id}`, { method: "DELETE" });
