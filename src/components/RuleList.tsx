import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";
import { C } from "../theme";
import { ui } from "../ui";

// tombol buka-tutup "Cara hitungnya" + daftar aturan bernomor pakai kalimat biasa
export function RuleList({ label, items, footer }: { label: string; items: string[]; footer?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Pressable onPress={() => setOpen((o) => !o)} hitSlop={8} style={ui.moreBtn}>
        <Ionicons name="information-circle-outline" size={15} color={C.accent} />
        <Text style={ui.moreText}>{open ? `Tutup ${label.toLowerCase()}` : label}</Text>
        <Ionicons name={open ? "chevron-up" : "chevron-down"} size={14} color={C.accent} />
      </Pressable>
      {open ? (
        <View style={styles.box}>
          {items.map((t, i) => (
            <View key={i} style={styles.item}>
              <Text style={styles.num}>{i + 1}</Text>
              <Text style={styles.text}>{t}</Text>
            </View>
          ))}
          {footer ? <Text style={styles.footer}>{footer}</Text> : null}
        </View>
      ) : null}
    </>
  );
}

const styles = StyleSheet.create({
  box: { marginTop: 8, padding: 12, borderRadius: 10, backgroundColor: C.sunken, borderWidth: 1, borderColor: C.border, gap: 9 },
  item: { flexDirection: "row", gap: 9, alignItems: "flex-start" },
  num: { width: 18, height: 18, borderRadius: 9, backgroundColor: "rgba(45,212,191,0.15)", color: C.accent, fontSize: 11, fontWeight: "800", textAlign: "center", lineHeight: 18 },
  text: { flex: 1, color: C.textSoft, fontSize: 12, lineHeight: 18, textAlign: "justify" },
  footer: { color: C.label, fontSize: 11, fontWeight: "800", letterSpacing: 0.5, textAlign: "center", marginTop: 4 },
});
