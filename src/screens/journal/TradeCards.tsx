// Kartu posisi di jurnal: terbuka (P/L jalan + garis jual) / tertutup (P/L final), plus form tutup & hapus.
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";
import { Position, verdictColor } from "../../analysis";
import { closeTrade, deleteTrade, errMsg, JournalTrade } from "../../api";
import { ActBtn, Field, FormButtons } from "../../components/Form";
import { Level } from "../../components/Level";
import { code, daysSince, fmtDay, fmtInt, num, pctSigned, rpSigned, todayIso } from "../../format";
import { C, signColor } from "../../theme";
import { ui } from "../../ui";

type CardProps = { t: JournalTrade; onChanged: () => void };

// seberapa jauh harga dari garis jual (trailing stop)
function trailStatus(t: JournalTrade): { text: string; color: string } | null {
  if (t.px == null || t.trail == null) return null;
  const cushion = ((t.px - t.trail) / t.px) * 100;
  if (t.px < t.trail) return { text: "Tembus garis jual — evaluasi keluar", color: C.down };
  if (cushion < 3) return { text: `Waspada — tinggal ${cushion.toFixed(1)}% di atas garis jual`, color: C.warn };
  return { text: `Aman — ${cushion.toFixed(1)}% di atas garis jual`, color: C.up };
}

export function OpenTradeCard({ t, verdict, onChanged }: CardProps & { verdict?: Position }) {
  const [mode, setMode] = useState<"" | "close" | "delete">("");
  const col = signColor(t.pl_rp);
  const st = trailStatus(t);
  const vc = verdict ? verdictColor(verdict.verdict) : "";

  return (
    <View style={[ui.card, { borderLeftColor: col }]}>
      <View style={ui.cardTop}>
        <View style={styles.tickerRow}>
          <Text style={ui.ticker}>{code(t.ticker)}</Text>
          {verdict ? (
            <View style={[ui.badge, { backgroundColor: vc + "22", borderColor: vc }]}>
              <Text style={[ui.badgeText, { color: vc }]}>{verdict.verdict}</Text>
            </View>
          ) : null}
        </View>
        <Text style={[styles.pct, { color: col }]}>{pctSigned(t.gross_pct)}</Text>
      </View>
      <Text style={ui.subline}>
        {fmtInt(t.lot)} lot · beli {fmtDay(t.entry_date)} · dipegang {daysSince(t.entry_date)} hari
      </Text>

      <View style={ui.levels}>
        <Level label="Modal" val={fmtInt(t.entry)} />
        <Level label="Harga" val={fmtInt(t.px)} sub={t.px_date ? `close ${fmtDay(t.px_date)}` : undefined} subColor={C.muted} />
        <Level label="Garis jual" val={fmtInt(t.trail)} />
        {t.target != null ? <Level label="Target" val={fmtInt(t.target)} /> : null}
      </View>

      <View style={styles.plRow}>
        <Text style={styles.plLabel}>P/L</Text>
        <Text style={[styles.plVal, { color: col }]}>{rpSigned(t.pl_rp)}</Text>
      </View>
      {st ? (
        <View style={ui.iconRow}>
          <View style={[ui.dot, { backgroundColor: st.color }]} />
          <Text style={[styles.status, { color: st.color }]}>{st.text}</Text>
        </View>
      ) : null}
      {verdict?.reason ? <Text style={ui.reason} numberOfLines={3}>{verdict.reason}</Text> : null}
      {t.thesis ? <Text style={styles.thesis}>Alasan: {t.thesis}</Text> : null}

      {mode === "close" ? (
        <CloseForm t={t} onDone={onChanged} onCancel={() => setMode("")} />
      ) : mode === "delete" ? (
        <ConfirmDelete t={t} onDone={onChanged} onCancel={() => setMode("")} />
      ) : (
        <View style={styles.actions}>
          <ActBtn icon="checkmark-done-outline" label="Tutup posisi" onPress={() => setMode("close")} />
          <View style={ui.flex1} />
          <ActBtn icon="trash-outline" label="Hapus" danger onPress={() => setMode("delete")} />
        </View>
      )}
    </View>
  );
}

