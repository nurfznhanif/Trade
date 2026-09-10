// Klien backend Trade IDX. Ganti API_BASE ke alamat backend yang bisa dijangkau:
//   - web / emulator di laptop : http://127.0.0.1:8000
//   - HP via hotspot / LAN     : http://<IP-laptop>:8000   (mis. 192.168.x.x)
//   - HP via tunnel            : URL ngrok / cloudflare
import { Analysis } from "./analysis";

export let API_BASE = "http://127.0.0.1:8000";
export function setApiBase(url: string) {
  API_BASE = url.replace(/\/+$/, "");
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
