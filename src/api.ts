// Klien backend Trade IDX. Server utama = VPS cloud (nyala 24 jam, jurnal tersimpan di sana).
// Alamat dicari OTOMATIS pas app buka (loadApiBase); isi manual di Pengaturan cuma cadangan.
// Kunci akses (header X-Token) diisi di Pengaturan & disimpan di HP — JANGAN ditanam di kode (repo publik).
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Analysis } from "./analysis";

const CLOUD = "https://149-129-251-217.sslip.io";
const BASE_KEY = "trade_api_base";
const TOKEN_KEY = "trade_api_token";
const MODAL_KEY = "trade_modal";

export let API_BASE = CLOUD;
export let API_TOKEN = "";

const norm = (u: string) => u.trim().replace(/\/+$/, "");

// pesan error yang kebaca manusia
export const errMsg = (e: any) => String(e?.message || e);

// status sambungan ke server: lagi dicari / tersambung / ketemu tapi kunci akses ditolak / gak ketemu
export type Conn = "cari" | "ok" | "kunci" | "mati";

// server nolak karena kunci akses kosong / salah (beda dari server mati).
// Pakai penanda, bukan `instanceof` subclass Error (gak selalu jalan setelah dikompilasi buat Android).
export const isAuthError = (e: any) => e?.auth === true;

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

// Cari server OTOMATIS: coba semua kandidat barengan, ambil yang nyaut sesuai urutan prioritas, simpan.
// Return alamat yang ketemu, atau null kalau gak ada yang nyaut.
//   1. server cloud (selalu didahulukan biar gak nyasar ke backend lokal yang basi)
//   2. alamat tersimpan (terakhir berhasil / diisi manual)
//   3. backend di laptop ini (app versi web pas ngetes: uvicorn :8000)
export async function loadApiBase(): Promise<string | null> {
  let saved: string | null = null;
  try {
    saved = await AsyncStorage.getItem(BASE_KEY);
    const tok = await AsyncStorage.getItem(TOKEN_KEY);
    if (tok) API_TOKEN = tok;
  } catch {}
  const host = typeof window !== "undefined" ? window.location?.hostname : undefined;
  const cands = [CLOUD, saved, host ? `http://${host}:8000` : null, "http://127.0.0.1:8000"]
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

// modal terakhir di kartu Slicing (diinget di HP)
export const loadModal = async (): Promise<string> => {
  try {
    return (await AsyncStorage.getItem(MODAL_KEY)) || "";
  } catch {
    return "";
  }
};
export const saveModal = (v: string) => AsyncStorage.setItem(MODAL_KEY, v).catch(() => {});

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
    if (r.status === 401) throw Object.assign(new Error(detail || "Kunci akses salah atau kosong."), { auth: true });
    throw new Error(detail || `HTTP ${r.status}${t ? " · " + t.slice(0, 120) : ""}`);
  }
  return r.json();
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

// ---- Tab Analisa ----
export const getAnalysis = (): Promise<Analysis> => req("/analysis");

export interface MacroItem {
  ticker: string;
  label: string;
  unit: string; // "Rp" di depan, "%" di belakang, "" (indeks)
  per?: string | null; // satuan komoditas: "gr" (emas), "barel" (minyak)
  last: number;
  chg: number; // % perubahan harian
  date: string;
}
export const getMacro = (): Promise<{ items: MacroItem[] }> => req("/macro");

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
}
export const getPrices = (ticker: string, days = 90): Promise<Prices> =>
  req(`/prices?ticker=${encodeURIComponent(ticker)}&days=${days}`);

// Slicing modal: bagi modal ke saham BELI (hitungan aturan risiko di server, bukan LLM)
export interface SlicePick {
  ticker: string;
  lot: number;
  entry: number;
  stop: number;
  target: number | null;
  value: number; // Rp, termasuk fee beli
  pct: number; // porsi dari modal (0..1)
  risk_rp: number; // rugi kalau kena stop
  reward_rp: number; // untung kalau sampai target
}
export interface Slicing {
  modal: number; // modal total = kas + nilai saham yang dipegang (dasar ukuran)
  kas_awal?: number; // uang kas yang diisi (yang beneran dibelanjain)
  held?: { ticker: string; lot: number; value: number }[]; // posisi terbuka di Jurnal (dilewati)
  held_value?: number;
  used: number;
  cash: number;
  risk_rp: number;
  risk_pct: number;
  reward_rp: number;
  reward_pct: number;
  risk_off: boolean;
  picks: SlicePick[];
  skipped: { ticker: string; why: string }[];
  rules: { risk_pct: number; max_pct: number; min_pct: number };
}
// kas = uang yang belum dipakai beli (saldo di broker); saham yang dipegang dibaca server dari Jurnal
export const getSlicing = (kas: number): Promise<Slicing> => req("/slicing", json("POST", { kas }));

// ---- Tab Berita ----
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
export const getNews = (limit = 40): Promise<{ items: NewsItem[]; positif: Mover[]; negatif: Mover[] }> =>
  req(`/news?limit=${limit}`);

// ---- Tab Jurnal ----
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
  created?: string | null;
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
export const getJournal = (): Promise<{ trades: JournalTrade[]; summary: JournalSummary }> => req("/journal");

export const addTrade = (t: {
  ticker: string; entry: number; lot: number; stop?: number | null; target?: number | null;
  thesis?: string | null; entry_date?: string | null;
}) => req("/journal", json("POST", t));

export const closeTrade = (id: number, exit: number, exit_date?: string | null) =>
  req(`/journal/${id}/close`, json("POST", { exit, exit_date }));

export const deleteTrade = (id: number) => req(`/journal/${id}`, { method: "DELETE" });

