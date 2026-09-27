// Style yang dipakai lintas layar (kartu, tombol, input, judul bagian). Style khusus 1 layar ada di file layarnya.
import { StyleSheet } from "react-native";
import { C } from "./theme";

export const ui = StyleSheet.create({
  flex1: { flex: 1 },
  pressed: { opacity: 0.8 },
  note: { color: C.warnText, fontSize: 12, marginTop: 6 },
  dot: { width: 7, height: 7, borderRadius: 4 },

  // judul bagian: "JURNAL REAL", "POSISI TERBUKA · 2"
  secHead: { marginTop: 14, marginBottom: 2 },
  sectionTitle: { color: C.muted, fontSize: 12, fontWeight: "800", letterSpacing: 1, marginTop: 26, marginBottom: 2 },
  secHeadTitle: { marginTop: 0 },
  cardLabel: { color: C.accent, fontSize: 11, fontWeight: "800", letterSpacing: 1 },
  metricLabel: { color: C.muted, fontSize: 10, fontWeight: "700", letterSpacing: 0.5 },
  moreBtn: { flexDirection: "row", alignItems: "center", gap: 4, alignSelf: "flex-start", marginTop: 8 },
  moreText: { color: C.accent, fontSize: 13, fontWeight: "700" },

  // kartu saham (saran analisa & posisi jurnal)
  card: { backgroundColor: C.card, borderRadius: 14, padding: 14, marginTop: 12, borderLeftWidth: 4, borderWidth: 1, borderColor: C.border },
  cardTop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  ticker: { color: C.text, fontSize: 19, fontWeight: "800", letterSpacing: 1 },
  badge: { borderWidth: 1, borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3 },
  badgeText: { fontSize: 11, fontWeight: "800", letterSpacing: 0.5 },
  subline: { color: C.muted, fontSize: 12, marginTop: 3 },
  levels: { flexDirection: "row", gap: 8, marginTop: 12, flexWrap: "wrap" },
  reason: { color: C.textSoft, fontSize: 13, lineHeight: 19, marginTop: 10 },
  iconRow: { flexDirection: "row", alignItems: "center", gap: 5, marginTop: 10 },
  chartBox: { backgroundColor: C.sunken, borderRadius: 12, borderWidth: 1, borderColor: C.border, marginTop: 14, position: "relative", overflow: "hidden" },

  // input & tombol
  input: { backgroundColor: C.card, borderWidth: 1, borderColor: C.border, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 11, color: C.text, fontSize: 14 },
  inputLabel: { color: C.label, fontSize: 11, fontWeight: "700", letterSpacing: 0.5, marginTop: 16, marginBottom: 6 },
  fieldLabel: { color: C.label, fontSize: 11, fontWeight: "700", letterSpacing: 0.3, marginBottom: 6 },
  inputRow: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 8 },
  inputFlex: { flex: 1, minWidth: 0 },
  formRow: { flexDirection: "row", gap: 8 },
  formErr: { color: C.errText, fontSize: 13, marginTop: 10 },
  // tombol kecil di samping input ("Hitung", "Cek")
  sideBtn: { minWidth: 76, alignSelf: "stretch", alignItems: "center", justifyContent: "center", paddingHorizontal: 14, borderRadius: 10, borderWidth: 1, borderColor: C.accent + "55", backgroundColor: "rgba(45,212,191,0.10)" },
  sideBtnText: { color: C.accent, fontSize: 14, fontWeight: "800" },
  // tombol aksi kecil berikon ("Tutup posisi", "Hapus", "Sambungkan")
  actBtn: { flexDirection: "row", alignItems: "center", gap: 6, borderWidth: 1, borderColor: C.border, backgroundColor: C.sunken, borderRadius: 9, paddingHorizontal: 11, paddingVertical: 7 },
  actBtnText: { fontSize: 12, fontWeight: "700" },
  // pasangan tombol Simpan / Batal
  btnRow: { flexDirection: "row", gap: 10, marginTop: 14 },
  btn: { flex: 1, borderRadius: 12, paddingVertical: 13, alignItems: "center" },
  btnPri: { backgroundColor: C.accent },
  btnPriText: { color: C.onAccent, fontSize: 14, fontWeight: "800", letterSpacing: 0.5 },
  btnGhost: { borderWidth: 1, borderColor: C.border, backgroundColor: C.card },
  btnGhostText: { color: C.text, fontSize: 14, fontWeight: "700" },

  // layar kosong / gagal
  empty: { alignItems: "center", paddingVertical: 64, gap: 9 },
  emptyTitle: { color: C.text, fontSize: 17, fontWeight: "800" },
  emptyDesc: { color: C.muted, fontSize: 13, textAlign: "center", maxWidth: 250, lineHeight: 19 },
});
