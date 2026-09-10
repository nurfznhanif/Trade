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

// kelompok tab
export function group(action: string): "beli" | "tunggu" | "hindari" {
  if (action.startsWith("BELI")) return "beli";
  if (action.startsWith("HINDARI")) return "hindari";
  return "tunggu";
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
