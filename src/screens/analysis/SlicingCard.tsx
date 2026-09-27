import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";
import { errMsg, getSlicing, loadModal, saveModal, Slicing } from "../../api";
import { code, fmtInt, fmtRibuan, fmtRpShort, num, pctTxt } from "../../format";
import { C } from "../../theme";
import { RuleList } from "../../components/RuleList";
import { ui } from "../../ui";

// warna porsi tiap saham (kategori, bukan makna untung/rugi)
const PALET = [C.accent, C.info, "#818cf8", "#a78bfa", "#22d3ee", "#5eead4"];
const rp = (x: number) => `Rp${fmtRpShort(x)}`;

// SLICING MODAL: bagi modal ke saham BELI hari ini. Hitungan aturan risiko di server (bukan LLM).
export function SlicingCard({ live }: { live: boolean }) {
  const [modal, setModal] = useState("");
  const [res, setRes] = useState<Slicing | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    loadModal().then((v) => v && setModal(v)); // modal terakhir diinget
  }, []);

  const hitung = () => {
    const m = num(modal);
    if (!m) return setErr("Isi modal dulu.");
    if (!live) return setErr("Server belum nyambung.");
    setBusy(true);
    setErr("");
    saveModal(modal);
    getSlicing(m)
      .then(setRes)
      .catch((e) => { setRes(null); setErr(errMsg(e)); })
      .finally(() => setBusy(false));
  };

  return (
    <View style={styles.card}>
      <View style={styles.head}>
        <Ionicons name="pie-chart-outline" size={15} color={C.accent} />
        <Text style={ui.cardLabel}>SLICING MODAL</Text>
      </View>
      <View style={ui.inputRow}>
        <View style={[ui.input, ui.inputFlex, styles.rpBox]}>
          <Text style={styles.rpPrefix}>Rp</Text>
          <TextInput
            style={styles.rpInput}
            value={modal}
            onChangeText={(v) => setModal(fmtRibuan(v))}
            keyboardType="numeric"
            placeholder="modal, mis. 1.500.000"
            placeholderTextColor={C.dim}
            onSubmitEditing={hitung}
          />
        </View>
        <Pressable style={({ pressed }) => [ui.sideBtn, pressed && ui.pressed]} onPress={hitung} disabled={busy}>
          {busy ? <ActivityIndicator size="small" color={C.accent} /> : <Text style={ui.sideBtnText}>Hitung</Text>}
        </Pressable>
      </View>
      {err ? <Text style={ui.formErr}>{err}</Text> : null}
      {res ? <SliceResult r={res} /> : null}
    </View>
  );
}

function SliceStat({ label, val, sub, color }: { label: string; val: string; sub?: string; color?: string }) {
  return (
    <View style={styles.stat}>
      <Text style={ui.metricLabel}>{label}</Text>
      <Text style={[styles.statVal, color ? { color } : null]}>{val}</Text>
      {sub ? <Text style={[styles.sub, color ? { color } : null]}>{sub}</Text> : null}
    </View>
  );
}

