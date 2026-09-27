import { useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";
import { Analysis } from "../../analysis";
import { MacroItem } from "../../api";
import { fmtInt } from "../../format";
import { C, signColor } from "../../theme";
import { ui } from "../../ui";

// Kartu ANALISIS MAKRO: cerita pasar dari LLM (paragraf 1 + "Baca selengkapnya") + pil regime + strip angka
export function MacroCard({ data, items }: { data: Analysis; items: MacroItem[] }) {
  const [open, setOpen] = useState(false);
  const up = data.macro.toUpperCase();
  // regime dari field LLM; analisa lama belum punya -> tebak dari teks
  const regime = (data.regime || "").toUpperCase() ||
    (up.includes("RISK-OFF") ? "RISK-OFF" : up.includes("RISK-ON") ? "RISK-ON" : "NETRAL");
  const regimeCol = regime === "RISK-OFF" ? C.down : regime === "RISK-ON" ? C.up : C.warn;
  const paras = data.macro.split(/\n+/).map((s) => s.trim()).filter(Boolean);

  return (
    <View style={styles.card}>
      <View style={styles.head}>
        <Text style={ui.cardLabel}>ANALISIS MAKRO</Text>
        <View style={[styles.pill, { borderColor: regimeCol }]}>
          <Text style={[styles.pillText, { color: regimeCol }]}>{regime}</Text>
        </View>
      </View>
      <Text style={styles.text}>{paras[0]}</Text>
      {open
        ? paras.slice(1).map((p, i) => (
            <Text key={i} style={[styles.text, styles.para]}>{p}</Text>
          ))
        : null}
      {paras.length > 1 ? (
        <Pressable onPress={() => setOpen((o) => !o)} hitSlop={8} style={ui.moreBtn}>
          <Text style={ui.moreText}>{open ? "Tutup" : "Baca selengkapnya"}</Text>
          <Ionicons name={open ? "chevron-up" : "chevron-down"} size={14} color={C.accent} />
        </Pressable>
      ) : null}
      {items.length > 0 ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.strip}
          contentContainerStyle={styles.stripInner}>
          {items.map((m) => (
            <MacroTile key={m.ticker} m={m} />
          ))}
        </ScrollView>
      ) : null}
    </View>
  );
}

// Rupiah >= 1 juta -> "Rp2,48jt"; >= 1000 -> titik ribuan (17.875); < 1000 -> 2 desimal (98,73)
function fmtMacro(m: MacroItem): string {
  const n = m.last;
  if (m.unit === "Rp") return n >= 1e6 ? `Rp${(n / 1e6).toFixed(2).replace(".", ",")}jt` : `Rp${fmtInt(n)}`;
  const s = n >= 1000 ? fmtInt(n) : n.toFixed(2).replace(".", ",");
  return m.unit === "%" ? s + "%" : s;
}

function MacroTile({ m }: { m: MacroItem }) {
  return (
    <View style={styles.tile}>
      <Text style={styles.tileLabel}>
        {m.label}
        {m.per ? <Text style={styles.tilePer}> /{m.per}</Text> : null}
      </Text>
      <Text style={styles.tileVal}>{fmtMacro(m)}</Text>
      <Text style={[styles.tileChg, { color: signColor(m.chg) }]}>
        {m.chg >= 0 ? "+" : ""}
        {m.chg}%
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: C.card, borderRadius: 14, padding: 14, marginTop: 14, borderWidth: 1, borderColor: C.border },
  head: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 8 },
  pill: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4 },
  pillText: { fontSize: 12, fontWeight: "800", letterSpacing: 1 },
  text: { color: C.textSoft, fontSize: 14, lineHeight: 21, textAlign: "justify" },
  para: { marginTop: 10 },
  strip: { marginTop: 12, marginHorizontal: -2 },
  stripInner: { gap: 8, paddingHorizontal: 2 },
  tile: { backgroundColor: C.sunken, borderRadius: 10, borderWidth: 1, borderColor: C.border, paddingHorizontal: 11, paddingVertical: 8, minWidth: 82 },
  tileLabel: { color: C.muted, fontSize: 10, fontWeight: "700", letterSpacing: 0.3 },
  tilePer: { color: C.dim, fontWeight: "600" },
  tileVal: { color: C.text, fontSize: 15, fontWeight: "800", marginTop: 3 },
  tileChg: { fontSize: 11, fontWeight: "700", marginTop: 2 },
});
