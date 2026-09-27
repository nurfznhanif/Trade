// Tipe data analysis.json (ditulis scripts/auto_analisa.py) + helper warna & kelompok aksi.
import sample from "../assets/analysis.sample.json";
import { C } from "./theme";

export type Flag = "good" | "neutral" | "caution" | "danger";

export interface Call {
  ticker: string;
  action: string; // BELI / BELI (tenang) / BELI (spekulatif) / TUNGGU PULLBACK / HINDARI
  conviction?: string;
  flag?: Flag;
  entry: number | null;
  target: number | null;
  stop: number | null;
  lot?: number; // cuma ada di analisa lama yang pakai modal
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
  regime?: "RISK-ON" | "RISK-OFF" | "NETRAL" | string;
  engine: string;
  modal?: number;
  macro: string;
  calls: Call[];
  positions?: Position[];
}

// data contoh yang tampil sebelum server ketemu
export const sampleAnalysis = sample as unknown as Analysis;

export type Group = "beli" | "tunggu" | "hindari";

// kelompok tab Beli / Tunggu / Hindari
export function group(action: string): Group {
  if (action.startsWith("BELI")) return "beli";
  if (action.startsWith("HINDARI")) return "hindari";
  return "tunggu";
}

export const flagColor: Record<string, string> = {
  good: C.up,
  neutral: C.info,
  caution: C.warn,
  danger: C.down,
};

export function actionColor(action: string): string {
  const g = group(action);
  return g === "beli" ? C.up : g === "hindari" ? C.down : C.warn;
}

export function verdictColor(v: string): string {
  if (v === "JUAL") return C.down;
  if (v === "WASPADA") return C.warn;
  return C.up; // TAHAN
}

// warna sentimen berita: + hijau, - merah, ~0 netral (biru)
export function sentColor(score: number | null | undefined): string {
  if (score == null) return C.muted;
  if (score > 0.15) return C.up;
  if (score < -0.15) return C.down;
  return C.info;
}

// Risk:Reward = (target-entry)/(entry-stop)
export function rr(c: Call): string | null {
  if (c.entry == null || c.target == null || c.stop == null) return null;
  const risk = c.entry - c.stop;
  if (risk <= 0) return null;
  return ((c.target - c.entry) / risk).toFixed(2);
}

// persen perubahan from -> to ("13.7")
export function pct(from: number | null, to: number | null): string | null {
  if (from == null || to == null || from === 0) return null;
  return (((to - from) / from) * 100).toFixed(1);
}