function SliceResult({ r }: { r: Slicing }) {
  const usedPct = r.modal ? r.used / r.modal : 0;
  const more = r.skipped.length - 3;
  const rk = r.rules;
  return (
    <View>
      <View style={styles.bar}>
        {r.picks.map((p, i) => (
          <View key={p.ticker} style={{ flex: p.pct, backgroundColor: PALET[i % PALET.length] }} />
        ))}
        <View style={{ flex: Math.max(0, 1 - usedPct), backgroundColor: C.border }} />
      </View>

      <View style={styles.stats}>
        <SliceStat label="Terpakai" val={rp(r.used)} sub={`${pctTxt(usedPct)} dari modal`} />
        <SliceStat label="Tidak Terpakai" val={rp(r.cash)} sub={`${pctTxt(1 - usedPct)} dari modal`} />
        <SliceStat label="Untung" val={`+${rp(r.reward_rp)}`} sub={`+${pctTxt(r.reward_pct)} dari modal`} color={C.up} />
        <SliceStat label="Rugi" val={`−${rp(r.risk_rp)}`} sub={`−${pctTxt(r.risk_pct)} dari modal`} color={C.down} />
      </View>

      {r.risk_off ? (
        <View style={styles.callout}>
          <Ionicons name="shield-half-outline" size={16} color={C.warn} />
          <Text style={styles.calloutText}>
            <Text style={styles.calloutStrong}>Mode hati-hati · </Text>
            pasar lagi RISK-OFF, ukuran tiap saham dipotong setengah. Sisanya disimpan jadi kas.
          </Text>
        </View>
      ) : null}

      {r.picks.map((p, i) => (
        <View key={p.ticker} style={styles.row}>
          <View style={[styles.swatch, { backgroundColor: PALET[i % PALET.length] }]} />
          <View style={ui.flex1}>
            <View style={styles.headRow}>
              <Text style={styles.ticker}>{code(p.ticker)}</Text>
              <View style={[styles.pill, styles.pillBuy]}>
                <Text style={[styles.pillText, { color: C.info }]}>
                  Beli {p.lot} lot @ {fmtInt(p.entry)}
                </Text>
              </View>
            </View>
            <View style={styles.pills}>
              {p.target != null && p.reward_rp > 0 ? (
                <View style={[styles.pill, styles.pillUp]}>
                  <Text style={[styles.pillText, { color: C.up }]}>
                    Target {fmtInt(p.target)} · Untung +{rp(p.reward_rp)}
                  </Text>
                </View>
              ) : null}
              <View style={[styles.pill, styles.pillDown]}>
                <Text style={[styles.pillText, { color: C.down }]}>
                  Stop {fmtInt(p.stop)} · Rugi −{rp(p.risk_rp)}
                </Text>
              </View>
            </View>
          </View>
          <View style={styles.right}>
            <Text style={styles.val}>Rp{fmtInt(p.value)}</Text>
            <Text style={styles.sub}>{Math.round(p.pct * 100)}% modal</Text>
          </View>
        </View>
      ))}
      {r.picks.length === 0 ? <Text style={styles.note}>Modal belum cukup buat saham BELI hari ini.</Text> : null}

      {r.skipped.length > 0 ? (
        <Text style={styles.note}>
          Gak kebagian: {r.skipped.slice(0, 3).map((s) => `${code(s.ticker)} (${s.why})`).join(", ")}
          {more > 0 ? ` +${more} lainnya` : ""}
        </Text>
      ) : null}

      {/* aturan hitungan, dijelasin pakai angka rupiah modal ini */}
      <RuleList
        label="Cara hitungnya"
        footer="KEPUTUSAN TETAP DI TANGAN SENDIRI"
        items={[
          `Tiap saham maksimal ${Math.round(rk.max_pct * 100)}% dari modal (${rp(r.modal * rk.max_pct)}), biar gak numpuk di satu saham. Kalau 1 lot aja udah lebih mahal dari itu, sahamnya dilewati.`,
          `Kalau harga turun sampai Stop, rugi tiap saham dijaga sekitar ${(rk.risk_pct * 100).toFixed(0)}% dari modal (${rp(r.modal * rk.risk_pct)}).` +
            (r.risk_off ? " Normalnya 2%, dipotong setengah karena pasar lagi RISK-OFF." : ""),
          `Maksimal ${rk.max_pos} saham. Porsi yang kurang dari ${Math.round(rk.min_pct * 100)}% modal (${rp(r.modal * rk.min_pct)}) gak diambil karena kekecilan.`,
          "Yang dapat jatah duluan: keyakinan (konviksi) paling tinggi, lalu yang peluang untungnya paling besar dibanding ruginya.",
          "Fee beli 0,15% udah ikut dihitung. Sisa uang yang gak kebelikan jadi kas.",
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: C.card, borderRadius: 14, padding: 14, marginTop: 16, borderWidth: 1, borderColor: C.border },
  head: { flexDirection: "row", alignItems: "center", gap: 8 },
  rpBox: { flexDirection: "row", alignItems: "center", paddingVertical: 0 },
  rpPrefix: { color: C.muted, fontSize: 14, fontWeight: "700", marginRight: 6 },
  rpInput: { flex: 1, minWidth: 0, color: C.text, fontSize: 15, fontWeight: "700", paddingVertical: 11 },

  bar: { flexDirection: "row", height: 8, borderRadius: 4, overflow: "hidden", marginTop: 14, gap: 2 },
  stats: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", rowGap: 8, marginTop: 12, marginBottom: 12 },
  stat: { width: "48.5%", alignItems: "center", paddingVertical: 10, borderRadius: 10, backgroundColor: C.sunken, borderWidth: 1, borderColor: C.border },
  statVal: { color: C.text, fontSize: 16, fontWeight: "800", marginTop: 2 },
  sub: { color: C.muted, fontSize: 11, marginTop: 2 },
  callout: { flexDirection: "row", alignItems: "flex-start", gap: 8, marginBottom: 12, padding: 10, borderRadius: 10, backgroundColor: "rgba(245,158,11,0.08)", borderWidth: 1, borderColor: "rgba(245,158,11,0.30)" },
  calloutText: { flex: 1, color: C.textSoft, fontSize: 12, lineHeight: 17, textAlign: "justify" },
  calloutStrong: { color: C.warnText, fontWeight: "800" },

  row: { flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 12, borderTopWidth: 1, borderTopColor: C.border },
  swatch: { width: 4, alignSelf: "stretch", borderRadius: 2 },
  headRow: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: 8 },
  ticker: { color: C.text, fontSize: 15, fontWeight: "800" },
  pills: { alignItems: "flex-start", gap: 6, marginTop: 8 },
  pill: { borderRadius: 6, borderWidth: 1, paddingHorizontal: 6, paddingVertical: 2 },
  pillBuy: { borderColor: "rgba(56,189,248,0.35)", backgroundColor: "rgba(56,189,248,0.08)" },
  pillUp: { borderColor: "rgba(34,197,94,0.35)", backgroundColor: "rgba(34,197,94,0.08)" },
  pillDown: { borderColor: "rgba(239,68,68,0.35)", backgroundColor: "rgba(239,68,68,0.08)" },
  pillText: { fontSize: 11, fontWeight: "700" },
  right: { alignItems: "flex-end" },
  val: { color: C.text, fontSize: 14, fontWeight: "800" },
  note: { color: C.label, fontSize: 12, lineHeight: 17, marginTop: 10 },
});
