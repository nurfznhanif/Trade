import { StyleSheet, Text, View } from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";
import { CallResult, getRapor, Rapor } from "../api";
import { ErrBox, Loading } from "../components/Feedback";
import { RuleList } from "../components/RuleList";
import { code, fmtDay, fmtInt, fmtRpShort, pctPlus, rpSigned } from "../format";
import { C, signColor } from "../theme";
import { ui } from "../ui";
import { useAsync } from "../useAsync";

type Sim = NonNullable<Rapor["sim"]>;
type Calls = NonNullable<Rapor["calls"]>;

// Tab Rapor: uji coba OTOMATIS — portofolio uji (ikut Slicing Modal tiap pagi) + rapor saran BELI.
// Terpisah total dari Jurnal (jurnal = trade beneran Bapak).
export function RaporScreen() {
  const { loading, data, err } = useAsync(getRapor, []);
  if (loading) return <Loading />;
  if (err || !data) return <ErrBox msg={err} />;
  const modalTxt = `Rp${fmtRpShort(data.modal)}`;
  const rules = (
    <RuleList
      label="Cara ngukurnya"
      items={[...data.rules.portofolio, ...data.rules.saran]}
      footer="Hasil 1 minggu masih banyak unsur hoki. App ini baru bisa dinilai setelah ±50 saran BELI (sekitar 1–2 bulan)."
    />
  );

  if (!data.ready || !data.sim || !data.calls) {
    return (
      <>
        <Head sub={`Otomatis ngikutin saran app, modal ${modalTxt}`} />
        <View style={ui.empty}>
          <Ionicons name="clipboard-outline" size={40} color={C.dim} />
          <Text style={ui.emptyTitle}>Uji coba mulai analisa pagi berikutnya</Text>
          <Text style={ui.emptyDesc}>
            Tiap pagi jam 05.00 saran analisa diarsip, lalu portofolio uji {modalTxt} ngikutin Slicing Modal. Hasil
            hari itu kelihatan sorenya jam 17.00, setelah harga penutupan masuk.
          </Text>
        </View>
        {rules}
      </>
    );
  }

  const { sim, calls } = data;
  return (
    <>
      <Head
        sub={`Otomatis ngikutin saran app sejak ${fmtDay(data.start ?? null)}` +
          (data.asof ? ` · harga s/d ${fmtDay(data.asof)}` : " · harga pertama masuk sore ini jam 17.00")}
      />
      <SimCard sim={sim} modalTxt={modalTxt} />
      <CallsCard calls={calls} modalTxt={modalTxt} />
      {rules}
    </>
  );
}

function Head({ sub }: { sub: string }) {
  return (
    <View style={ui.secHead}>
      <Text style={[ui.sectionTitle, ui.secHeadTitle]}>RAPOR UJI COBA</Text>
      <Text style={styles.secSub}>{sub}</Text>
    </View>
  );
}

