import { useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";
import { Call, group } from "../../analysis";
import { addTrade, errMsg } from "../../api";
import { Field, FormButtons } from "../../components/Form";
import { code, fmtInt, num, todayIso } from "../../format";
import { C } from "../../theme";
import { ui } from "../../ui";

// form CATAT BELI: saham yang UDAH dibeli di broker. Bisa diisi otomatis dari saran BELI hari ini.
export function AddTradeForm({ calls, onDone, onCancel }: { calls: Call[]; onDone: () => void; onCancel: () => void }) {
  const picks = calls.filter((c) => group(c.action) === "beli" && c.entry);
  const blank = { ticker: "", entry: "", lot: "1", stop: "", target: "", date: todayIso(), thesis: "" };
  const [f, setF] = useState(blank);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const set = (k: keyof typeof blank) => (v: string) => setF((o) => ({ ...o, [k]: v }));

  // isi dari saran analisa (harga tinggal disesuaiin sama harga nyata di broker)
  const pick = (c: Call) =>
    setF({
      ticker: code(c.ticker),
      entry: c.entry != null ? String(c.entry) : "",
      lot: String(c.lot || 1),
      stop: c.stop != null ? String(c.stop) : "",
      target: c.target != null ? String(c.target) : "",
      date: todayIso(),
      thesis: `Ikut saran analisa (${c.action})`,
    });

  const entry = num(f.entry);
  const lot = num(f.lot);
  const value = entry && lot ? entry * lot * 100 : null;

  const save = () => {
    if (!f.ticker.trim()) return setMsg("Isi kode saham dulu.");
    if (!entry || !lot) return setMsg("Harga beli & jumlah lot wajib diisi.");
    if (!Number.isInteger(lot)) return setMsg("Lot harus bilangan bulat (1 lot = 100 lembar).");
    setBusy(true);
    setMsg("");
    addTrade({
      ticker: f.ticker.trim(),
      entry,
      lot,
      stop: num(f.stop),
      target: num(f.target),
      thesis: f.thesis.trim() || null,
      entry_date: f.date.trim() || null,
    })
      .then(onDone)
      .catch((e) => setMsg(errMsg(e)))
      .finally(() => setBusy(false));
  };

  return (
    <View style={styles.card}>
      <View style={ui.cardTop}>
        <Text style={styles.title}>Catat Beli</Text>
        <Pressable onPress={onCancel} hitSlop={8}>
          <Ionicons name="close" size={20} color={C.muted} />
        </Pressable>
      </View>

      {picks.length > 0 ? (
        <>
          <Text style={ui.fieldLabel}>DARI SARAN ANALISA HARI INI</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
            {picks.map((c) => {
              const on = f.ticker === code(c.ticker);
              return (
                <Pressable key={c.ticker} onPress={() => pick(c)} style={[styles.chip, on && styles.chipOn]}>
                  <Text style={[styles.chipText, on && styles.chipTextOn]}>
                    {code(c.ticker)} · {fmtInt(c.entry)}
                  </Text>
                </Pressable>
              );
            })}
          </ScrollView>
        </>
      ) : null}

      <View style={ui.formRow}>
        <Field label="Kode" value={f.ticker} onChange={set("ticker")} placeholder="BBCA" caps />
        <Field label="Harga beli" value={f.entry} onChange={set("entry")} placeholder="6500" numeric />
        <Field label="Lot" value={f.lot} onChange={set("lot")} placeholder="1" numeric />
      </View>
      <View style={ui.formRow}>
        <Field label="Stop" value={f.stop} onChange={set("stop")} placeholder="opsional" numeric />
        <Field label="Target" value={f.target} onChange={set("target")} placeholder="opsional" numeric />
        <Field label="Tgl beli" value={f.date} onChange={set("date")} placeholder={todayIso()} />
      </View>
      <View style={ui.formRow}>
        <Field label="Alasan beli" value={f.thesis} onChange={set("thesis")} placeholder="opsional" />
      </View>

      {value ? <Text style={styles.hint}>Nilai posisi ~Rp{fmtInt(value)}</Text> : null}
      {msg ? <Text style={ui.formErr}>{msg}</Text> : null}
      <FormButtons label="Simpan" onSave={save} onCancel={onCancel} busy={busy} />
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: C.card, borderRadius: 14, padding: 14, marginTop: 16, borderWidth: 1, borderColor: C.accent + "55" },
  title: { color: C.text, fontSize: 17, fontWeight: "800", marginBottom: 10 },
  chips: { gap: 8, paddingRight: 8 },
  chip: { borderWidth: 1, borderColor: C.border, backgroundColor: C.card, borderRadius: 999, paddingHorizontal: 13, paddingVertical: 7 },
  chipOn: { borderColor: C.accent, backgroundColor: "rgba(45,212,191,0.12)" },
  chipText: { color: C.label, fontSize: 12, fontWeight: "700" },
  chipTextOn: { color: C.accent },
  hint: { color: C.dim, fontSize: 11, marginTop: 5 },
});
