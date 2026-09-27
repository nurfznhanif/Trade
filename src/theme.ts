import type { ComponentProps } from "react";
import type Ionicons from "@expo/vector-icons/Ionicons";

// Palet warna app (tema gelap). Warna = makna: hijau untung/beli, merah rugi/hindari, kuning waspada/tunggu.
export const C = {
  bg: "#0a0e13", // latar app
  nav: "#0c1117", // menu bawah
  card: "#121821", // kartu
  sunken: "#0e141b", // kotak di dalam kartu
  border: "#1e2731",
  divider: "#161d26",
  text: "#e6edf3",
  textSoft: "#c2cbd4", // paragraf
  label: "#8b95a1", // label kecil
  muted: "#7d8792", // teks sekunder
  dim: "#56606c", // placeholder, ikon pasif
  faint: "#3a434e",
  accent: "#2dd4bf", // teal: tombol, link, menu aktif
  onAccent: "#04110d", // teks di atas tombol teal
  up: "#22c55e", // untung / BELI / naik
  down: "#ef4444", // rugi / HINDARI / turun
  warn: "#f59e0b", // TUNGGU / WASPADA
  warnText: "#fbbf24",
  info: "#38bdf8", // Entry / netral
  errText: "#fca5a5",
};

// warna angka bertanda: + hijau, - merah, 0 / kosong abu-abu
export const signColor = (n: number | null | undefined) =>
  n == null || n === 0 ? C.muted : n > 0 ? C.up : C.down;

// nama ikon Ionicons (app pakai ikon beneran, bukan emoji)
export type IconName = ComponentProps<typeof Ionicons>["name"];
