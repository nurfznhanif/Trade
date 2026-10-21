// Kotak "Rem pasar aktif": pasar RISK-OFF -> gak beli saham baru (dipakai di Analisa, Slicing, Rapor).
import { StyleSheet, Text, View } from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";
import { C } from "../theme";

export function RemPasar({ text, style }: { text: string; style?: object }) {
  return (
    <View style={[styles.box, style]}>
      <Ionicons name="hand-left-outline" size={16} color={C.warn} />
      <Text style={styles.text}>
        <Text style={styles.strong}>Rem pasar aktif · </Text>
        {text}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  box: { flexDirection: "row", alignItems: "flex-start", gap: 8, padding: 10, borderRadius: 10, backgroundColor: "rgba(245,158,11,0.08)", borderWidth: 1, borderColor: "rgba(245,158,11,0.30)" },
  text: { flex: 1, color: C.textSoft, fontSize: 12, lineHeight: 17, textAlign: "justify" },
  strong: { color: C.warnText, fontWeight: "800" },
});
