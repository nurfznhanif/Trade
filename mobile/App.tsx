import { ComponentProps, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { Ionicons } from "@expo/vector-icons";
import {
  actionColor,
  Analysis,
  Call,
  fmtInt,
  flagColor,
  group,
  pct,
  Position,
  rr,
  sampleAnalysis,
  verdictColor,
} from "./src/analysis";
import {
  API_BASE,
  getAnalysis,
  getLlmConfig,
  loadApiBase,
  LlmInfo,
  runAnalisa,
  saveApiBase,
  setLlmConfig,
  testLlm,
} from "./src/api";

type Tab = "beli" | "tunggu" | "hindari";
const TABS: { key: Tab; label: string }[] = [
  { key: "beli", label: "Beli" },
  { key: "tunggu", label: "Tunggu" },
  { key: "hindari", label: "Hindari" },
];

type Nav = "analisa" | "jurnal" | "sinyal" | "berita" | "chart" | "pengaturan";
type IconName = ComponentProps<typeof Ionicons>["name"];
const NAV_ITEMS: { key: Nav; label: string; icon: IconName }[] = [
  { key: "analisa", label: "Analisa", icon: "stats-chart" },
  { key: "jurnal", label: "Jurnal", icon: "briefcase-outline" },
  { key: "sinyal", label: "Sinyal", icon: "pulse" },
  { key: "berita", label: "Berita", icon: "newspaper-outline" },
  { key: "chart", label: "Chart", icon: "trending-up" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("beli");
  const [nav, setNav] = useState<Nav>("analisa");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<Analysis>(sampleAnalysis);
  const [live, setLive] = useState(false);
  const [note, setNote] = useState("");

  // ambil analisa terbaru dari backend pas app dibuka (pakai alamat tersimpan)
  const loadLive = () =>
    getAnalysis()
      .then((a) => { setData(a); setLive(true); setNote(""); })
      .catch(() => setNote("Backend belum nyambung — nampilin data sampel. Set alamat di Pengaturan."));

  useEffect(() => {
    loadApiBase().then(loadLive);
  }, []);

  const counts = useMemo(() => {
    const c = { beli: 0, tunggu: 0, hindari: 0 };
    data.calls.forEach((x) => (c[group(x.action)] += 1));
    return c;
  }, [data]);

  const shown = data.calls.filter((c) => group(c.action) === tab);
  const regime = data.macro.toUpperCase().includes("RISK-OFF")
    ? "RISK-OFF"
    : data.macro.toUpperCase().includes("RISK-ON")
    ? "RISK-ON"
    : "NETRAL";

  // tombol Analisa: panggil backend jalanin auto_analisa (bisa 1-2 menit)
  const onAnalisa = () => {
    setLoading(true);
    setNote("");
    runAnalisa(data.modal ? String(data.modal) : undefined)
      .then((a) => { setData(a); setLive(true); })
      .catch((e) => setNote("Gagal analisa: " + String(e?.message || e)))
      .finally(() => setLoading(false));
  };

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <StatusBar style="light" />
      <ScrollView style={styles.flex1} contentContainerStyle={styles.scroll}>
        {/* Header (global) */}
        <View style={styles.headerRow}>
          <Text style={styles.logo}>
            TRADE <Text style={styles.logoAccent}>IDX</Text>
          </Text>
          <View style={styles.headerRight}>
            <View
              style={[
                styles.regimePill,
                { borderColor: regime === "RISK-OFF" ? "#ef4444" : "#22c55e" },
              ]}
            >
              <Text
                style={[
                  styles.regimeText,
                  { color: regime === "RISK-OFF" ? "#ef4444" : "#22c55e" },
                ]}
              >
                {regime}
              </Text>
            </View>
            <Pressable onPress={() => setNav("pengaturan")} hitSlop={8}>
              <Ionicons
                name="settings-outline"
                size={22}
                color={nav === "pengaturan" ? "#2dd4bf" : "#7d8792"}
              />
            </Pressable>
          </View>
        </View>
        <Text style={styles.sub}>
          data {data.generated} · {live ? "LIVE" : "sampel"} · {data.engine}
        </Text>
        {note ? <Text style={styles.note}>{note}</Text> : null}

        {nav === "analisa" && (
          <>
            {/* Macro */}
            <View style={styles.macroCard}>
              <Text style={styles.macroLabel}>ANALISIS MAKRO</Text>
              <Text style={styles.macroText}>{data.macro}</Text>
            </View>

            {/* Tombol Analisa */}
            <Pressable
              style={({ pressed }) => [styles.btn, pressed && styles.btnPressed]}
              onPress={onAnalisa}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#04110d" />
              ) : (
                <View style={styles.btnRow}>
                  <Ionicons name="refresh" size={17} color="#04110d" />
                  <Text style={styles.btnText}>ANALISA SEKARANG</Text>
                </View>
              )}
            </Pressable>
            {data.modal ? (
              <Text style={styles.modalNote}>
                Sizing untuk modal Rp{fmtInt(data.modal)}
              </Text>
            ) : null}

            {/* Stat tiles */}
            <View style={styles.tiles}>
              <StatTile n={counts.beli} label="BELI" color="#22c55e" />
              <StatTile n={counts.tunggu} label="TUNGGU" color="#f59e0b" />
              <StatTile n={counts.hindari} label="HINDARI" color="#ef4444" />
            </View>

            {/* Tabs filter */}
            <View style={styles.tabs}>
              {TABS.map((t) => (
                <Pressable
                  key={t.key}
                  style={[styles.tab, tab === t.key && styles.tabActive]}
                  onPress={() => setTab(t.key)}
                >
                  <Text style={[styles.tabText, tab === t.key && styles.tabTextActive]}>
                    {t.label} · {counts[t.key]}
                  </Text>
                </Pressable>
              ))}
            </View>

            {/* Kartu call */}
            {shown.map((c) => (
              <CallCard key={c.ticker} c={c} />
            ))}
          </>
        )}

        {nav === "jurnal" && (
          <>
            <Text style={[styles.sectionTitle, { marginTop: 18 }]}>POSISI TERBUKA</Text>
            {data.positions && data.positions.length > 0 ? (
              data.positions.map((p) => <PositionCard key={p.ticker} p={p} />)
            ) : (
              <Text style={styles.footer}>Belum ada posisi terbuka.</Text>
            )}
          </>
        )}

        {nav === "sinyal" && (
          <Soon icon="pulse" title="Sinyal Mesin" desc="Skor teknikal + sentimen per saham, urut kekuatan. Nyusul pas datanya disambungin." />
        )}
        {nav === "berita" && (
          <Soon icon="newspaper-outline" title="Sentimen Berita" desc="Feed berita per saham + skor sentimen dari isi artikel." />
        )}
        {nav === "chart" && (
          <Soon icon="trending-up" title="Chart Harga" desc="Grafik harga + MA + level entry/target/stop langsung di chart." />
        )}

        {nav === "pengaturan" && <SettingsScreen onConnected={loadLive} />}

        <Text style={styles.footer}>
          Trade IDX · {live ? "tersambung backend" : `backend: ${API_BASE}`}
        </Text>
      </ScrollView>

      <BottomNav nav={nav} setNav={setNav} />
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

function BottomNav({ nav, setNav }: { nav: Nav; setNav: (n: Nav) => void }) {
  return (
    <View style={styles.nav}>
      {NAV_ITEMS.map((it) => {
        const active = nav === it.key;
        return (
          <Pressable key={it.key} style={styles.navBtn} onPress={() => setNav(it.key)}>
            <Ionicons name={it.icon} size={21} color={active ? "#2dd4bf" : "#7d8792"} />
            <Text style={[styles.navLabel, active && styles.navLabelActive]}>{it.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

function Soon({ icon, title, desc }: { icon: IconName; title: string; desc: string }) {
  return (
    <View style={styles.soon}>
      <Ionicons name={icon} size={44} color="#56606c" />
      <Text style={styles.soonTitle}>{title}</Text>
      <Text style={styles.soonDesc}>{desc}</Text>
      <View style={styles.soonTag}>
        <Text style={styles.soonTagText}>SEGERA HADIR</Text>
      </View>
    </View>
  );
}

function StatTile({ n, label, color }: { n: number; label: string; color: string }) {
  return (
    <View style={styles.tile}>
      <Text style={[styles.tileNum, { color }]}>{n}</Text>
      <Text style={styles.tileLabel}>{label}</Text>
    </View>
  );
}

function CallCard({ c }: { c: Call }) {
  const bar = c.flag ? flagColor[c.flag] : actionColor(c.action);
  const toTarget = pct(c.entry, c.target);
  const toStop = pct(c.entry, c.stop);
  const ratio = rr(c);
  const short = c.ticker.replace(".JK", "");
  const lotRp = c.lot && c.entry ? c.lot * 100 * c.entry : null;

  return (
    <View style={[styles.card, { borderLeftColor: bar }]}>
      <View style={styles.cardTop}>
        <Text style={styles.ticker}>{short}</Text>
        <View style={[styles.badge, { backgroundColor: actionColor(c.action) + "22", borderColor: actionColor(c.action) }]}>
          <Text style={[styles.badgeText, { color: actionColor(c.action) }]}>{c.action}</Text>
        </View>
      </View>
      {c.conviction && c.conviction !== "-" ? (
        <Text style={styles.conviction}>Konviksi: {c.conviction}</Text>
      ) : null}

      {c.entry != null ? (
        <View style={styles.levels}>
          <Level label="Entry" val={fmtInt(c.entry)} />
          <Level label="Target" val={fmtInt(c.target)} sub={toTarget ? `+${toTarget}%` : undefined} subColor="#22c55e" />
          <Level label="Stop" val={fmtInt(c.stop)} sub={toStop ? `${toStop}%` : undefined} subColor="#ef4444" />
          {ratio ? <Level label="R:R" val={`1:${ratio}`} /> : null}
        </View>
      ) : null}

      {c.lot ? (
        <View style={styles.lotRow}>
          <Ionicons name="cube-outline" size={14} color="#2dd4bf" />
          <Text style={styles.lot}>
            {c.lot} lot{lotRp ? ` · ~Rp${fmtInt(lotRp)}` : ""}
          </Text>
        </View>
      ) : null}

      <Text style={styles.reason}>{c.reason}</Text>
    </View>
  );
}

function Level({ label, val, sub, subColor }: { label: string; val: string; sub?: string; subColor?: string }) {
  return (
    <View style={styles.level}>
      <Text style={styles.levelLabel}>{label}</Text>
      <Text style={styles.levelVal}>{val}</Text>
      {sub ? <Text style={[styles.levelSub, { color: subColor }]}>{sub}</Text> : null}
    </View>
  );
}

function PositionCard({ p }: { p: Position }) {
  const col = verdictColor(p.verdict);
  return (
    <View style={[styles.posCard, { borderLeftColor: col }]}>
      <View style={styles.cardTop}>
        <Text style={styles.ticker}>{p.ticker.replace(".JK", "")}</Text>
        <View style={[styles.badge, { backgroundColor: col + "22", borderColor: col }]}>
          <Text style={[styles.badgeText, { color: col }]}>{p.verdict}</Text>
        </View>
      </View>
      <Text style={styles.reason}>{p.reason}</Text>
    </View>
  );
}

function SettingsScreen({ onConnected }: { onConnected: () => void }) {
  const [info, setInfo] = useState<LlmInfo | null>(null);
  const [prov, setProv] = useState("gemini");
  const [model, setModel] = useState("");
  const [key, setKey] = useState("");
  const [base, setBase] = useState(API_BASE);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const loadConfig = () =>
    getLlmConfig()
      .then((i) => { setInfo(i); setProv(i.provider); setModel(i.model); })
      .catch((e) => setMsg("Backend belum nyambung: " + String(e?.message || e)));

  useEffect(() => { loadConfig(); }, []);

  const providers = info ? Object.entries(info.providers) : [];
  const pinfo = info?.providers[prov];

  const save = async () => {
    setBusy(true); setMsg("");
    await saveApiBase(base);
    setLlmConfig({ provider: prov, model: model.trim(), api_key: key.trim() || undefined })
      .then(() => { setMsg("Tersimpan. Provider aktif: " + (pinfo?.label || prov)); setKey(""); loadConfig(); onConnected(); })
      .catch((e) => setMsg("Gagal simpan: " + String(e?.message || e)))
      .finally(() => setBusy(false));
  };
  const test = async () => {
    setBusy(true); setMsg("Nyoba nyambung…");
    await saveApiBase(base);
    testLlm()
      .then((r) => { setMsg(r.message); if (r.ok) { loadConfig(); onConnected(); } })
      .catch((e) => setMsg("Gagal tes: " + String(e?.message || e)))
      .finally(() => setBusy(false));
  };

  return (
    <View style={{ marginTop: 8 }}>
      <Text style={styles.settTitle}>Pengaturan LLM</Text>
      <Text style={styles.settSub}>Bongkar-pasang otak analisa — gak terpaku ke Gemini.</Text>

      <Text style={styles.settLabel}>Alamat Backend</Text>
      <TextInput style={styles.input} value={base} onChangeText={setBase}
        autoCapitalize="none" autoCorrect={false}
        placeholder="http://192.168.x.x:8000" placeholderTextColor="#56606c" />

      <Text style={styles.settLabel}>Provider</Text>
      <View style={styles.chips}>
        {providers.map(([k, v]) => (
          <Pressable key={k} onPress={() => { setProv(k); setModel(v.models[0] || ""); }}
            style={[styles.chip, prov === k && styles.chipOn]}>
            <Text style={[styles.chipText, prov === k && styles.chipTextOn]}>{v.label}</Text>
          </Pressable>
        ))}
        {providers.length === 0 ? <Text style={styles.hint}>Sambungin backend dulu buat lihat daftar provider.</Text> : null}
      </View>

      <Text style={styles.settLabel}>Model</Text>
      <TextInput style={styles.input} value={model} onChangeText={setModel}
        autoCapitalize="none" autoCorrect={false}
        placeholder="nama model" placeholderTextColor="#56606c" />
      {pinfo && pinfo.models.length > 0 ? (
        <Text style={styles.hint}>Contoh: {pinfo.models.join(" · ")}</Text>
      ) : null}

      <Text style={styles.settLabel}>
        API Key{info?.has_key ? " (udah ada — isi cuma kalau mau ganti)" : ""}
      </Text>
      <TextInput style={styles.input} value={key} onChangeText={setKey} secureTextEntry
        autoCapitalize="none" autoCorrect={false}
        placeholder="tempel API key" placeholderTextColor="#56606c" />
      {pinfo && pinfo.key_url !== "-" ? (
        <Text style={styles.hint}>Ambil key: {pinfo.key_url}</Text>
      ) : null}

      <View style={styles.settBtns}>
        <Pressable style={[styles.settBtn, styles.settBtnPri]} onPress={save} disabled={busy}>
          <Text style={styles.settBtnPriText}>{busy ? "…" : "Simpan"}</Text>
        </Pressable>
        <Pressable style={[styles.settBtn, styles.settBtnGhost]} onPress={test} disabled={busy}>
          <Text style={styles.settBtnGhostText}>Tes Koneksi</Text>
        </Pressable>
      </View>
      {msg ? <Text style={styles.settMsg}>{msg}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#0a0e13" },
  flex1: { flex: 1 },
  headerRight: { flexDirection: "row", alignItems: "center", gap: 12 },
  note: { color: "#fbbf24", fontSize: 12, marginTop: 6 },

  // Pengaturan (Settings)
  settTitle: { color: "#e6edf3", fontSize: 20, fontWeight: "800" },
  settSub: { color: "#7d8792", fontSize: 13, marginTop: 3 },
  settLabel: { color: "#8b95a1", fontSize: 11, fontWeight: "700", letterSpacing: 0.5, marginTop: 16, marginBottom: 6 },
  input: { backgroundColor: "#121821", borderWidth: 1, borderColor: "#1e2731", borderRadius: 10, paddingHorizontal: 12, paddingVertical: 11, color: "#e6edf3", fontSize: 14 },
  hint: { color: "#56606c", fontSize: 11, marginTop: 5 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: { borderWidth: 1, borderColor: "#1e2731", backgroundColor: "#121821", borderRadius: 999, paddingHorizontal: 13, paddingVertical: 7 },
  chipOn: { borderColor: "#2dd4bf", backgroundColor: "rgba(45,212,191,0.12)" },
  chipText: { color: "#8b95a1", fontSize: 12, fontWeight: "700" },
  chipTextOn: { color: "#2dd4bf" },
  settBtns: { flexDirection: "row", gap: 10, marginTop: 20 },
  settBtn: { flex: 1, borderRadius: 12, paddingVertical: 13, alignItems: "center" },
  settBtnPri: { backgroundColor: "#2dd4bf" },
  settBtnPriText: { color: "#04110d", fontSize: 14, fontWeight: "800", letterSpacing: 0.5 },
  settBtnGhost: { borderWidth: 1, borderColor: "#1e2731", backgroundColor: "#121821" },
  settBtnGhostText: { color: "#e6edf3", fontSize: 14, fontWeight: "700" },
  settMsg: { color: "#c2cbd4", fontSize: 13, marginTop: 14, lineHeight: 19 },
  scroll: { padding: 16, paddingBottom: 32 },

  // Bottom navigation (pola mobile — bukan sidebar)
  nav: { flexDirection: "row", backgroundColor: "#0c1117", borderTopWidth: 1, borderTopColor: "#1e2731", paddingTop: 8, paddingBottom: 10 },
  navBtn: { flex: 1, alignItems: "center", gap: 3, paddingVertical: 2 },
  navIcon: { fontSize: 20, opacity: 0.5 },
  navIconActive: { opacity: 1 },
  navLabel: { color: "#7d8792", fontSize: 10, fontWeight: "700", letterSpacing: 0.3 },
  navLabelActive: { color: "#2dd4bf" },

  // Placeholder view
  soon: { alignItems: "center", paddingVertical: 64, gap: 9 },
  soonEm: { fontSize: 44 },
  soonTitle: { color: "#e6edf3", fontSize: 17, fontWeight: "800" },
  soonDesc: { color: "#7d8792", fontSize: 13, textAlign: "center", maxWidth: 250, lineHeight: 19 },
  soonTag: { marginTop: 4, borderWidth: 1, borderColor: "#1e2731", borderRadius: 999, paddingHorizontal: 11, paddingVertical: 4 },
  soonTagText: { color: "#56606c", fontSize: 10, fontWeight: "700", letterSpacing: 1 },
  headerRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  logo: { color: "#e6edf3", fontSize: 26, fontWeight: "800", letterSpacing: 1 },
  logoAccent: { color: "#2dd4bf" },
  regimePill: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4 },
  regimeText: { fontSize: 12, fontWeight: "800", letterSpacing: 1 },
  sub: { color: "#7d8792", fontSize: 12, marginTop: 4 },

  macroCard: { backgroundColor: "#121821", borderRadius: 14, padding: 14, marginTop: 14, borderWidth: 1, borderColor: "#1e2731" },
  macroLabel: { color: "#2dd4bf", fontSize: 11, fontWeight: "800", letterSpacing: 1, marginBottom: 6 },
  macroText: { color: "#c2cbd4", fontSize: 13, lineHeight: 19 },

  btn: { backgroundColor: "#2dd4bf", borderRadius: 14, paddingVertical: 15, alignItems: "center", marginTop: 16 },
  btnPressed: { opacity: 0.8 },
  btnText: { color: "#04110d", fontSize: 15, fontWeight: "800", letterSpacing: 1 },
  btnRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  modalNote: { color: "#7d8792", fontSize: 12, textAlign: "center", marginTop: 8 },

  tiles: { flexDirection: "row", gap: 10, marginTop: 16 },
  tile: { flex: 1, backgroundColor: "#121821", borderRadius: 12, paddingVertical: 14, alignItems: "center", borderWidth: 1, borderColor: "#1e2731" },
  tileNum: { fontSize: 24, fontWeight: "800" },
  tileLabel: { color: "#7d8792", fontSize: 11, fontWeight: "700", letterSpacing: 1, marginTop: 2 },

  tabs: { flexDirection: "row", backgroundColor: "#121821", borderRadius: 12, padding: 4, marginTop: 16, borderWidth: 1, borderColor: "#1e2731" },
  tab: { flex: 1, paddingVertical: 9, alignItems: "center", borderRadius: 9 },
  tabActive: { backgroundColor: "#1e2731" },
  tabText: { color: "#7d8792", fontSize: 13, fontWeight: "700" },
  tabTextActive: { color: "#e6edf3" },

  card: { backgroundColor: "#121821", borderRadius: 14, padding: 14, marginTop: 12, borderLeftWidth: 4, borderWidth: 1, borderColor: "#1e2731" },
  cardTop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  ticker: { color: "#e6edf3", fontSize: 19, fontWeight: "800", letterSpacing: 1 },
  badge: { borderWidth: 1, borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3 },
  badgeText: { fontSize: 11, fontWeight: "800", letterSpacing: 0.5 },
  conviction: { color: "#7d8792", fontSize: 12, marginTop: 3 },

  levels: { flexDirection: "row", gap: 8, marginTop: 12, flexWrap: "wrap" },
  level: { minWidth: 64 },
  levelLabel: { color: "#7d8792", fontSize: 10, fontWeight: "700", letterSpacing: 0.5 },
  levelVal: { color: "#e6edf3", fontSize: 16, fontWeight: "800", marginTop: 2 },
  levelSub: { fontSize: 11, fontWeight: "700", marginTop: 1 },

  lot: { color: "#2dd4bf", fontSize: 13, fontWeight: "700" },
  lotRow: { flexDirection: "row", alignItems: "center", gap: 5, marginTop: 10 },
  reason: { color: "#c2cbd4", fontSize: 13, lineHeight: 19, marginTop: 10 },

  sectionTitle: { color: "#7d8792", fontSize: 12, fontWeight: "800", letterSpacing: 1, marginTop: 26, marginBottom: 2 },
  posCard: { backgroundColor: "#121821", borderRadius: 14, padding: 14, marginTop: 12, borderLeftWidth: 4, borderWidth: 1, borderColor: "#1e2731" },

  footer: { color: "#4b5560", fontSize: 11, textAlign: "center", marginTop: 28 },
});
