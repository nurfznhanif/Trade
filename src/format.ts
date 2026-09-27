// Format angka & tanggal gaya Indonesia (1.310 · 1,25jt · "Jumat, 25 September 2026 pukul 17.35 WIB").

const HARI = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];
const BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
  "September", "Oktober", "November", "Desember"];

// "BBCA.JK" -> "BBCA"
export const code = (ticker: string) => ticker.replace(".JK", "");

// 1310 -> "1.310"
export function fmtInt(n: number | null | undefined): string {
  if (n === null || n === undefined) return "–";
  return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

// Rp ringkas: 1.250.000 -> "1,25jt", 52.300 -> "52,3rb"
export function fmtRpShort(n: number): string {
  const a = Math.abs(n);
  if (a >= 1e6) return (n / 1e6).toFixed(2).replace(/\.?0+$/, "").replace(".", ",") + "jt";
  if (a >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, "").replace(".", ",") + "rb";
  return fmtInt(n);
}

// 0.125 -> "12,5%"
export const pctTxt = (x: number) => (x * 100).toFixed(1).replace(".", ",") + "%";

// 0.016 -> "+1,6%", -0.031 -> "−3,1%"
export const pctPlus = (x: number) => (x > 0 ? "+" : x < 0 ? "−" : "") + pctTxt(Math.abs(x));

// +Rp1.500 / -Rp1.500
export function rpSigned(n: number | null | undefined): string {
  if (n == null) return "–";
  return (n > 0 ? "+" : n < 0 ? "-" : "") + "Rp" + fmtInt(Math.abs(n));
}

// 0.031 -> "+3.1%"
export function pctSigned(x: number | null | undefined): string {
  if (x == null) return "–";
  return (x > 0 ? "+" : "") + (x * 100).toFixed(1) + "%";
}

// pas ngetik: "1500000" -> "1.500.000"
export const fmtRibuan = (v: string) => {
  const d = v.replace(/\D/g, "").replace(/^0+/, "");
  return d ? d.replace(/\B(?=(\d{3})+(?!\d))/g, ".") : "";
};

// "6.500" / "6500" -> 6500 ; kosong -> null
export function num(s: string): number | null {
  const c = s.replace(/[^\d,]/g, "").replace(",", ".");
  return c ? Number(c) : null;
}

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

// umur berita: "hari ini" / "kemarin" / "3 hari lalu" / "12 Sep"
export function fmtAgo(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(+d)) return "";
  const days = Math.floor((Date.now() - +d) / 86400000);
  if (days <= 0) return "hari ini";
  if (days === 1) return "kemarin";
  if (days < 7) return `${days} hari lalu`;
  return d.toLocaleDateString("id-ID", { day: "numeric", month: "short" });
}

// "2026-09-15" -> "15 Sep"
export function fmtDay(iso: string | null): string {
  if (!iso) return "–";
  const d = new Date(iso.slice(0, 10) + "T00:00:00");
  return isNaN(+d) ? iso : d.toLocaleDateString("id-ID", { day: "numeric", month: "short" });
}

export function daysSince(iso: string): number {
  return Math.max(0, Math.floor((Date.now() - +new Date(iso.slice(0, 10) + "T00:00:00")) / 86400000));
}

// tanggal lokal hari ini "2026-09-25" (default tanggal beli/jual)
export function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
