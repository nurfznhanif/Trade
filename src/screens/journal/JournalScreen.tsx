import { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";
import { Analysis } from "../../analysis";
import {
  clearJournalCopy, errMsg, getJournal, JournalCopy, JournalSummary, JournalTrade, loadJournalCopy, restoreJournal,
  saveJournalCopy,
} from "../../api";
import { ErrBox, Loading } from "../../components/Feedback";
import { FormButtons } from "../../components/Form";
import { fmtDay, rpSigned } from "../../format";
import { C, signColor } from "../../theme";
import { ui } from "../../ui";
import { AddTradeForm } from "./AddTradeForm";
import { ClosedTradeCard, OpenTradeCard } from "./TradeCards";

// Tab Jurnal: jurnal trading REAL (disimpan di server). Verdict TAHAN/WASPADA/JUAL dari analisa nempel di posisi.
export function JournalScreen({ data }: { data: Analysis | null }) {
  const [j, setJ] = useState<{ trades: JournalTrade[]; summary: JournalSummary } | null>(null);
  const [err, setErr] = useState("");
  const [adding, setAdding] = useState(false);
  const [copy, setCopy] = useState<JournalCopy | null>(null); // cadangan jurnal di HP ini
  const [offer, setOffer] = useState<JournalCopy | null>(null); // server kosong tapi HP punya cadangan

  // muat ulang tanpa ngosongin layar (data lama tetap nongol selama ngambil).
  // Isi server disimpan jadi cadangan di HP — kecuali server tiba-tiba kosong padahal HP punya cadangan
  // (server dipasang ulang?): cadangannya jangan ditimpa, tawarin buat dipulihkan. afterWrite = habis
  // Bapak sendiri catat/tutup/hapus, jadi isi server pasti yang terbaru.
  const load = (afterWrite = false) =>
    getJournal()
      .then(async (d) => {
        setJ(d);
        setErr("");
        const saved = await loadJournalCopy();
        if (d.trades.length > 0 || afterWrite || !saved?.trades.length) {
          await saveJournalCopy(d.trades);
          setCopy(await loadJournalCopy());
          setOffer(null);
        } else {
          setCopy(saved);
          setOffer(saved);
        }
      })
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

      {offer ? <RestoreCard copy={offer} onDone={() => load(true)} /> : null}

      {j.trades.length > 0 ? <SummaryCard s={j.summary} /> : null}

      {adding ? (
        <AddTradeForm calls={data?.calls ?? []} onDone={() => { setAdding(false); load(true); }} onCancel={() => setAdding(false)} />
      ) : (
        <Pressable style={({ pressed }) => [styles.addBtn, pressed && ui.pressed]} onPress={() => setAdding(true)}>
          <View style={styles.addRow}>
            <Ionicons name="add-circle-outline" size={18} color={C.onAccent} />
            <Text style={styles.addText}>CATAT BELI</Text>
          </View>
        </Pressable>
      )}

      {j.trades.length === 0 && !adding && !offer ? (
        <View style={ui.empty}>
          <Ionicons name="book-outline" size={40} color={C.dim} />
          <Text style={ui.emptyTitle}>Jurnal masih kosong</Text>
          <Text style={ui.emptyDesc}>Catat saham yang udah dibeli di broker — untung-ruginya kehitung otomatis.</Text>
        </View>
      ) : null}

      {open.length > 0 ? <Text style={ui.sectionTitle}>POSISI TERBUKA · {open.length}</Text> : null}
      {open.map((t) => (
        <OpenTradeCard key={t.id} t={t} verdict={verdicts.get(t.ticker)} onChanged={() => load(true)} />
      ))}

      {closed.length > 0 ? <Text style={ui.sectionTitle}>RIWAYAT TERTUTUP · {closed.length}</Text> : null}
      {closed.map((t) => (
        <ClosedTradeCard key={t.id} t={t} onChanged={() => load(true)} />
      ))}

      {j.trades.length > 0 && copy ? (
        <Text style={styles.backupNote}>
          Cadangan jurnal tersimpan di server (tiap pagi, 30 hari) dan di HP ini (terakhir {fmtDay(copy.saved_at)}).
        </Text>
      ) : null}
    </>
  );
}

// server kosong tapi HP masih nyimpen cadangan -> tawarin pulihkan (atau buang cadangannya, 2 langkah)
function RestoreCard({ copy, onDone }: { copy: JournalCopy; onDone: () => void }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [discard, setDiscard] = useState(false);
  const restore = () => {
    setBusy(true);
    setMsg("");
    restoreJournal(copy.trades)
      .then(onDone)
      .catch((e) => setMsg(errMsg(e)))
      .finally(() => setBusy(false));
  };
  const drop = () => clearJournalCopy().then(onDone);
  return (
    <View style={styles.restore}>
      <View style={styles.restoreHead}>
        <Ionicons name="cloud-upload-outline" size={17} color={C.warn} />
        <Text style={styles.restoreTitle}>Jurnal di server kosong</Text>
      </View>
      <Text style={styles.restoreDesc}>
        {discard
          ? "Cadangan di HP ini bakal dihapus permanen. Lanjut kalau jurnal memang sengaja dikosongin."
          : `HP ini masih nyimpen cadangan ${copy.trades.length} catatan (terakhir ${fmtDay(copy.saved_at)}). ` +
            "Kalau server baru dipasang ulang, pulihkan biar catatan Bapak balik."}
      </Text>
      {msg ? <Text style={ui.formErr}>{msg}</Text> : null}
      {discard ? (
        <FormButtons label="Ya, hapus cadangan" onSave={drop} onCancel={() => setDiscard(false)} busy={busy} danger />
      ) : (
        <View style={ui.btnRow}>
          <Pressable style={[ui.btn, ui.btnPri]} onPress={restore} disabled={busy}>
            <Text style={ui.btnPriText}>{busy ? "…" : "Pulihkan"}</Text>
          </Pressable>
          <Pressable style={[ui.btn, ui.btnGhost]} onPress={() => setDiscard(true)} disabled={busy}>
            <Text style={ui.btnGhostText}>Abaikan</Text>
          </Pressable>
        </View>
      )}
    </View>
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
  restore: { backgroundColor: "rgba(245,158,11,0.08)", borderRadius: 14, padding: 14, marginTop: 14, borderWidth: 1, borderColor: "rgba(245,158,11,0.35)" },
  restoreHead: { flexDirection: "row", alignItems: "center", gap: 8 },
  restoreTitle: { color: C.warnText, fontSize: 14, fontWeight: "800" },
  restoreDesc: { color: C.textSoft, fontSize: 13, lineHeight: 19, marginTop: 6 },
  backupNote: { color: C.dim, fontSize: 11, lineHeight: 16, textAlign: "center", marginTop: 20 },
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
