import { Pressable, StyleSheet, Text, View } from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";
import { C, IconName } from "../theme";

export type Nav = "analisa" | "jurnal" | "rapor" | "berita" | "pengaturan";

const ITEMS: { key: Nav; label: string; icon: IconName }[] = [
  { key: "analisa", label: "Analisa", icon: "stats-chart" },
  { key: "jurnal", label: "Jurnal", icon: "briefcase-outline" },
  { key: "rapor", label: "Rapor", icon: "clipboard-outline" },
  { key: "berita", label: "Berita", icon: "newspaper-outline" },
  { key: "pengaturan", label: "Pengaturan", icon: "settings-outline" },
];

// menu bawah (pola app HP, bukan sidebar)
export function BottomNav({ nav, setNav }: { nav: Nav; setNav: (n: Nav) => void }) {
  return (
    <View style={styles.nav}>
      {ITEMS.map((it) => {
        const active = nav === it.key;
        return (
          <Pressable key={it.key} style={styles.btn} onPress={() => setNav(it.key)}>
            <Ionicons name={it.icon} size={21} color={active ? C.accent : C.muted} />
            <Text style={[styles.label, active && styles.labelActive]}>{it.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  nav: { flexDirection: "row", backgroundColor: C.nav, borderTopWidth: 1, borderTopColor: C.border, paddingTop: 8, paddingBottom: 10 },
  btn: { flex: 1, alignItems: "center", gap: 3, paddingVertical: 2 },
  label: { color: C.muted, fontSize: 10, fontWeight: "700", letterSpacing: 0.3 },
  labelActive: { color: C.accent },
});