// ---------------------------------------------------------------- portofolio uji
function SimCard({ sim, modalTxt }: { sim: Sim; modalTxt: string }) {
  return (
    <View style={styles.card}>
      <Text style={ui.cardLabel}>PORTOFOLIO UJI · MODAL {modalTxt}</Text>
      <Text style={[styles.big, { color: signColor(sim.pl_rp) }]}>{rpSigned(sim.pl_rp)}</Text>
      <Text style={styles.bigSub}>
        <Text style={{ color: signColor(sim.pl_rp) }}>{pctPlus(sim.pl_pct)}</Text>
        {sim.ihsg_pct != null ? (
          <>
            {"  ·  IHSG di periode sama "}
            <Text style={{ color: signColor(sim.ihsg_pct) }}>{pctPlus(sim.ihsg_pct)}</Text>
          </>
        ) : null}
      </Text>
      <View style={styles.stats}>
        <Stat label="Nilai sekarang" val={`Rp${fmtInt(sim.equity)}`} />
        <Stat label="Uang kas" val={`Rp${fmtInt(sim.cash)}`} />
        <Stat label="Dipegang" val={`${sim.open.length} saham`} />
        <Stat label="Udah dijual" val={`${sim.closed.length} kali`} />
      </View>

      {sim.open.length > 0 ? <Text style={styles.part}>DIPEGANG · {sim.open.length}</Text> : null}
      {sim.open.map((p) => (
        <Row
          key={p.ticker}
          ticker={p.ticker}
          pill={`${p.lot} lot · beli ${fmtInt(p.buy_px)} · ${fmtDay(p.buy_date)}`}
          lines={heldLines(p)}
          flag={p.hit_target ? "Sempat lewat Target" : undefined}
          pl={p.pl_rp}
          pct={p.pl_pct}
        />
      ))}

      {sim.closed.length > 0 ? <Text style={styles.part}>UDAH DIJUAL · {sim.closed.length}</Text> : null}
      {sim.closed.map((p, i) => (
        <Row
          key={`${p.ticker}-${p.sell_date}-${i}`}
          ticker={p.ticker}
          pill={`${p.lot} lot · beli ${fmtInt(p.buy_px)} → jual ${fmtInt(p.sell_px)}`}
          lines={[`${fmtDay(p.buy_date)} – ${fmtDay(p.sell_date)} · ${p.why}`]}
          flag={p.hit_target ? "Sempat lewat Target" : undefined}
          pl={p.pl_rp}
          pct={p.pl_pct}
        />
      ))}

      {sim.today.length > 0 ? (
        <>
          <Text style={styles.part}>ORDER PAGI INI · {fmtDay(sim.today_date)}</Text>
          {sim.today.map((o) => (
            <View key={o.ticker} style={styles.orderRow}>
              <Text style={styles.ticker}>{code(o.ticker)}</Text>
              <Text style={styles.orderText}>
                Beli {o.lot} lot @ {fmtInt(o.entry)} · Stop {fmtInt(o.stop)}
              </Text>
            </View>
          ))}
          <Text style={styles.note}>Kebeli atau enggak, ketahuan sore ini jam 17.00 setelah harga penutupan masuk.</Text>
        </>
      ) : null}

      {sim.missed.length > 0 ? (
        <Text style={styles.note}>
          Gak kebeli: {sim.missed.slice(0, 3).map((m) => `${code(m.ticker)} ${fmtDay(m.date)} (${m.why})`).join(", ")}
          {sim.missed.length > 3 ? ` +${sim.missed.length - 3} lainnya` : ""}
        </Text>
      ) : null}
    </View>
  );
}

// harga tutup terakhir (bukan harga live) + Target + garis jual; garis jual naik dari Stop kalau harga udah naik
function heldLines(p: Sim["open"][number]): string[] {
  const now = `Harga tutup ${fmtDay(p.last_date)}: ${fmtInt(p.last)}` + (p.target ? ` · Target ${fmtInt(p.target)}` : "");
  const line =
    p.trail > p.stop
      ? `Garis jual ${fmtInt(p.trail)} (naik dari Stop ${fmtInt(p.stop)})`
      : `Garis jual ${fmtInt(p.trail)} (masih di Stop awal)`;
  return [now, line];
}

function Row({
  ticker, pill, lines, flag, pl, pct,
}: { ticker: string; pill: string; lines: string[]; flag?: string; pl: number; pct: number }) {
  const col = signColor(pl);
  return (
    <View style={styles.row}>
      <View style={[styles.swatch, { backgroundColor: col }]} />
      <View style={ui.flex1}>
        <View style={styles.headRow}>
          <Text style={styles.ticker}>{code(ticker)}</Text>
          <Text style={styles.pill}>{pill}</Text>
        </View>
        {lines.map((l) => (
          <Text key={l} style={styles.rowSub}>{l}</Text>
        ))}
        {flag ? <Text style={styles.flag}>{flag}</Text> : null}
      </View>
      <View style={styles.right}>
        <Text style={[styles.val, { color: col }]}>{rpSigned(pl)}</Text>
        <Text style={[styles.rowSub, { color: col }]}>{pctPlus(pct)}</Text>
      </View>
    </View>
  );
}

// ---------------------------------------------------------------- rapor saran
const RESULT: Record<CallResult["result"], { label: string; color: string }> = {
  target: { label: "Kena Target", color: C.up },
  stop: { label: "Kena Stop", color: C.down },
  jalan: { label: "Masih jalan", color: C.info },
  miss: { label: "Gak kebeli", color: C.muted },
  wait: { label: "Nunggu harga", color: C.muted },
};

