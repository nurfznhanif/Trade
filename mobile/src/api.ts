// Klien backend Trade IDX. Ganti API_BASE ke alamat backend yang bisa dijangkau:
//   - web / emulator di laptop : http://127.0.0.1:8000
//   - HP via hotspot / LAN     : http://<IP-laptop>:8000   (mis. 192.168.x.x)
//   - HP via tunnel            : URL ngrok / cloudflare
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Analysis } from "./analysis";

const BASE_KEY = "trade_api_base";
export let API_BASE = "http://127.0.0.1:8000";

export function setApiBase(url: string) {
  API_BASE = url.replace(/\/+$/, "");
}

// muat alamat backend tersimpan (panggil pas app start, sebelum fetch)
export async function loadApiBase(): Promise<string> {
  try {
    const v = await AsyncStorage.getItem(BASE_KEY);
    if (v) API_BASE = v.replace(/\/+$/, "");
  } catch {}
  return API_BASE;
}

// set + simpan permanen
export async function saveApiBase(url: string): Promise<void> {
  API_BASE = url.replace(/\/+$/, "");
  try {
    await AsyncStorage.setItem(BASE_KEY, API_BASE);
  } catch {}
}

async function req(path: string, init?: RequestInit) {
  const r = await fetch(`${API_BASE}${path}`, init);
  if (!r.ok) {
    const t = await r.text().catch(() => "");
    throw new Error(`HTTP ${r.status}${t ? " · " + t.slice(0, 120) : ""}`);
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
  providers: Record<string, { label: string; models: string[]; key_url: string; openai: boolean }>;
}
export const getLlmConfig = (): Promise<LlmInfo> => req("/config/llm");

export const setLlmConfig = (cfg: {
  provider: string; model: string; api_key?: string; base_url?: string;
}) => req("/config/llm", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(cfg),
});

export const testLlm = (): Promise<{ ok: boolean; message: string }> =>
  req("/config/llm/test", { method: "POST" });

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