// Cadangan jurnal DI HP: tiap Jurnal kebuka, isi aslinya disimpan di sini. Kalau server hilang / dipasang
// ulang (jurnal di server kosong), app nawarin buat dipulihkan (POST /journal/restore, cuma kalau server kosong).
const JOURNAL_COPY_KEY = "trade_journal_copy";
const BACKUP_FIELDS = ["id", "ticker", "entry_date", "entry", "lot", "stop", "target", "thesis",
  "exit_date", "exit", "status", "created"] as const;
export interface JournalCopy {
  saved_at: string;
  trades: Record<string, unknown>[];
}
export async function saveJournalCopy(trades: JournalTrade[]): Promise<void> {
  const rows = trades.map((t) => Object.fromEntries(BACKUP_FIELDS.map((k) => [k, (t as any)[k] ?? null])));
  const copy: JournalCopy = { saved_at: new Date().toISOString(), trades: rows };
  await AsyncStorage.setItem(JOURNAL_COPY_KEY, JSON.stringify(copy)).catch(() => {});
}
export async function loadJournalCopy(): Promise<JournalCopy | null> {
  try {
    const raw = await AsyncStorage.getItem(JOURNAL_COPY_KEY);
    return raw ? (JSON.parse(raw) as JournalCopy) : null;
  } catch {
    return null;
  }
}
export const clearJournalCopy = () => AsyncStorage.removeItem(JOURNAL_COPY_KEY).catch(() => {});
export const restoreJournal = (trades: Record<string, unknown>[]): Promise<{ ok: boolean; restored: number }> =>
  req("/journal/restore", json("POST", { trades }));

// ---- Tab Rapor (uji coba otomatis; terpisah dari jurnal asli) ----
export interface SimPosition {
  ticker: string;
  lot: number;
  buy_date: string;
  buy_px: number;
  stop: number;
  target: number | null;
  hit_target: boolean; // sempat lewat Target (gak dijual, biarin lari)
  last: number;
  last_date: string;
  trail: number; // garis jual buat hari bursa berikutnya
  pl_rp: number; // udah dipotong biaya beli & jual
  pl_pct: number;
}
export interface SimClosed {
  ticker: string;
  lot: number;
  buy_date: string;
  buy_px: number;
  sell_date: string;
  sell_px: number;
  why: string;
  hit_target: boolean;
  pl_rp: number;
  pl_pct: number;
}
export interface CallResult {
  date: string;
  ticker: string;
  action: string;
  entry: number;
  target: number | null;
  stop: number;
  result: "target" | "stop" | "jalan" | "miss" | "wait";
  ret: number | null;
  // nasib saran ini di portofolio uji (dompet Rp1,5 juta): ikut dibeli (masih dipegang / udah dijual + hasilnya),
  // order pagi ini, order gak kebeli, atau gak dibeli (chip = alasan pendek, mis. "Uang gak cukup")
  porto?: {
    status: "ikut" | "order" | "batal" | "lewat";
    why: string;
    chip?: string;
    sold?: boolean;
    sold_why?: string;
    pl_pct?: number;
  } | null;
}
export interface Rapor {
  ready: boolean;
  start?: string;
  asof?: string | null;
  n_analyses?: number;
  modal: number;
  sim?: {
    modal: number;
    cash: number;
    value: number;
    equity: number;
    pl_rp: number;
    pl_pct: number;
    ihsg_pct: number | null;
    open: SimPosition[];
    closed: SimClosed[];
    missed: { ticker: string; date: string; why: string }[];
    curve: { date: string; equity: number }[];
    today: { ticker: string; lot: number; entry: number; stop: number; target: number | null; value: number }[];
    today_date: string | null;
  };
  calls?: {
    beli: { n: number; target: number; stop: number; jalan: number; miss: number; wait: number };
    hit_rate: number | null;
    avg: { beli: number | null; tunggu: number | null; hindari: number | null; ihsg: number | null };
    n: { beli: number; tunggu: number; hindari: number };
    items: CallResult[];
  };
  rules: { portofolio: string[]; saran: string[] };
}
export const getRapor = (): Promise<Rapor> => req("/rapor");

// ---- Tab Pengaturan (otak analisa / LLM) ----
export interface LlmInfo {
  provider: string;
  model: string;
  keys: Record<string, boolean>; // provider mana aja yang udah punya API key tersimpan
  providers: Record<string, { label: string; models: string[] }>;
}
export const getLlmConfig = (): Promise<LlmInfo> => req("/config/llm");

// status otak aktif — GRATIS (server cuma cek key, gak manggil LLM). DeepSeek + sisa saldo.
export interface LlmStatus {
  ok: boolean | null; // null = gak ketahuan (jaringan)
  balance_usd: number | null;
  balance_rp: number | null;
}
export const getLlmStatus = (): Promise<LlmStatus> => req("/config/llm/status");

type LlmChoice = { provider: string; model: string; api_key?: string };

export const setLlmConfig = (cfg: LlmChoice) => req("/config/llm", json("POST", cfg));

export const deleteLlmKey = (provider: string) =>
  req(`/config/llm/key/${encodeURIComponent(provider)}`, { method: "DELETE" });

// tes provider/model/key yang lagi DIPILIH (belum disimpan) — LLM beneran dipanggil
export const testLlm = (cfg: LlmChoice): Promise<{ ok: boolean; message: string }> =>
  req("/config/llm/test", json("POST", cfg));

// daftar model ASLI dari provider (pakai key); live=false -> daftar bawaan
export const getLlmModels = (q: { provider: string; api_key?: string }): Promise<{ models: string[]; live: boolean }> =>
  req("/config/llm/models", json("POST", q));
