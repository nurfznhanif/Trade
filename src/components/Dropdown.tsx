import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";
import { C } from "../theme";
import { ui } from "../ui";

// dropdown sederhana (buka-tutup di tempat) — jalan sama di Android & web
export function Dropdown({
  label, value, options, onChange, placeholder, disabled,
}: {
  label: string; value: string; options: { value: string; label: string }[];
  onChange: (v: string) => void; placeholder: string; disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const cur = options.find((o) => o.value === value);
  return (
    <View>
      <Text style={ui.inputLabel}>{label}</Text>
      <Pressable
        style={[ui.input, styles.box, open && styles.boxOpen, disabled && styles.disabled]}
        onPress={() => !disabled && setOpen((o) => !o)}
      >
        <Text style={[styles.text, !cur && styles.placeholder]} numberOfLines={1}>
          {cur ? cur.label : placeholder}
        </Text>
        <Ionicons name={open ? "chevron-up" : "chevron-down"} size={16} color={C.muted} />
      </Pressable>
      {open ? (
        <View style={styles.list}>
          {options.map((o) => {
            const on = o.value === value;
            return (
              <Pressable
                key={o.value}
                style={({ pressed }) => [styles.item, on && styles.itemOn, pressed && ui.pressed]}
                onPress={() => { onChange(o.value); setOpen(false); }}
              >
                <Text style={[styles.itemText, on && styles.itemTextOn]}>{o.label}</Text>
                {on ? <Ionicons name="checkmark" size={16} color={C.accent} /> : null}
              </Pressable>
            );
          })}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  box: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8 },
  boxOpen: { borderColor: C.accent },
  disabled: { opacity: 0.5 },
  text: { color: C.text, fontSize: 14, flex: 1 },
  placeholder: { color: C.dim },
  list: { marginTop: 6, backgroundColor: C.sunken, borderWidth: 1, borderColor: C.border, borderRadius: 10, overflow: "hidden" },
  item: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 12, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: C.divider },
  itemOn: { backgroundColor: "rgba(45,212,191,0.08)" },
  itemText: { color: C.textSoft, fontSize: 14 },
  itemTextOn: { color: C.accent, fontWeight: "700" },
});
