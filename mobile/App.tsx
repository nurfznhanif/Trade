import { ComponentProps, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Linking,
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
  sentColor,
  sigColor,
  verdictColor,
} from "./src/analysis";
import {
  API_BASE,
  getAnalysis,
  getLlmConfig,
  getNews,
  getPrices,
  getSignals,
  loadApiBase,
  LlmInfo,
  Mover,
  NewsItem,
  Prices,
  runAnalisa,
  saveApiBase,
  setLlmConfig,
  Signal,
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

        {nav === "sinyal" && <SignalsScreen />}
        {nav === "berita" && <NewsScreen />}
        {nav === "chart" && <ChartScreen data={data} />}

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

// ---- fetch helper: loading / data / error dalam satu state ----
function useAsync<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [s, setS] = useState<{ loading: boolean; data: T | null; err: string }>({
    loading: true,
    data: null,
    err: "",
  });
  useEffect(() => {
    let alive = true;
    setS({ loading: true, data: null, err: "" });
    fn()
      .then((d) => alive && setS({ loading: false, data: d, err: "" }))
      .catch((e) => alive && setS({ loading: false, data: null, err: String(e?.message || e) }));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return s;
}

function Loading() {
  return (
    <View style={styles.center}>
      <ActivityIndicator color="#2dd4bf" />
      <Text style={styles.centerText}>Ngambil data…</Text>
    </View>
  );
}

function ErrBox({ msg }: { msg: string }) {
  return (
    <View style={styles.soon}>
      <Ionicons name="cloud-offline-outline" size={40} color="#56606c" />
      <Text style={styles.soonTitle}>Backend belum nyambung</Text>
      <Text style={styles.soonDesc}>{msg || "Gagal ambil data."}</Text>
      <Text style={styles.soonDesc}>Set alamat backend di menu Pengaturan (ikon gerigi kanan atas).</Text>
    </View>
  );
}

function Metric({ label, val, color }: { label: string; val: string; color?: string }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={[styles.metricVal, color ? { color } : null]}>{val}</Text>
    </View>
  );
}

// ============================ TAB SINYAL ============================
function SignalsScreen() {
  const { loading, data, err } = useAsync(() => getSignals(40), []);
  if (loading) return <Loading />;
  if (err || !data) return <ErrBox msg={err} />;
  return (
    <>
      <View style={styles.secHead}>
        <Text style={styles.sectionTitle}>SINYAL MESIN</Text>
        <Text style={styles.secSub}>skor teknikal + sentimen · {data.asof}</Text>
      </View>
      {data.signals.map((s, i) => (
        <SignalRow key={s.ticker} s={s} rank={i + 1} />
      ))}
    </>
  );
}

function SignalRow({ s, rank }: { s: Signal; rank: number }) {
  const col = sigColor(s.action);
  const trend =
    s.ma20 && s.ma50
      ? s.close > s.ma20 && s.ma20 > s.ma50
        ? "uptrend"
        : s.close < s.ma20 && s.ma20 < s.ma50
        ? "downtrend"
        : "sideways"
      : "";
  return (
    <View style={[styles.card, { borderLeftColor: col }]}>
      <View style={styles.cardTop}>
        <View style={styles.sigLeft}>
          <Text style={styles.rank}>#{rank}</Text>
          <Text style={styles.ticker}>{s.ticker.replace(".JK", "")}</Text>
        </View>
        <View style={[styles.badge, { backgroundColor: col + "22", borderColor: col }]}>
          <Text style={[styles.badgeText, { color: col }]}>{s.action}</Text>
        </View>
      </View>
      <View style={styles.metricRow}>
        <Metric label="Skor" val={s.score.toFixed(2)} />
        {s.rsi != null ? (
          <Metric
            label="RSI"
            val={s.rsi.toFixed(0)}
            color={s.rsi >= 70 ? "#ef4444" : s.rsi <= 30 ? "#22c55e" : undefined}
          />
        ) : null}
        {s.sent != null ? (
          <Metric label="Sentimen" val={(s.sent >= 0 ? "+" : "") + s.sent.toFixed(2)} color={sentColor(s.sent)} />
        ) : null}
        <Metric label="Berita" val={String(s.n_news)} />
      </View>
      {trend ? (
        <Text style={styles.trendText}>
          {trend} · harga {fmtInt(s.close)}
        </Text>
      ) : null}
      {s.reasons && s.reasons.length > 0 ? (
        <View style={styles.reasonWrap}>
          {s.reasons.slice(0, 3).map((r, idx) => (
            <View key={idx} style={styles.reasonItem}>
              <View style={[styles.rDot, { backgroundColor: col }]} />
              <Text style={styles.reasonSmall}>{r}</Text>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
}

// ============================ TAB BERITA ============================
function fmtDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(+d)) return "";
  const days = Math.floor((Date.now() - +d) / 86400000);
  if (days <= 0) return "hari ini";
  if (days === 1) return "kemarin";
  if (days < 7) return `${days} hari lalu`;
  return d.toLocaleDateString("id-ID", { day: "numeric", month: "short" });
}

function NewsScreen() {
  const { loading, data, err } = useAsync(() => getNews(undefined, 40), []);
  if (loading) return <Loading />;
  if (err || !data) return <ErrBox msg={err} />;
  return (
    <>
      <View style={styles.secHead}>
        <Text style={styles.sectionTitle}>SENTIMEN BERITA</Text>
        <Text style={styles.secSub}>skor dari isi berita · 14 hari terakhir</Text>
      </View>
      {data.positif.length > 0 || data.negatif.length > 0 ? (
        <View style={styles.moverBox}>
          <MoverRow label="Paling positif" movers={data.positif} pos />
          <MoverRow label="Paling negatif" movers={data.negatif} />
        </View>
      ) : null}
      {data.items.map((n, i) => (
        <NewsCard key={i} n={n} />
      ))}
    </>
  );
}

function MoverRow({ label, movers, pos }: { label: string; movers: Mover[]; pos?: boolean }) {
  if (!movers.length) return null;
  const col = pos ? "#22c55e" : "#ef4444";
  return (
    <View style={styles.moverRow}>
      <Text style={styles.moverLabel}>{label}</Text>
      <View style={styles.moverChips}>
        {movers.map((m) => (
          <View key={m.ticker} style={[styles.moverChip, { borderColor: col + "55" }]}>
            <Text style={[styles.moverTicker, { color: col }]}>{m.ticker.replace(".JK", "")}</Text>
            <Text style={styles.moverAvg}>{(m.avg >= 0 ? "+" : "") + m.avg.toFixed(2)}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

function NewsCard({ n }: { n: NewsItem }) {
  const col = sentColor(n.sent_score);
  const open = () => {
    if (n.link) Linking.openURL(n.link).catch(() => {});
  };
  return (
    <Pressable style={styles.newsCard} onPress={open} disabled={!n.link}>
      <View style={[styles.sentDot, { backgroundColor: col }]} />
      <View style={styles.flex1}>
        <Text style={styles.newsTitle} numberOfLines={2}>
          {n.title}
        </Text>
        <View style={styles.newsMeta}>
          <Text style={[styles.newsTicker, { color: col }]}>{n.ticker.replace(".JK", "")}</Text>
          <Text style={styles.newsDot}>·</Text>
          <Text style={styles.newsSrc}>{n.source || "?"}</Text>
          <Text style={styles.newsDot}>·</Text>
          <Text style={styles.newsSrc}>{fmtDate(n.published)}</Text>
        </View>
      </View>
      {n.link ? <Ionicons name="open-outline" size={15} color="#56606c" /> : null}
    </Pressable>
  );
}

// ============================ TAB CHART ============================
function ChartScreen({ data }: { data: Analysis }) {
  const tickers = useMemo(() => {
    const t = [...data.calls.map((c) => c.ticker), ...(data.positions || []).map((p) => p.ticker)];
    return Array.from(new Set(t));
  }, [data]);
  const [sel, setSel] = useState(tickers[0] || "BMRI.JK");
  const { loading, data: px, err } = useAsync(() => getPrices(sel, 90), [sel]);
  return (
    <>
      <View style={styles.secHead}>
        <Text style={styles.sectionTitle}>CHART HARGA</Text>
        <Text style={styles.secSub}>90 hari · level target/stop dari sinyal</Text>
      </View>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.chipScroll}
        contentContainerStyle={styles.chipScrollInner}
      >
        {tickers.map((t) => (
          <Pressable key={t} onPress={() => setSel(t)} style={[styles.chip, sel === t && styles.chipOn]}>
            <Text style={[styles.chipText, sel === t && styles.chipTextOn]}>{t.replace(".JK", "")}</Text>
          </Pressable>
        ))}
      </ScrollView>
      {loading ? <Loading /> : err || !px ? <ErrBox msg={err} /> : <ChartPanel px={px} />}
    </>
  );
}

function RefLine({ y, color, label }: { y: number; color: string; label: string }) {
  return (
    <View style={[styles.refLine, { top: y }]} pointerEvents="none">
      <View style={[styles.refDash, { borderColor: color }]} />
      <Text style={[styles.refLabel, { color }]}>{label}</Text>
    </View>
  );
}

function ChartPanel({ px }: { px: Prices }) {
  const H = 168;
  const s = px.series;
  const lv = px.levels;
  let lo = Math.min(...s.map((b) => b.low));
  let hi = Math.max(...s.map((b) => b.high));
  [lv.stop, lv.target].forEach((v) => {
    if (v != null) {
      lo = Math.min(lo, v);
      hi = Math.max(hi, v);
    }
  });
  const range = hi - lo || 1;
  const y = (v: number) => H - ((v - lo) / range) * H;
  const up = "#22c55e";
  const down = "#ef4444";
  const chg = px.chg_pct ?? 0;
  const sig = px.signal;
  const sc = sig ? sigColor(sig.action) : "#7d8792";
  return (
    <View>
      <View style={styles.chartHead}>
        <View>
          <Text style={styles.chartTicker}>{px.ticker.replace(".JK", "")}</Text>
          <Text style={styles.chartLast}>
            Rp{fmtInt(px.last)}{" "}
            <Text style={{ color: chg >= 0 ? up : down, fontSize: 13, fontWeight: "700" }}>
              {chg >= 0 ? "+" : ""}
              {chg}% · {px.days}h
            </Text>
          </Text>
        </View>
        {sig ? (
          <View style={[styles.badge, { backgroundColor: sc + "22", borderColor: sc }]}>
            <Text style={[styles.badgeText, { color: sc }]}>{sig.action}</Text>
          </View>
        ) : null}
      </View>

      <View style={[styles.chartBox, { height: H }]}>
        <View style={styles.barsRow}>
          {s.map((b, i) => {
            const top = y(b.high);
            const h = Math.max(1.5, y(b.low) - y(b.high));
            const c = b.close >= b.open ? up : down;
            return (
              <View key={i} style={styles.barCell}>
                <View style={{ marginTop: top, height: h, width: 2.2, borderRadius: 1.5, backgroundColor: c, opacity: 0.85 }} />
              </View>
            );
          })}
        </View>
        {lv.target != null ? <RefLine y={y(lv.target)} color={up} label={`T ${fmtInt(lv.target)}`} /> : null}
        {lv.stop != null ? <RefLine y={y(lv.stop)} color={down} label={`S ${fmtInt(lv.stop)}`} /> : null}
      </View>

      {sig ? (
        <View style={styles.metricRow}>
          <Metric label="Skor" val={sig.score.toFixed(2)} />
          <Metric label="RSI" val={sig.rsi.toFixed(0)} color={sig.rsi >= 70 ? down : sig.rsi <= 30 ? up : undefined} />
          <Metric label="Sentimen" val={(sig.sent >= 0 ? "+" : "") + sig.sent.toFixed(2)} color={sentColor(sig.sent)} />
          {lv.ma20 != null ? <Metric label="MA20" val={fmtInt(lv.ma20)} /> : null}
          {lv.ma50 != null ? <Metric label="MA50" val={fmtInt(lv.ma50)} /> : null}
        </View>
      ) : null}
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

  // ---- shared tab data ----
  center: { alignItems: "center", justifyContent: "center", paddingVertical: 56, gap: 10 },
  centerText: { color: "#7d8792", fontSize: 13 },
  secHead: { marginTop: 18, marginBottom: 2 },
  secSub: { color: "#7d8792", fontSize: 12, marginTop: 2 },
  metricRow: { flexDirection: "row", gap: 16, marginTop: 12, flexWrap: "wrap" },
  metric: { minWidth: 52 },
  metricLabel: { color: "#7d8792", fontSize: 10, fontWeight: "700", letterSpacing: 0.5 },
  metricVal: { color: "#e6edf3", fontSize: 15, fontWeight: "800", marginTop: 2 },

  // ---- Sinyal ----
  sigLeft: { flexDirection: "row", alignItems: "center", gap: 8 },
  rank: { color: "#56606c", fontSize: 13, fontWeight: "800" },
  trendText: { color: "#8b95a1", fontSize: 12, marginTop: 10 },
  reasonWrap: { marginTop: 10, gap: 6 },
  reasonItem: { flexDirection: "row", alignItems: "flex-start", gap: 7 },
  rDot: { width: 5, height: 5, borderRadius: 3, marginTop: 6 },
  reasonSmall: { color: "#c2cbd4", fontSize: 12, lineHeight: 17, flex: 1 },

  // ---- Berita ----
  moverBox: { backgroundColor: "#121821", borderRadius: 14, padding: 12, marginTop: 14, borderWidth: 1, borderColor: "#1e2731", gap: 10 },
  moverRow: { gap: 6 },
  moverLabel: { color: "#7d8792", fontSize: 11, fontWeight: "700", letterSpacing: 0.5 },
  moverChips: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  moverChip: { flexDirection: "row", alignItems: "center", gap: 5, borderWidth: 1, borderRadius: 8, paddingHorizontal: 8, paddingVertical: 4 },
  moverTicker: { fontSize: 12, fontWeight: "800" },
  moverAvg: { color: "#7d8792", fontSize: 11, fontWeight: "700" },
  newsCard: { flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: "#121821", borderRadius: 12, padding: 12, marginTop: 10, borderWidth: 1, borderColor: "#1e2731" },
  sentDot: { width: 9, height: 9, borderRadius: 5 },
  newsTitle: { color: "#e6edf3", fontSize: 13, fontWeight: "600", lineHeight: 18 },
  newsMeta: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 5 },
  newsTicker: { fontSize: 11, fontWeight: "800" },
  newsDot: { color: "#3a434e", fontSize: 11 },
  newsSrc: { color: "#7d8792", fontSize: 11 },

  // ---- Chart ----
  chipScroll: { marginTop: 12, marginBottom: 2 },
  chipScrollInner: { gap: 8, paddingRight: 8 },
  chartHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 14 },
  chartTicker: { color: "#e6edf3", fontSize: 22, fontWeight: "800", letterSpacing: 1 },
  chartLast: { color: "#e6edf3", fontSize: 18, fontWeight: "800", marginTop: 2 },
  chartBox: { backgroundColor: "#0e141b", borderRadius: 12, borderWidth: 1, borderColor: "#1e2731", marginTop: 14, position: "relative", overflow: "hidden" },
  barsRow: { flexDirection: "row", height: "100%", alignItems: "flex-start" },
  barCell: { flex: 1, alignItems: "center" },
  refLine: { position: "absolute", left: 0, right: 0, flexDirection: "row", alignItems: "center" },
  refDash: { flex: 1, borderTopWidth: 1, borderStyle: "dashed", height: 0, opacity: 0.55 },
  refLabel: { fontSize: 9, fontWeight: "800", marginLeft: 4, marginRight: 4 },
});