// nasib tiap saran di portofolio uji: label kanan (chip) + keterangan di bawah level
function fate(it: CallResult): { chip: string; color: string; line: string; inPorto: boolean } {
  const p = it.porto;
  if (!p) {
    const r = RESULT[it.result]; // jaga-jaga: saran tanpa catatan portofolio -> hasil saran itu sendiri
    return { chip: r.label + (it.ret != null ? ` ${pctPlus(it.ret)}` : ""), color: r.color, line: "", inPorto: false };
  }
  if (p.status === "ikut") {
    const pl = p.pl_pct ?? 0;
    return p.sold
      ? { chip: `Dijual ${pctPlus(pl)}`, color: signColor(pl), line: `Dibeli portofolio uji, udah dijual (${p.sold_why})`, inPorto: true }
      : { chip: `Dipegang ${pctPlus(pl)}`, color: signColor(pl), line: "Dibeli portofolio uji, masih dipegang", inPorto: true };
  }
  if (p.status === "order") return { chip: "Order pagi ini", color: C.info, line: "Masuk order portofolio uji pagi ini", inPorto: true };
  if (p.status === "batal") return { chip: "Gak kebeli", color: C.muted, line: `Order gak kebeli: ${p.why}`, inPorto: false };
  return { chip: p.chip ?? "Gak dibeli", color: C.muted, line: `Gak dibeli portofolio uji: ${p.why}`, inPorto: false };
}

// "BDMN 2 Okt (+9,1%), AUTO 28 Sep (−3,6%)" — saran yang udah kena Target / Stop
function doneList(items: CallResult[], res: "target" | "stop"): string {
  const hit = items.filter((it) => it.result === res);
  const txt = hit.slice(0, 6).map((it) => `${code(it.ticker)} ${fmtDay(it.date)}${it.ret != null ? ` (${pctPlus(it.ret)})` : ""}`);
  return txt.join(", ") + (hit.length > 6 ? ` +${hit.length - 6} lainnya` : "");
}

function CallsCard({ calls, modalTxt }: { calls: Calls; modalTxt: string }) {
  const b = calls.beli;
  const done = b.target + b.stop;
  const avg = calls.avg;
  return (
    <View style={styles.card}>
      <Text style={ui.cardLabel}>RAPOR SARAN BELI · {b.n} SARAN</Text>
      <Text style={styles.explain}>
        Angka di bawah ini menilai semua saran BELI seolah dibeli semua tanpa batas uang, buat ngukur bagus-enggaknya
        saran app. Daftar paling bawah nunjukin nasib tiap saran di portofolio uji {modalTxt}: dipegang, udah dijual,
        atau gak dibeli (mis. uang gak cukup).
      </Text>
      <View style={styles.stats}>
        <Stat label="Kena Target" val={`${b.target}`} color={C.up} />
        <Stat label="Kena Stop" val={`${b.stop}`} color={C.down} />
        <Stat label="Masih jalan" val={`${b.jalan}`} />
        <Stat label="Gak kebeli" val={`${b.miss}`} />
      </View>
      <Text style={styles.note}>
        {done > 0
          ? `Dari ${done} saran yang udah selesai, ${b.target} kena Target duluan (${Math.round((b.target / done) * 100)}%).`
          : "Belum ada saran BELI yang selesai (kena Target atau Stop)."}
        {b.wait > 0 ? ` ${b.wait} saran nunggu harga penutupan (masuk jam 17.00).` : ""}
      </Text>
      {b.target > 0 ? (
        <Text style={styles.note}>
          <Text style={styles.hitUp}>Kena Target: </Text>
          {doneList(calls.items, "target")}
        </Text>
      ) : null}
      {b.stop > 0 ? (
        <Text style={styles.note}>
          <Text style={styles.hitDown}>Kena Stop: </Text>
          {doneList(calls.items, "stop")}
        </Text>
      ) : null}

      <Text style={styles.part}>RATA-RATA HASIL SEJAK DISARANIN</Text>
      <View style={styles.avgRow}>
        <Avg label="BELI" v={avg.beli} n={calls.n.beli} />
        <Avg label="TUNGGU" v={avg.tunggu} n={calls.n.tunggu} />
        <Avg label="HINDARI" v={avg.hindari} n={calls.n.hindari} />
        <Avg label="IHSG" v={avg.ihsg} />
      </View>

      {calls.items.length > 0 ? <Text style={styles.part}>NASIB TIAP SARAN DI PORTOFOLIO UJI</Text> : null}
      {calls.items.map((it, i) => {
        const f = fate(it);
        return (
          <View key={`${it.date}-${it.ticker}-${i}`} style={styles.callRow}>
            <View style={ui.flex1}>
              <Text style={styles.ticker}>
                {code(it.ticker)} <Text style={styles.callDate}>{fmtDay(it.date)}</Text>
              </Text>
              <Text style={styles.rowSub}>
                Entry {fmtInt(it.entry)} · Target {fmtInt(it.target)} · Stop {fmtInt(it.stop)}
              </Text>
              {f.line ? <Text style={[styles.porto, f.inPorto ? styles.portoIn : null]}>{f.line}</Text> : null}
              {it.result === "target" || it.result === "stop" ? (
                <Text style={[styles.porto, it.result === "target" ? styles.hitUp : styles.hitDown]}>
                  Sarannya kena {it.result === "target" ? `Target ${fmtInt(it.target)}` : `Stop ${fmtInt(it.stop)}`}
                  {it.end ? ` tgl ${fmtDay(it.end)}` : ""}
                </Text>
              ) : null}
            </View>
            <View style={[styles.chip, { borderColor: f.color + "55" }]}>
              <Text style={[styles.chipText, { color: f.color }]}>{f.chip}</Text>
            </View>
          </View>
        );
      })}
    </View>
  );
}

