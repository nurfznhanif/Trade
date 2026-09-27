// Potongan form: kolom isian berlabel + tombol aksi kecil berikon.
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";
import { C, IconName } from "../theme";
import { ui } from "../ui";

export function Field({
  label, value, onChange, placeholder, numeric, caps,
}: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string;
  numeric?: boolean; caps?: boolean;
}) {
  return (
    <View style={styles.field}>
      <Text style={ui.fieldLabel}>{label}</Text>
      <TextInput
        style={[ui.input, styles.input]}
        value={value}
        onChangeText={onChange}
        placeholder={placeholder}
        placeholderTextColor={C.dim}
        keyboardType={numeric ? "numeric" : "default"}
        autoCapitalize={caps ? "characters" : "none"}
        autoCorrect={false}
      />
    </View>
  );
}

export function ActBtn({
  icon, label, onPress, danger,
}: { icon: IconName; label: string; onPress: () => void; danger?: boolean }) {
  const c = danger ? C.down : C.textSoft;
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [ui.actBtn, danger && styles.danger, pressed && ui.pressed]}
    >
      <Ionicons name={icon} size={15} color={c} />
      <Text style={[ui.actBtnText, { color: c }]}>{label}</Text>
    </Pressable>
  );
}

// pasangan tombol [label] + Batal di bawah form. danger = tombol merah (hapus).
export function FormButtons({
  label, onSave, onCancel, busy, danger,
}: { label: string; onSave: () => void; onCancel: () => void; busy: boolean; danger?: boolean }) {
  return (
    <View style={ui.btnRow}>
      <Pressable style={[ui.btn, danger ? styles.dangerBtn : ui.btnPri]} onPress={onSave} disabled={busy}>
        <Text style={danger ? styles.dangerBtnText : ui.btnPriText}>{busy ? "…" : label}</Text>
      </Pressable>
      <Pressable style={[ui.btn, ui.btnGhost]} onPress={onCancel} disabled={busy}>
        <Text style={ui.btnGhostText}>Batal</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  field: { flex: 1, minWidth: 0, marginTop: 10 },
  input: { width: "100%", paddingHorizontal: 10 },
  danger: { borderColor: "rgba(239,68,68,0.35)" },
  dangerBtn: { backgroundColor: C.down },
  dangerBtnText: { color: "#fff", fontSize: 14, fontWeight: "800", letterSpacing: 0.5 },
});
