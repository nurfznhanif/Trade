import { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";
import { Analysis } from "../../analysis";
import { errMsg, getJournal, JournalSummary, JournalTrade } from "../../api";
import { ErrBox, Loading } from "../../components/Feedback";
import { rpSigned } from "../../format";
import { C, signColor } from "../../theme";
import { ui } from "../../ui";
import { AddTradeForm } from "./AddTradeForm";
import { ClosedTradeCard, OpenTradeCard } from "./TradeCards";

// Tab Jurnal: jurnal trading REAL (disimpan di server). Verdict TAHAN/WASPADA/JUAL dari analisa nempel di posisi.
export function JournalScreen({ data }: { data: Analysis | null }) {
  const [j, setJ] = useState<{ trades: JournalTrade[]; summary: JournalSummary } | null>(null);
  const [err, setErr] = useState("");
  const [adding, setAdding] = useState(false);

  // muat ulang tanpa ngosongin layar (data lama tetap nongol selama ngambil)
  const load = () =>
    getJournal()
      .then((d) => { setJ(d); setErr(""); })
      .catch((e) => setErr(errMsg(e)));

  useEffect(() => { load(); }, []);

  if (!j && !err) return <Loading />;
  if (!j) return <ErrBox msg={err} />;

  const open = j.trades.filter((t) => t.status === "open");
  const closed = j.trades.filter((t) => t.status === "closed");
  const verdicts = new Map((data?.positions || []).map((p) => [p.ticker, p]));

  return (
    <>
      <View style={ui.secHead}>
        <Text style={[ui.sectionTitle, ui.secHeadTitle]}>JURNAL REAL</Text>
      </View>
      {err ? <Text style={ui.note}>{err}</Text> : null}

      {j.trades.length > 0 ? <SummaryCard s={j.summary} /> : null}

      {adding ? (
        <AddTradeForm calls={data?.calls ?? []} onDone={() => { setAdding(false); load(); }} onCancel={() => setAdding(false)} />
      ) : (
        <Pressable style={({ pressed }) => [styles.addBtn, pressed && ui.pressed]} onPress={() => setAdding(true)}>
          <View style={styles.addRow}>
            <Ionicons name="add-circle-outline" size={18} color={C.onAccent} />
            <Text style={styles.addText}>CATAT BELI</Text>
          </View>
        </Pressable>
      )}

      {j.trades.length === 0 && !adding ? (
        <View style={ui.empty}>
          <Ionicons name="book-outline" size={40} color={C.dim} />
          <Text style={ui.emptyTitle}>Jurnal masih kosong</Text>
          <Text style={ui.emptyDesc}>Catat saham yang udah dibeli di broker — untung-ruginya kehitung otomatis.</Text>
        </View>
      ) : null}

      {open.length > 0 ? <Text style={ui.sectionTitle}>POSISI TERBUKA · {open.length}</Text> : null}
      {open.map((t) => (
        <OpenTradeCard key={t.id} t={t} verdict={verdicts.get(t.ticker)} onChanged={load} />
      ))}

      {closed.length > 0 ? <Text style={ui.sectionTitle}>RIWAYAT TERTUTUP · {closed.length}</Text> : null}
      {closed.map((t) => (
        <ClosedTradeCard key={t.id} t={t} onChanged={load} />
      ))}
    </>
  );
}

function SummaryCard({ s }: { s: JournalSummary }) {
  return (
    <View style={styles.sum}>
      <Text style={styles.sumLabel}>TOTAL UNTUNG / RUGI</Text>
      <Text style={[styles.sumTotal, { color: signColor(s.total) }]}>{rpSigned(s.total)}</Text>
      <View style={styles.metricRow}>
        <Metric label="Realized" val={rpSigned(s.realized)} color={signColor(s.realized)} />
        <Metric label="Floating" val={rpSigned(s.unreal)} color={signColor(s.unreal)} />
        <Metric label="Win rate" val={s.closed ? `${Math.round(s.win_rate * 100)}% · ${s.wins}/${s.closed}` : "–"} />
      </View>
    </View>
  );
}

function Metric({ label, val, color }: { label: string; val: string; color?: string }) {
  return (
    <View style={styles.metric}>
      <Text style={ui.metricLabel}>{label}</Text>
      <Text style={[styles.metricVal, color ? { color } : null]}>{val}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  addBtn: { backgroundColor: C.accent, borderRadius: 14, paddingVertical: 15, alignItems: "center", marginTop: 16 },
  addRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  addText: { color: C.onAccent, fontSize: 15, fontWeight: "800", letterSpacing: 1 },
  sum: { backgroundColor: C.card, borderRadius: 14, padding: 14, marginTop: 14, borderWidth: 1, borderColor: C.border },
  sumLabel: { color: C.muted, fontSize: 11, fontWeight: "800", letterSpacing: 1 },
  sumTotal: { fontSize: 26, fontWeight: "800", marginTop: 4 },
  metricRow: { flexDirection: "row", gap: 16, marginTop: 12, flexWrap: "wrap" },
  metric: { minWidth: 52 },
  metricVal: { color: C.text, fontSize: 15, fontWeight: "800", marginTop: 2 },
});