function Stat({ label, val, color }: { label: string; val: string; color?: string }) {
  return (
    <View style={styles.stat}>
      <Text style={ui.metricLabel}>{label}</Text>
      <Text style={[styles.statVal, color ? { color } : null]}>{val}</Text>
    </View>
  );
}

function Avg({ label, v, n }: { label: string; v: number | null; n?: number }) {
  return (
    <View style={styles.avg}>
      <Text style={ui.metricLabel}>{label}</Text>
      <Text style={[styles.avgVal, { color: signColor(v) }]}>{v == null ? "–" : pctPlus(v)}</Text>
      {n != null ? <Text style={styles.avgN}>{n} saham</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  secSub: { color: C.muted, fontSize: 12, marginTop: 2 },
  card: { backgroundColor: C.card, borderRadius: 14, padding: 14, marginTop: 14, borderWidth: 1, borderColor: C.border },
  big: { fontSize: 26, fontWeight: "800", marginTop: 6 },
  bigSub: { color: C.muted, fontSize: 12, fontWeight: "700", marginTop: 2 },
  stats: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", rowGap: 8, marginTop: 12 },
  stat: { width: "48.5%", alignItems: "center", paddingVertical: 10, borderRadius: 10, backgroundColor: C.sunken, borderWidth: 1, borderColor: C.border },
  statVal: { color: C.text, fontSize: 16, fontWeight: "800", marginTop: 2 },
  part: { color: C.muted, fontSize: 11, fontWeight: "800", letterSpacing: 1, marginTop: 18, marginBottom: 2 },
  row: { flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 12, borderTopWidth: 1, borderTopColor: C.border },
  swatch: { width: 4, alignSelf: "stretch", borderRadius: 2 },
  headRow: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: 8 },
  ticker: { color: C.text, fontSize: 15, fontWeight: "800" },
  pill: { color: C.info, fontSize: 11, fontWeight: "700", borderRadius: 6, borderWidth: 1, paddingHorizontal: 6, paddingVertical: 2, borderColor: "rgba(56,189,248,0.35)", backgroundColor: "rgba(56,189,248,0.08)" },
  rowSub: { color: C.muted, fontSize: 11, marginTop: 3 },
  flag: { color: C.up, fontSize: 11, fontWeight: "700", marginTop: 3 },
  right: { alignItems: "flex-end" },
  val: { fontSize: 14, fontWeight: "800" },
  orderRow: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 8, borderTopWidth: 1, borderTopColor: C.border },
  orderText: { color: C.textSoft, fontSize: 12 },
  note: { color: C.label, fontSize: 12, lineHeight: 17, marginTop: 10 },
  avgRow: { flexDirection: "row", gap: 6, marginTop: 8 },
  avg: { flex: 1, alignItems: "center", paddingVertical: 9, borderRadius: 10, backgroundColor: C.sunken, borderWidth: 1, borderColor: C.border },
  avgVal: { fontSize: 15, fontWeight: "800", marginTop: 2 },
  avgN: { color: C.dim, fontSize: 10, marginTop: 1 },
  callRow: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 10, borderTopWidth: 1, borderTopColor: C.border },
  callDate: { color: C.muted, fontSize: 11, fontWeight: "600" },
  explain: { color: C.label, fontSize: 12, lineHeight: 17, marginTop: 6, textAlign: "justify" },
  porto: { color: C.dim, fontSize: 11, marginTop: 3 },
  portoIn: { color: C.accent, fontWeight: "700" },
  hitUp: { color: C.up, fontWeight: "700" },
  hitDown: { color: C.down, fontWeight: "700" },
  chip: { borderWidth: 1, borderRadius: 8, paddingHorizontal: 8, paddingVertical: 4 },
  chipText: { fontSize: 11, fontWeight: "800" },
});