export function ClosedTradeCard({ t, onChanged }: CardProps) {
  const [del, setDel] = useState(false);
  const col = signColor(t.pl_rp);
  return (
    <View style={[ui.card, { borderLeftColor: col }]}>
      <View style={ui.cardTop}>
        <Text style={ui.ticker}>{code(t.ticker)}</Text>
        <Text style={[styles.pct, { color: col }]}>{pctSigned(t.gross_pct)}</Text>
      </View>
      <Text style={ui.subline}>
        {fmtInt(t.lot)} lot · {fmtInt(t.entry)} → {fmtInt(t.exit)} · {fmtDay(t.entry_date)} – {fmtDay(t.exit_date)}
      </Text>
      <View style={styles.plRow}>
        <Text style={styles.plLabel}>P/L</Text>
        <Text style={[styles.plVal, { color: col }]}>{rpSigned(t.pl_rp)}</Text>
        <Text style={styles.net}>bersih setelah fee {pctSigned(t.net_pct)}</Text>
      </View>
      {t.thesis ? <Text style={styles.thesis}>Alasan: {t.thesis}</Text> : null}

      {del ? (
        <ConfirmDelete t={t} onDone={onChanged} onCancel={() => setDel(false)} />
      ) : (
        <View style={styles.actions}>
          <View style={ui.flex1} />
          <ActBtn icon="trash-outline" label="Hapus" danger onPress={() => setDel(true)} />
        </View>
      )}
    </View>
  );
}

type FormProps = { t: JournalTrade; onDone: () => void; onCancel: () => void };

// tutup posisi pakai harga jual NYATA di broker
function CloseForm({ t, onDone, onCancel }: FormProps) {
  const [px, setPx] = useState(t.px != null ? String(Math.round(t.px)) : "");
  const [d, setD] = useState(todayIso());
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const exit = num(px);
  const result = exit ? (exit - t.entry) * t.lot * 100 : null;

  const save = () => {
    if (!exit) return setMsg("Isi harga jual dulu.");
    setBusy(true);
    setMsg("");
    closeTrade(t.id, exit, d.trim() || null)
      .then(onDone)
      .catch((e) => setMsg(errMsg(e)))
      .finally(() => setBusy(false));
  };

  return (
    <View style={styles.inline}>
      <Text style={ui.fieldLabel}>TUTUP POSISI — HARGA JUAL NYATA DI BROKER</Text>
      <View style={ui.formRow}>
        <Field label="Harga jual" value={px} onChange={setPx} numeric />
        <Field label="Tgl jual" value={d} onChange={setD} placeholder={todayIso()} />
      </View>
      {result != null && exit ? (
        <Text style={[styles.preview, { color: signColor(result) }]}>
          Hasil: {rpSigned(result)} ({pctSigned(exit / t.entry - 1)})
        </Text>
      ) : null}
      {msg ? <Text style={ui.formErr}>{msg}</Text> : null}
      <FormButtons label="Simpan jual" onSave={save} onCancel={onCancel} busy={busy} />
    </View>
  );
}

// hapus 2 langkah (tap Hapus -> konfirmasi) biar gak kepencet
function ConfirmDelete({ t, onDone, onCancel }: FormProps) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const del = () => {
    setBusy(true);
    setMsg("");
    deleteTrade(t.id)
      .then(onDone)
      .catch((e) => setMsg(errMsg(e)))
      .finally(() => setBusy(false));
  };
  return (
    <View style={styles.inline}>
      <View style={ui.iconRow}>
        <Ionicons name="warning-outline" size={16} color={C.down} />
        <Text style={styles.confirm}>
          Hapus catatan {code(t.ticker)} ({fmtInt(t.lot)} lot @ {fmtInt(t.entry)})? Permanen, gak bisa dibalikin.
        </Text>
      </View>
      {msg ? <Text style={ui.formErr}>{msg}</Text> : null}
      <FormButtons label="Ya, hapus" onSave={del} onCancel={onCancel} busy={busy} danger />
    </View>
  );
}

const styles = StyleSheet.create({
  tickerRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  pct: { fontSize: 17, fontWeight: "800" },
  plRow: { flexDirection: "row", alignItems: "baseline", gap: 8, marginTop: 12 },
  plLabel: { color: C.muted, fontSize: 11, fontWeight: "700", letterSpacing: 0.5 },
  plVal: { fontSize: 16, fontWeight: "800" },
  net: { color: C.muted, fontSize: 11 },
  status: { fontSize: 12, fontWeight: "700", flex: 1 },
  thesis: { color: C.label, fontSize: 12, marginTop: 8, fontStyle: "italic" },
  actions: { flexDirection: "row", alignItems: "center", marginTop: 12, paddingTop: 10, borderTopWidth: 1, borderTopColor: C.border },
  inline: { marginTop: 12, paddingTop: 10, borderTopWidth: 1, borderTopColor: C.border },
  confirm: { color: C.errText, fontSize: 13, lineHeight: 19, flex: 1 },
  preview: { fontSize: 13, fontWeight: "700", marginTop: 8 },
});
