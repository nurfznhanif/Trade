import { Pressable, StyleSheet, Text, View } from "react-native";
import { Analysis, Group, group } from "../../analysis";
import { MacroItem } from "../../api";
import { C } from "../../theme";
import { CallCard } from "./CallCard";
import { MacroCard } from "./MacroCard";
import { SlicingCard } from "./SlicingCard";

const GROUPS: { key: Group; label: string; color: string }[] = [
  { key: "beli", label: "Beli", color: C.up },
  { key: "tunggu", label: "Tunggu", color: C.warn },
  { key: "hindari", label: "Hindari", color: C.down },
];

// Tab Analisa: makro -> slicing modal -> jumlah saran -> filter -> kartu saran saham
export function AnalysisScreen({
  data, macro, tab, onTab,
}: { data: Analysis; macro: MacroItem[]; tab: Group; onTab: (g: Group) => void }) {
  const counts = { beli: 0, tunggu: 0, hindari: 0 };
  data.calls.forEach((x) => (counts[group(x.action)] += 1));

  return (
    <>
      <MacroCard data={data} items={macro} />

      {/* slicing modal (analisa sendiri jalan otomatis tiap subuh di server) */}
      <SlicingCard />

      <View style={styles.tiles}>
        {GROUPS.map((g) => (
          <View key={g.key} style={styles.tile}>
            <Text style={[styles.tileNum, { color: g.color }]}>{counts[g.key]}</Text>
            <Text style={styles.tileLabel}>{g.label.toUpperCase()}</Text>
          </View>
        ))}
      </View>

      <View style={styles.tabs}>
        {GROUPS.map((g) => (
          <Pressable key={g.key} style={[styles.tab, tab === g.key && styles.tabActive]} onPress={() => onTab(g.key)}>
            <Text style={[styles.tabText, tab === g.key && styles.tabTextActive]}>
              {g.label} · {counts[g.key]}
            </Text>
          </Pressable>
        ))}
      </View>

      {data.calls.filter((c) => group(c.action) === tab).map((c) => (
        <CallCard key={c.ticker} c={c} />
      ))}
    </>
  );
}

const styles = StyleSheet.create({
  tiles: { flexDirection: "row", gap: 10, marginTop: 16 },
  tile: { flex: 1, backgroundColor: C.card, borderRadius: 12, paddingVertical: 14, alignItems: "center", borderWidth: 1, borderColor: C.border },
  tileNum: { fontSize: 24, fontWeight: "800" },
  tileLabel: { color: C.muted, fontSize: 11, fontWeight: "700", letterSpacing: 1, marginTop: 2 },
  tabs: { flexDirection: "row", backgroundColor: C.card, borderRadius: 12, padding: 4, marginTop: 16, borderWidth: 1, borderColor: C.border },
  tab: { flex: 1, paddingVertical: 9, alignItems: "center", borderRadius: 9 },
  tabActive: { backgroundColor: C.border },
  tabText: { color: C.muted, fontSize: 13, fontWeight: "700" },
  tabTextActive: { color: C.text },
});
