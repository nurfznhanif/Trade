import { StyleSheet, Text, View } from "react-native";
import { C } from "../theme";

// satu angka berlabel di kartu saham: "Target / 1.330 / +13.7%"
export function Level({ label, val, sub, subColor }: { label: string; val: string; sub?: string; subColor?: string }) {
  return (
    <View style={styles.level}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.val}>{val}</Text>
      {sub ? <Text style={[styles.sub, { color: subColor }]}>{sub}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  level: { minWidth: 64 },
  label: { color: C.muted, fontSize: 10, fontWeight: "700", letterSpacing: 0.5 },
  val: { color: C.text, fontSize: 16, fontWeight: "800", marginTop: 2 },
  sub: { fontSize: 11, fontWeight: "700", marginTop: 1 },
});
