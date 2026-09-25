// Tipe data + helper buat baca analysis.json (skema yang ditulis auto_analisa.py).
// Untuk rangka ini kita pakai data SAMPEL bundel; nanti diganti fetch ke backend.
import sample from "../assets/analysis.sample.json";

export type Flag = "good" | "neutral" | "caution" | "danger";

export interface Call {
  ticker: string;
  action: string;
  conviction?: string;
  flag?: Flag;
  entry: number | null;
  target: number | null;
  stop: number | null;
  lot?: number;
  reason: string;
}

export interface Position {
  ticker: string;
  verdict: "TAHAN" | "WASPADA" | "JUAL" | string;
  reason: string;
}

export interface Analysis {
  generated: string;
  generated_at?: string; // jam analisa (ISO, UTC)
  engine: string;
  modal?: number;
  macro: string;
  calls: Call[];
  positions?: Position[];
}

export const sampleAnalysis = sample as unknown as Analysis;

// ---- helper tampilan ----
export const flagColor: Record<string, string> = {
  good: "#22c55e",
  neutral: "#38bdf8",
  caution: "#f59e0b",
  danger: "#ef4444",
};

export function actionColor(action: string): string {
  if (action.startsWith("BELI")) return "#22c55e";
  if (action.startsWith("HINDARI")) return "#ef4444";
  return "#f59e0b"; // TUNGGU PULLBACK
}

export function verdictColor(v: string): string {
  if (v === "JUAL") return "#ef4444";
  if (v === "WASPADA") return "#f59e0b";
  return "#22c55e"; // TAHAN
}

// warna sentimen berita: + hijau, - merah, ~0 netral (biru)
export function sentColor(score: number | null | undefined): string {
  if (score == null) return "#7d8792";
  if (score > 0.15) return "#22c55e";
  if (score < -0.15) return "#ef4444";
  return "#38bdf8";
}

// warna aksi sinyal mesin (BUY/HOLD/SELL)
export function sigColor(action: string): string {
  const a = action.toUpperCase();
  if (a.includes("BUY") || a.includes("BELI")) return "#22c55e";
  if (a.includes("SELL") || a.includes("HINDARI") || a.includes("AVOID")) return "#ef4444";
  return "#f59e0b"; // HOLD
}

// kelompok tab
export function group(action: string): "beli" | "tunggu" | "hindari" {
  if (action.startsWith("BELI")) return "beli";
  if (action.startsWith("HINDARI")) return "hindari";
  return "tunggu";
}

const HARI = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];
const BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
  "September", "Oktober", "November", "Desember"];

// "2026-09-25T10:35:00+00:00" -> "Jumat, 25 September 2026 pukul 17.35 WIB"
// (tanpa jam -> tanggal aja). Digeser manual ke WIB biar gak tergantung zona waktu HP.
export function fmtWaktu(iso?: string, tanggal?: string): string {
  const t = iso ? Date.parse(iso) : NaN;
  if (!isNaN(t)) {
    const d = new Date(t + 7 * 3600e3);
    const hh = String(d.getUTCHours()).padStart(2, "0");
    const mm = String(d.getUTCMinutes()).padStart(2, "0");
    return `${HARI[d.getUTCDay()]}, ${d.getUTCDate()} ${BULAN[d.getUTCMonth()]} ${d.getUTCFullYear()} pukul ${hh}.${mm} WIB`;
  }
  const d = tanggal ? new Date(tanggal.slice(0, 10) + "T00:00:00Z") : null;
  if (d && !isNaN(+d)) return `${HARI[d.getUTCDay()]}, ${d.getUTCDate()} ${BULAN[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  return tanggal || "";
}

// format angka ala Indonesia: 1310 -> "1.310"
export function fmtInt(n: number | null | undefined): string {
  if (n === null || n === undefined) return "–";
  return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

// Risk:Reward = (target-entry)/(entry-stop)
export function rr(c: Call): string | null {
  if (c.entry == null || c.target == null || c.stop == null) return null;
  const risk = c.entry - c.stop;
  if (risk <= 0) return null;
  return (((c.target - c.entry) / risk)).toFixed(2);
}

// persen ke target / ke stop
export function pct(from: number | null, to: number | null): string | null {
  if (from == null || to == null || from === 0) return null;
  return (((to - from) / from) * 100).toFixed(1);
}
