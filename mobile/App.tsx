import { ComponentProps, useEffect, useMemo, useRef, useState } from "react";
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
  fmtWaktu,
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
  addTrade,
  API_BASE,
  API_TOKEN,
  closeTrade,
  deleteLlmKey,
  deleteTrade,
  getAnalysis,
  getJournal,
  getLlmModels,
  getLlmConfig,
  getMacro,
  getNews,
  getPrices,
  getSignals,
  JournalSummary,
  JournalTrade,
  loadApiBase,
  LlmInfo,
  MacroItem,
  Mover,
  NewsItem,
  Prices,
  runAnalisa,
  saveApiBase,
  saveApiToken,
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
  const [macro, setMacro] = useState<MacroItem[]>([]);
  const [conn, setConn] = useState<"cari" | "ok" | "mati">("cari");

  // ambil analisa + angka makro dari backend
  const loadLive = (hit = true) => {
    getAnalysis()
      .then((a) => { setData(a); setLive(true); setNote(""); })
      .catch((e) => { setLive(false); setNote(hit ? "Gagal ambil analisa: " + String(e?.message || e) : ""); });
    getMacro()
      .then((m) => setMacro(m.items))
      .catch(() => setMacro([]));
  };

  // cari server di PC otomatis (gak perlu isi alamat), terus muat data
  const connect = () => {
    setConn("cari");
    loadApiBase().then((hit) => {
      setConn(hit ? "ok" : "mati");
      loadLive(!!hit);
    });
  };

  useEffect(() => {
    connect();
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
          <Pressable onPress={() => setNav("pengaturan")} hitSlop={8}>
            <Ionicons
              name="settings-outline"
              size={22}
              color={nav === "pengaturan" ? "#2dd4bf" : "#7d8792"}
            />
          </Pressable>
        </View>
        <Text style={styles.sub}>
          {fmtWaktu(data.generated_at, data.generated)}
        </Text>
        {conn === "cari" ? <Text style={styles.sub}>Nyari server di PC…</Text> : null}
        {conn === "mati" ? <OfflineCard onRetry={connect} /> : null}
        {note ? <Text style={styles.note}>{note}</Text> : null}

        {nav === "analisa" && (
          <>
            {/* Macro */}
            <View style={styles.macroCard}>
              <View style={styles.macroHead}>
                <Text style={styles.macroLabel}>ANALISIS MAKRO</Text>
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
              </View>
              <Text style={styles.macroText}>{data.macro}</Text>
              {macro.length > 0 ? (
                <ScrollView
                  horizontal
                  showsHorizontalScrollIndicator={false}
                  style={styles.macroStrip}
                  contentContainerStyle={styles.macroStripInner}
                >
                  {macro.map((m) => (
                    <MacroTile key={m.ticker} m={m} />
                  ))}
                </ScrollView>
              ) : null}
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

        {nav === "jurnal" && <JournalScreen data={data} />}

        {nav === "sinyal" && <SignalsScreen />}
        {nav === "berita" && <NewsScreen />}
        {nav === "chart" && <ChartScreen data={data} />}

        {nav === "pengaturan" && (
          <SettingsScreen connected={conn === "cari" ? null : conn === "ok" && live} onConnected={connect} />
        )}

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
      <Text style={styles.soonTitle}>Server belum nyambung</Text>
      <Text style={styles.soonDesc}>{msg || "Gagal ambil data."}</Text>
      <Text style={styles.soonDesc}>Cek internet HP. Kalau pakai server di PC: double-klik run_backend.bat.</Text>
    </View>
  );
}

// kartu pas server di PC gak ketemu — jelasin langkahnya + tombol coba lagi
function OfflineCard({ onRetry }: { onRetry: () => void }) {
  return (
    <View style={styles.offCard}>
      <View style={styles.offHead}>
        <Ionicons name="desktop-outline" size={17} color="#f59e0b" />
        <Text style={styles.offTitle}>Server belum nyambung</Text>
      </View>
      <Text style={styles.offDesc}>
        Cek internet HP, lalu ketuk Sambung ulang. Kalau pakai server di PC: double-klik{" "}
        <Text style={styles.offCode}>run_backend.bat</Text> dulu. Sementara ini yang tampil data sampel.
      </Text>
      <Pressable style={({ pressed }) => [styles.offBtn, pressed && styles.btnPressed]} onPress={onRetry}>
        <Ionicons name="refresh" size={15} color="#f59e0b" />
        <Text style={styles.offBtnText}>Sambung ulang</Text>
      </Pressable>
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

// angka makro: >=1000 -> ribuan pakai titik (17.531); <1000 -> 2 desimal koma (98,73)
function fmtMacro(n: number): string {
  if (n >= 1000) return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return n.toFixed(2).replace(".", ",");
}

function MacroTile({ m }: { m: MacroItem }) {
  const col = m.chg > 0 ? "#22c55e" : m.chg < 0 ? "#ef4444" : "#7d8792";
  return (
    <View style={styles.macroTile}>
      <Text style={styles.macroTileLabel}>{m.label}</Text>
      <Text style={styles.macroTileVal}>
        {m.unit === "$" ? "$" : ""}
        {fmtMacro(m.last)}
        {m.unit === "%" ? "%" : ""}
      </Text>
      <Text style={[styles.macroTileChg, { color: col }]}>
        {m.chg >= 0 ? "+" : ""}
        {m.chg}%
      </Text>
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

// ============================ TAB JURNAL ============================
// tanggal lokal hari ini "2026-09-25" (default tgl beli/jual)
function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// "6.500" / "6500" -> 6500 ; kosong -> null
function num(s: string): number | null {
  const c = s.replace(/[^\d,]/g, "").replace(",", ".");
  return c ? Number(c) : null;
}

function rpSigned(n: number | null | undefined): string {
  if (n == null) return "–";
  return (n > 0 ? "+" : n < 0 ? "-" : "") + "Rp" + fmtInt(Math.abs(n));
}

function pctSigned(x: number | null | undefined): string {
  if (x == null) return "–";
  return (x > 0 ? "+" : "") + (x * 100).toFixed(1) + "%";
}

const plColor = (n: number | null | undefined) =>
  n == null || n === 0 ? "#7d8792" : n > 0 ? "#22c55e" : "#ef4444";

// "2026-09-15" -> "15 Sep"
function fmtDay(iso: string | null): string {
  if (!iso) return "–";
  const d = new Date(iso.slice(0, 10) + "T00:00:00");
  return isNaN(+d) ? iso : d.toLocaleDateString("id-ID", { day: "numeric", month: "short" });
}

function daysSince(iso: string): number {
  return Math.max(0, Math.floor((Date.now() - +new Date(iso.slice(0, 10) + "T00:00:00")) / 86400000));
}

function JournalScreen({ data }: { data: Analysis }) {
  const [j, setJ] = useState<{ trades: JournalTrade[]; summary: JournalSummary } | null>(null);
  const [err, setErr] = useState("");
  const [adding, setAdding] = useState(false);

  // reload tanpa ngosongin layar (data lama tetap nongol selama ngambil)
  const load = () =>
    getJournal()
      .then((d) => { setJ(d); setErr(""); })
      .catch((e) => setErr(String(e?.message || e)));

  useEffect(() => { load(); }, []);

  if (!j && !err) return <Loading />;
  if (!j) return <ErrBox msg={err} />;

  const open = j.trades.filter((t) => t.status === "open");
  const closed = j.trades.filter((t) => t.status === "closed");
  const verdicts = new Map((data.positions || []).map((p) => [p.ticker, p]));

  return (
    <>
      <View style={styles.secHead}>
        <Text style={styles.sectionTitle}>JURNAL REAL</Text>
        <Text style={styles.secSub}>catatan beli-jual beneran di broker</Text>
      </View>
      {err ? <Text style={styles.note}>{err}</Text> : null}

      {j.trades.length > 0 ? <JournalSummaryCard s={j.summary} /> : null}

      {adding ? (
        <AddTradeForm
          calls={data.calls}
          onDone={() => { setAdding(false); load(); }}
          onCancel={() => setAdding(false)}
        />
      ) : (
        <Pressable
          style={({ pressed }) => [styles.btn, pressed && styles.btnPressed]}
          onPress={() => setAdding(true)}
        >
          <View style={styles.btnRow}>
            <Ionicons name="add-circle-outline" size={18} color="#04110d" />
            <Text style={styles.btnText}>CATAT BELI</Text>
          </View>
        </Pressable>
      )}

      {j.trades.length === 0 && !adding ? (
        <View style={styles.soon}>
          <Ionicons name="book-outline" size={40} color="#56606c" />
          <Text style={styles.soonTitle}>Jurnal masih kosong</Text>
          <Text style={styles.soonDesc}>
            Catat saham yang udah dibeli di broker — untung-ruginya kehitung otomatis dari harga penutupan.
          </Text>
        </View>
      ) : null}

      {open.length > 0 ? <Text style={styles.sectionTitle}>POSISI TERBUKA · {open.length}</Text> : null}
      {open.map((t) => (
        <OpenTradeCard key={t.id} t={t} verdict={verdicts.get(t.ticker)} onChanged={load} />
      ))}

      {closed.length > 0 ? <Text style={styles.sectionTitle}>RIWAYAT TERTUTUP · {closed.length}</Text> : null}
      {closed.map((t) => (
        <ClosedTradeCard key={t.id} t={t} onChanged={load} />
      ))}
    </>
  );
}

function JournalSummaryCard({ s }: { s: JournalSummary }) {
  return (
    <View style={styles.jSum}>
      <Text style={styles.jSumLabel}>TOTAL UNTUNG / RUGI</Text>
      <Text style={[styles.jSumTotal, { color: plColor(s.total) }]}>{rpSigned(s.total)}</Text>
      <View style={styles.metricRow}>
        <Metric label="Realized" val={rpSigned(s.realized)} color={plColor(s.realized)} />
        <Metric label="Floating" val={rpSigned(s.unreal)} color={plColor(s.unreal)} />
        <Metric
          label="Win rate"
          val={s.closed ? `${Math.round(s.win_rate * 100)}% · ${s.wins}/${s.closed}` : "–"}
        />
      </View>
    </View>
  );
}

function Field({
  label, value, onChange, placeholder, numeric, caps,
}: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string;
  numeric?: boolean; caps?: boolean;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        style={[styles.input, styles.fieldInput]}
        value={value}
        onChangeText={onChange}
        placeholder={placeholder}
        placeholderTextColor="#56606c"
        keyboardType={numeric ? "numeric" : "default"}
        autoCapitalize={caps ? "characters" : "none"}
        autoCorrect={false}
      />
    </View>
  );
}

function ActBtn({
  icon, label, onPress, danger,
}: { icon: IconName; label: string; onPress: () => void; danger?: boolean }) {
  const c = danger ? "#ef4444" : "#c2cbd4";
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.actBtn, danger && styles.actBtnDanger, pressed && styles.btnPressed]}
    >
      <Ionicons name={icon} size={15} color={c} />
      <Text style={[styles.actBtnText, { color: c }]}>{label}</Text>
    </Pressable>
  );
}

function AddTradeForm({
  calls, onDone, onCancel,
}: { calls: Call[]; onDone: () => void; onCancel: () => void }) {
  const picks = calls.filter((c) => c.action.startsWith("BELI") && c.entry);
  const blank = { ticker: "", entry: "", lot: "1", stop: "", target: "", date: todayIso(), thesis: "" };
  const [f, setF] = useState(blank);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const set = (k: keyof typeof blank) => (v: string) => setF((o) => ({ ...o, [k]: v }));

  // isi otomatis dari saran analisa hari ini (harga tinggal disesuaiin sama harga nyata di broker)
  const pick = (c: Call) =>
    setF({
      ticker: c.ticker.replace(".JK", ""),
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
      .catch((e) => setMsg(String(e?.message || e)))
      .finally(() => setBusy(false));
  };

  return (
    <View style={styles.formCard}>
      <View style={styles.cardTop}>
        <Text style={styles.formTitle}>Catat Beli</Text>
        <Pressable onPress={onCancel} hitSlop={8}>
          <Ionicons name="close" size={20} color="#7d8792" />
        </Pressable>
      </View>

      {picks.length > 0 ? (
        <>
          <Text style={styles.fieldLabel}>DARI SARAN ANALISA HARI INI</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipScrollInner}>
            {picks.map((c) => {
              const on = f.ticker === c.ticker.replace(".JK", "");
              return (
                <Pressable key={c.ticker} onPress={() => pick(c)} style={[styles.chip, on && styles.chipOn]}>
                  <Text style={[styles.chipText, on && styles.chipTextOn]}>
                    {c.ticker.replace(".JK", "")} · {fmtInt(c.entry)}
                  </Text>
                </Pressable>
              );
            })}
          </ScrollView>
        </>
      ) : null}

      <View style={styles.formRow}>
        <Field label="Kode" value={f.ticker} onChange={set("ticker")} placeholder="BBCA" caps />
        <Field label="Harga beli" value={f.entry} onChange={set("entry")} placeholder="6500" numeric />
        <Field label="Lot" value={f.lot} onChange={set("lot")} placeholder="1" numeric />
      </View>
      <View style={styles.formRow}>
        <Field label="Stop" value={f.stop} onChange={set("stop")} placeholder="opsional" numeric />
        <Field label="Target" value={f.target} onChange={set("target")} placeholder="opsional" numeric />
        <Field label="Tgl beli" value={f.date} onChange={set("date")} placeholder={todayIso()} />
      </View>
      <View style={styles.formRow}>
        <Field label="Alasan beli" value={f.thesis} onChange={set("thesis")} placeholder="opsional" />
      </View>

      {value ? <Text style={styles.hint}>Nilai posisi ~Rp{fmtInt(value)}</Text> : null}
      {msg ? <Text style={styles.formErr}>{msg}</Text> : null}

      <View style={styles.jBtns}>
        <Pressable style={[styles.settBtn, styles.settBtnPri]} onPress={save} disabled={busy}>
          <Text style={styles.settBtnPriText}>{busy ? "…" : "Simpan"}</Text>
        </Pressable>
        <Pressable style={[styles.settBtn, styles.settBtnGhost]} onPress={onCancel} disabled={busy}>
          <Text style={styles.settBtnGhostText}>Batal</Text>
        </Pressable>
      </View>
    </View>
  );
}

function OpenTradeCard({
  t, verdict, onChanged,
}: { t: JournalTrade; verdict?: Position; onChanged: () => void }) {
  const [mode, setMode] = useState<"" | "close" | "delete">("");
  const col = plColor(t.pl_rp);

  // posisi harga vs garis jual (trailing stop)
  let st: { text: string; color: string } | null = null;
  if (t.px != null && t.trail != null) {
    const cushion = ((t.px - t.trail) / t.px) * 100;
    st =
      t.px < t.trail
        ? { text: "Tembus garis jual — evaluasi keluar", color: "#ef4444" }
        : cushion < 3
        ? { text: `Waspada — tinggal ${cushion.toFixed(1)}% di atas garis jual`, color: "#f59e0b" }
        : { text: `Aman — ${cushion.toFixed(1)}% di atas garis jual`, color: "#22c55e" };
  }
  const vc = verdict ? verdictColor(verdict.verdict) : "";

  return (
    <View style={[styles.card, { borderLeftColor: col }]}>
      <View style={styles.cardTop}>
        <View style={styles.sigLeft}>
          <Text style={styles.ticker}>{t.ticker.replace(".JK", "")}</Text>
          {verdict ? (
            <View style={[styles.badge, { backgroundColor: vc + "22", borderColor: vc }]}>
              <Text style={[styles.badgeText, { color: vc }]}>{verdict.verdict}</Text>
            </View>
          ) : null}
        </View>
        <Text style={[styles.jPct, { color: col }]}>{pctSigned(t.gross_pct)}</Text>
      </View>
      <Text style={styles.conviction}>
        {fmtInt(t.lot)} lot · beli {fmtDay(t.entry_date)} · dipegang {daysSince(t.entry_date)} hari
      </Text>

      <View style={styles.levels}>
        <Level label="Modal" val={fmtInt(t.entry)} />
        <Level label="Harga" val={fmtInt(t.px)} sub={t.px_date ? `close ${fmtDay(t.px_date)}` : undefined} subColor="#7d8792" />
        <Level label="Garis jual" val={fmtInt(t.trail)} />
        {t.target != null ? <Level label="Target" val={fmtInt(t.target)} /> : null}
      </View>

      <View style={styles.jPlRow}>
        <Text style={styles.jPlLabel}>P/L</Text>
        <Text style={[styles.jPlVal, { color: col }]}>{rpSigned(t.pl_rp)}</Text>
      </View>
      {st ? (
        <View style={styles.lotRow}>
          <View style={[styles.jDot, { backgroundColor: st.color }]} />
          <Text style={[styles.jStatus, { color: st.color }]}>{st.text}</Text>
        </View>
      ) : null}
      {verdict?.reason ? <Text style={styles.reason} numberOfLines={3}>{verdict.reason}</Text> : null}
      {t.thesis ? <Text style={styles.jThesis}>Alasan: {t.thesis}</Text> : null}

      {mode === "close" ? (
        <CloseForm t={t} onDone={onChanged} onCancel={() => setMode("")} />
      ) : mode === "delete" ? (
        <ConfirmDelete t={t} onDone={onChanged} onCancel={() => setMode("")} />
      ) : (
        <View style={styles.jActions}>
          <ActBtn icon="checkmark-done-outline" label="Tutup posisi" onPress={() => setMode("close")} />
          <View style={styles.flex1} />
          <ActBtn icon="trash-outline" label="Hapus" danger onPress={() => setMode("delete")} />
        </View>
      )}
    </View>
  );
}

function ClosedTradeCard({ t, onChanged }: { t: JournalTrade; onChanged: () => void }) {
  const [del, setDel] = useState(false);
  const col = plColor(t.pl_rp);
  return (
    <View style={[styles.card, { borderLeftColor: col }]}>
      <View style={styles.cardTop}>
        <Text style={styles.ticker}>{t.ticker.replace(".JK", "")}</Text>
        <Text style={[styles.jPct, { color: col }]}>{pctSigned(t.gross_pct)}</Text>
      </View>
      <Text style={styles.conviction}>
        {fmtInt(t.lot)} lot · {fmtInt(t.entry)} → {fmtInt(t.exit)} · {fmtDay(t.entry_date)} – {fmtDay(t.exit_date)}
      </Text>
      <View style={styles.jPlRow}>
        <Text style={styles.jPlLabel}>P/L</Text>
        <Text style={[styles.jPlVal, { color: col }]}>{rpSigned(t.pl_rp)}</Text>
        <Text style={styles.jNet}>bersih setelah fee {pctSigned(t.net_pct)}</Text>
      </View>
      {t.thesis ? <Text style={styles.jThesis}>Alasan: {t.thesis}</Text> : null}

      {del ? (
        <ConfirmDelete t={t} onDone={onChanged} onCancel={() => setDel(false)} />
      ) : (
        <View style={styles.jActions}>
          <View style={styles.flex1} />
          <ActBtn icon="trash-outline" label="Hapus" danger onPress={() => setDel(true)} />
        </View>
      )}
    </View>
  );
}

function CloseForm({ t, onDone, onCancel }: { t: JournalTrade; onDone: () => void; onCancel: () => void }) {
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
      .catch((e) => setMsg(String(e?.message || e)))
      .finally(() => setBusy(false));
  };

  return (
    <View style={styles.jInline}>
      <Text style={styles.fieldLabel}>TUTUP POSISI — HARGA JUAL NYATA DI BROKER</Text>
      <View style={styles.formRow}>
        <Field label="Harga jual" value={px} onChange={setPx} numeric />
        <Field label="Tgl jual" value={d} onChange={setD} placeholder={todayIso()} />
      </View>
      {result != null && exit ? (
        <Text style={[styles.jPreview, { color: plColor(result) }]}>
          Hasil: {rpSigned(result)} ({pctSigned(exit / t.entry - 1)})
        </Text>
      ) : null}
      {msg ? <Text style={styles.formErr}>{msg}</Text> : null}
      <View style={styles.jBtns}>
        <Pressable style={[styles.settBtn, styles.settBtnPri]} onPress={save} disabled={busy}>
          <Text style={styles.settBtnPriText}>{busy ? "…" : "Simpan jual"}</Text>
        </Pressable>
        <Pressable style={[styles.settBtn, styles.settBtnGhost]} onPress={onCancel} disabled={busy}>
          <Text style={styles.settBtnGhostText}>Batal</Text>
        </Pressable>
      </View>
    </View>
  );
}

// hapus 2 langkah (tap Hapus -> konfirmasi) biar gak kepencet
function ConfirmDelete({ t, onDone, onCancel }: { t: JournalTrade; onDone: () => void; onCancel: () => void }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const del = () => {
    setBusy(true);
    setMsg("");
    deleteTrade(t.id)
      .then(onDone)
      .catch((e) => setMsg(String(e?.message || e)))
      .finally(() => setBusy(false));
  };
  return (
    <View style={styles.jInline}>
      <View style={styles.lotRow}>
        <Ionicons name="warning-outline" size={16} color="#ef4444" />
        <Text style={styles.jConfirm}>
          Hapus catatan {t.ticker.replace(".JK", "")} ({fmtInt(t.lot)} lot @ {fmtInt(t.entry)})? Permanen, gak bisa dibalikin.
        </Text>
      </View>
      {msg ? <Text style={styles.formErr}>{msg}</Text> : null}
      <View style={styles.jBtns}>
        <Pressable style={[styles.settBtn, styles.jBtnDanger]} onPress={del} disabled={busy}>
          <Text style={styles.jBtnDangerText}>{busy ? "…" : "Ya, hapus"}</Text>
        </Pressable>
        <Pressable style={[styles.settBtn, styles.settBtnGhost]} onPress={onCancel} disabled={busy}>
          <Text style={styles.settBtnGhostText}>Batal</Text>
        </Pressable>
      </View>
    </View>
  );
}

// dropdown sederhana (buka-tutup di tempat) — jalan sama di Android & web
function Dropdown({
  label, value, options, onChange, placeholder, disabled,
}: {
  label: string; value: string; options: { value: string; label: string }[];
  onChange: (v: string) => void; placeholder: string; disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const cur = options.find((o) => o.value === value);
  return (
    <View>
      <Text style={styles.settLabel}>{label}</Text>
      <Pressable
        style={[styles.input, styles.ddBox, open && styles.ddBoxOpen, disabled && styles.ddDisabled]}
        onPress={() => !disabled && setOpen((o) => !o)}
      >
        <Text style={[styles.ddText, !cur && styles.ddPlaceholder]} numberOfLines={1}>
          {cur ? cur.label : placeholder}
        </Text>
        <Ionicons name={open ? "chevron-up" : "chevron-down"} size={16} color="#7d8792" />
      </Pressable>
      {open ? (
        <View style={styles.ddList}>
          {options.map((o) => {
            const on = o.value === value;
            return (
              <Pressable
                key={o.value}
                style={({ pressed }) => [styles.ddItem, on && styles.ddItemOn, pressed && styles.btnPressed]}
                onPress={() => { onChange(o.value); setOpen(false); }}
              >
                <Text style={[styles.ddItemText, on && styles.ddItemTextOn]}>{o.label}</Text>
                {on ? <Ionicons name="checkmark" size={16} color="#2dd4bf" /> : null}
              </Pressable>
            );
          })}
        </View>
      ) : null}
    </View>
  );
}

function SettingsScreen({ connected, onConnected }: { connected: boolean | null; onConnected: () => void }) {
  const [info, setInfo] = useState<LlmInfo | null>(null);
  const [prov, setProv] = useState("");
  const [model, setModel] = useState("");
  const [key, setKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [base, setBase] = useState(API_BASE);
  const [tok, setTok] = useState(API_TOKEN);
  const [showConn, setShowConn] = useState(false);
  const [editing, setEditing] = useState(false);
  // hasil tombol Cek terakhir; berlaku cuma buat kombinasi provider|model|key yang dicek
  const [check, setCheck] = useState<{ sig: string; ok: boolean; text: string } | null>(null);
  const [checking, setChecking] = useState(false);
  const [llmStatus, setLlmStatus] = useState<{ state: "cek" | "ok" | "gagal"; text?: string }>({ state: "cek" });
  const [confirmDel, setConfirmDel] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ text: string; ok?: boolean } | null>(null);
  const [busy, setBusy] = useState(false);
  const [liveModels, setLiveModels] = useState<Record<string, string[]>>({});
  const provRef = useRef(prov);
  provRef.current = prov;

  // daftar model ASLI dari provider (butuh key); model yang udah dipensiunkan otomatis diganti
  const fetchModels = (p: string, apiKey?: string) =>
    getLlmModels({ provider: p, api_key: apiKey })
      .then((r) => {
        if (!r.live) return;
        setLiveModels((m) => ({ ...m, [p]: r.models }));
        if (provRef.current === p) setModel((cur) => (r.models.includes(cur) ? cur : r.models[0]));
      })
      .catch(() => {});

  // cek otak analisa yang lagi dipakai beneran nyambung (1 pesan kecil ke LLM)
  const checkActive = () => {
    setLlmStatus({ state: "cek" });
    testLlm()
      .then((r) => setLlmStatus({ state: r.ok ? "ok" : "gagal", text: r.message.replace(/^GAGAL\s*\S\s*/, "") }))
      .catch((e) => setLlmStatus({ state: "gagal", text: String(e?.message || e) }));
  };

  const loadConfig = (cek = true) =>
    getLlmConfig()
      .then((i) => {
        setInfo(i); setProv(i.provider); setModel(i.model); setBaseUrl(i.base_url);
        provRef.current = i.provider;
        fetchModels(i.provider);
        if (cek) checkActive();
      })
      .catch(() => setInfo(null));

  useEffect(() => { loadConfig(); }, []);

  // koneksi manual (cadangan): simpan alamat + kunci, lalu sambung ulang
  const connect = async () => {
    setBusy(true); setMsg({ text: "Nyambungin…" });
    await saveApiToken(tok);
    if (base.trim()) await saveApiBase(base);
    loadApiBase()
      .then((hit) => {
        if (hit) { setBase(hit); setMsg(null); setShowConn(false); loadConfig(); onConnected(); }
        else setMsg({ text: "Server gak ketemu. Cek alamat & kunci akses.", ok: false });
      })
      .finally(() => setBusy(false));
  };

  const pinfo = info?.providers[prov];
  const label = pinfo?.label || prov;
  const provOpts = info ? Object.entries(info.providers).map(([k, v]) => ({ value: k, label: v.label })) : [];
  const live = liveModels[prov];
  const models = [...(live ?? pinfo?.models ?? [])];
  // model tersimpan di luar daftar bawaan tetap ditampilin — kecuali daftar asli bilang udah gak ada
  if (!live && info && prov === info.provider && info.model && !models.includes(info.model)) models.unshift(info.model);
  const modelOpts = models.map((m) => ({ value: m, label: m }));
  const hasKey = !!info?.keys?.[prov];
  const needKey = prov !== "" && prov !== "ollama";
  const active = !!info && prov === info.provider && model === info.model;   // pilihan = yang lagi dipakai
  const showBar = !!info && (editing || !active);   // bar API key + tombol Cek
  const showSave = showBar;
  const sig = `${prov}|${model.trim()}|${key.trim()}|${prov === "custom" ? baseUrl.trim() : ""}`;
  const chk = check && check.sig === sig ? check : null;   // ganti apa pun -> wajib Cek ulang
  const savedKeys = info ? Object.keys(info.keys || {}).filter((k) => info.keys[k]) : [];

  // ganti provider -> model ikut reset (balik ke provider aktif = model aktifnya)
  const pickProv = (k: string) => {
    setProv(k);
    setModel(k === info?.provider ? info.model : liveModels[k]?.[0] || info?.providers[k]?.models[0] || "");
    setKey("");
    setEditing(false);
    setMsg(null);
    provRef.current = k;
    fetchModels(k);
  };

  const cancel = () => {
    if (info) {
      setProv(info.provider); setModel(info.model);
      provRef.current = info.provider;
    }
    setKey(""); setEditing(false); setMsg(null); setCheck(null);
  };

  const cfg = () => ({
    provider: prov,
    model: model.trim(),
    api_key: key.trim() || undefined,
    base_url: prov === "custom" ? baseUrl.trim() : undefined,
  });

  // tombol Cek: sambungin provider/model/key yang dipilih (belum disimpan)
  const cek = () => {
    if (!model.trim()) return setMsg({ text: "Pilih model dulu.", ok: false });
    if (needKey && !hasKey && !key.trim()) return setMsg({ text: `Tempel API key ${label} dulu.`, ok: false });
    const s = sig;
    setChecking(true); setMsg(null);
    testLlm(cfg())
      .then((r) => {
        setCheck({ sig: s, ok: r.ok, text: r.message.replace(/^(GAGAL|OK)\s*\S\s*/, "") });
        if (r.ok && key.trim()) fetchModels(prov, key.trim());   // key baru valid -> ambil daftar model aslinya
      })
      .catch((e) => setCheck({ sig: s, ok: false, text: String(e?.message || e) }))
      .finally(() => setChecking(false));
  };

  // Simpan cuma boleh setelah Cek nyambung
  const save = async () => {
    if (!chk?.ok) return setMsg({ text: "Klik Cek dulu — pastiin nyambung sebelum disimpan.", ok: false });
    setBusy(true); setMsg(null);
    try {
      await setLlmConfig(cfg());
      setLlmStatus({ state: "ok" });
      setKey("");
      setEditing(false);
      setCheck(null);
      await loadConfig(false);
    } catch (e: any) {
      setMsg({ text: "Gagal simpan: " + String(e?.message || e), ok: false });
    } finally {
      setBusy(false);
    }
  };

  const delKey = (p: string) => {
    setBusy(true);
    deleteLlmKey(p)
      .then(() => { setConfirmDel(null); loadConfig(false); })
      .catch((e) => setMsg({ text: String(e?.message || e), ok: false }))
      .finally(() => setBusy(false));
  };

  // baris status di kolom API key: koneksi aktif / hasil Cek / key tersimpan / belum diisi
  const GREEN = "#22c55e", RED = "#ef4444", AMBER = "#f59e0b", GREY = "#7d8792";
  let rowDot = AMBER;
  let rowText = key.trim() ? `Klik Cek buat nyambungin ${label}` : `API key ${label} belum diisi`;
  if (active && !editing) {
    if (llmStatus.state === "ok") { rowDot = GREEN; rowText = `Tersambung — ${label} / ${model}`; }
    else if (llmStatus.state === "gagal") { rowDot = RED; rowText = `Gagal nyambung — ${llmStatus.text || ""}`; }
    else { rowDot = GREY; rowText = `Ngecek koneksi ${label}…`; }
  } else if (checking) {
    rowDot = GREY; rowText = `Ngecek ${label} / ${model}…`;
  } else if (chk) {
    rowDot = chk.ok ? GREEN : RED;
    rowText = chk.ok ? `Tersambung — ${label} / ${model} · tinggal Simpan` : `Gagal nyambung — ${chk.text}`;
  } else if (!needKey) {
    rowDot = GREY; rowText = `${label} gak butuh API key — klik Cek`;
  } else if (hasKey && !key.trim()) {
    rowDot = GREEN; rowText = `API key ${label} tersimpan${showBar ? " — klik Cek" : ""}`;
  }

  const connColor = connected ? "#22c55e" : connected === null ? "#7d8792" : "#f59e0b";
  const connText = connected ? "Tersambung ke server" : connected === null ? "Nyari server…" : "Belum tersambung";

  return (
    <View style={{ marginTop: 8 }}>
      <Text style={styles.settTitle}>Pengaturan</Text>

      <Text style={styles.settSection}>KONEKSI</Text>
      <View style={styles.connRow}>
        <View style={[styles.jDot, { backgroundColor: connColor }]} />
        <Text style={styles.connText}>{connText}</Text>
        <Pressable onPress={() => setShowConn((s) => !s)} hitSlop={8}>
          <Text style={styles.connLink}>{showConn ? "Tutup" : "Ubah"}</Text>
        </Pressable>
      </View>
      {showConn || connected === false ? (
        <>
          <Text style={styles.settLabel}>Alamat Server</Text>
          <TextInput style={styles.input} value={base} onChangeText={setBase}
            autoCapitalize="none" autoCorrect={false}
            placeholder="https://…" placeholderTextColor="#56606c" />
          <Text style={styles.settLabel}>Kunci Akses</Text>
          <TextInput style={styles.input} value={tok} onChangeText={setTok} secureTextEntry
            autoCapitalize="none" autoCorrect={false}
            placeholder="kunci dari server" placeholderTextColor="#56606c" />
          <Pressable style={({ pressed }) => [styles.actBtn, styles.findBtn, pressed && styles.btnPressed]}
            onPress={connect} disabled={busy}>
            <Ionicons name="link" size={14} color="#2dd4bf" />
            <Text style={[styles.actBtnText, { color: "#2dd4bf" }]}>Sambungkan</Text>
          </Pressable>
        </>
      ) : null}

      <Text style={styles.settSection}>OTAK ANALISA</Text>
      <Dropdown label="Provider" value={prov} options={provOpts} onChange={pickProv}
        placeholder={info ? "Pilih provider" : "Sambungkan server dulu"} disabled={!info} />
      {modelOpts.length > 0 ? (
        <Dropdown label="Model" value={model} options={modelOpts} onChange={setModel}
          placeholder="Pilih model" disabled={!prov} />
      ) : prov ? (
        <>
          <Text style={styles.settLabel}>Model</Text>
          <TextInput style={styles.input} value={model} onChangeText={setModel}
            autoCapitalize="none" autoCorrect={false}
            placeholder="nama model" placeholderTextColor="#56606c" />
        </>
      ) : null}
      {prov === "custom" ? (
        <>
          <Text style={styles.settLabel}>Base URL</Text>
          <TextInput style={styles.input} value={baseUrl} onChangeText={setBaseUrl}
            autoCapitalize="none" autoCorrect={false}
            placeholder="https://…/v1" placeholderTextColor="#56606c" />
        </>
      ) : null}
      {prov ? (
        <>
          <Text style={styles.settLabel}>{needKey ? "API Key" : "Koneksi"}</Text>
          <View style={[styles.connRow, styles.connRowField]}>
            <View style={[styles.jDot, { backgroundColor: rowDot }]} />
            <Text style={styles.connText}>{rowText}</Text>
            {active && !editing ? (
              <Pressable onPress={() => { setEditing(true); setKey(""); setMsg(null); setCheck(null); }} hitSlop={8}>
                <Text style={styles.connLink}>Ubah</Text>
              </Pressable>
            ) : null}
          </View>
          {showBar ? (
            <View style={styles.keyBar}>
              {needKey ? (
                <TextInput style={[styles.input, styles.keyBarInput]} value={key} onChangeText={setKey} secureTextEntry
                  autoCapitalize="none" autoCorrect={false}
                  placeholder={hasKey ? "key baru (kosongin = pakai yang tersimpan)" : `tempel API key ${label}`}
                  placeholderTextColor="#56606c" />
              ) : (
                <View style={styles.flex1} />
              )}
              <Pressable
                style={({ pressed }) => [styles.cekBtn, chk?.ok && styles.cekBtnOk, pressed && styles.btnPressed]}
                onPress={cek}
                disabled={checking || busy}
              >
                {checking ? (
                  <ActivityIndicator size="small" color="#2dd4bf" />
                ) : (
                  <Text style={[styles.cekText, chk?.ok && styles.cekTextOk]}>{chk?.ok ? "Nyambung" : "Cek"}</Text>
                )}
              </Pressable>
            </View>
          ) : null}
        </>
      ) : null}

      {showSave ? (
        <View style={styles.settBtns}>
          <Pressable style={[styles.settBtn, styles.settBtnPri, !chk?.ok && styles.settBtnOff]} onPress={save} disabled={busy || !chk?.ok}>
            <Text style={styles.settBtnPriText}>{busy ? "…" : "Simpan"}</Text>
          </Pressable>
          <Pressable style={[styles.settBtn, styles.settBtnGhost]} onPress={cancel} disabled={busy}>
            <Text style={styles.settBtnGhostText}>Batal</Text>
          </Pressable>
        </View>
      ) : null}
      {msg ? (
        <Text style={[styles.settMsg, msg.ok === true && styles.msgOk, msg.ok === false && styles.msgErr]}>
          {msg.text}
        </Text>
      ) : null}

      {savedKeys.length > 0 ? (
        <>
          <Text style={styles.settSection}>API KEY TERSIMPAN</Text>
          {savedKeys.map((p) => {
            const using = p === info?.provider;
            return (
              <View key={p} style={[styles.connRow, styles.keyRow]}>
                <Ionicons name="key-outline" size={15} color="#7d8792" />
                <Text style={styles.connText}>{info?.providers[p]?.label || p}</Text>
                {using ? (
                  <Text style={styles.keyUsing}>dipakai</Text>
                ) : confirmDel === p ? (
                  <View style={styles.keyConfirm}>
                    <Pressable onPress={() => delKey(p)} disabled={busy} hitSlop={6}>
                      <Text style={styles.keyDel}>Ya, hapus</Text>
                    </Pressable>
                    <Pressable onPress={() => setConfirmDel(null)} hitSlop={6}>
                      <Text style={styles.connLink}>Batal</Text>
                    </Pressable>
                  </View>
                ) : (
                  <Pressable onPress={() => setConfirmDel(p)} hitSlop={6}>
                    <Text style={styles.keyDel}>Hapus</Text>
                  </Pressable>
                )}
              </View>
            );
          })}
        </>
      ) : null}
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
  settSection: { color: "#2dd4bf", fontSize: 11, fontWeight: "800", letterSpacing: 1, marginTop: 24 },
  findBtn: { alignSelf: "flex-start", marginTop: 10, borderColor: "#2dd4bf55" },
  connRow: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 10, backgroundColor: "#121821", borderWidth: 1, borderColor: "#1e2731", borderRadius: 10, paddingHorizontal: 12, paddingVertical: 11 },
  connText: { color: "#e6edf3", fontSize: 14, fontWeight: "600", flex: 1 },
  connLink: { color: "#2dd4bf", fontSize: 13, fontWeight: "700" },
  connRowField: { marginTop: 0 },
  keyBar: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 8 },
  keyBarInput: { flex: 1, minWidth: 0 },
  cekBtn: { minWidth: 76, alignSelf: "stretch", alignItems: "center", justifyContent: "center", paddingHorizontal: 14, borderRadius: 10, borderWidth: 1, borderColor: "#2dd4bf55", backgroundColor: "rgba(45,212,191,0.10)" },
  cekBtnOk: { borderColor: "#22c55e88", backgroundColor: "rgba(34,197,94,0.12)" },
  cekText: { color: "#2dd4bf", fontSize: 14, fontWeight: "800" },
  cekTextOk: { color: "#22c55e" },
  settBtnOff: { opacity: 0.35 },
  keyRow: { marginTop: 8 },
  keyUsing: { color: "#7d8792", fontSize: 12, fontWeight: "700", borderWidth: 1, borderColor: "#1e2731", borderRadius: 999, paddingHorizontal: 9, paddingVertical: 2 },
  keyDel: { color: "#ef4444", fontSize: 13, fontWeight: "700" },
  keyConfirm: { flexDirection: "row", alignItems: "center", gap: 14 },
  msgOk: { color: "#22c55e" },
  msgErr: { color: "#fca5a5" },

  // Dropdown
  ddBox: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8 },
  ddBoxOpen: { borderColor: "#2dd4bf" },
  ddDisabled: { opacity: 0.5 },
  ddText: { color: "#e6edf3", fontSize: 14, flex: 1 },
  ddPlaceholder: { color: "#56606c" },
  ddList: { marginTop: 6, backgroundColor: "#0e141b", borderWidth: 1, borderColor: "#1e2731", borderRadius: 10, overflow: "hidden" },
  ddItem: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 12, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: "#161d26" },
  ddItemOn: { backgroundColor: "rgba(45,212,191,0.08)" },
  ddItemText: { color: "#c2cbd4", fontSize: 14 },
  ddItemTextOn: { color: "#2dd4bf", fontWeight: "700" },

  // Kartu "server di PC belum nyala"
  offCard: { backgroundColor: "rgba(245,158,11,0.08)", borderRadius: 14, padding: 14, marginTop: 12, borderWidth: 1, borderColor: "rgba(245,158,11,0.35)" },
  offHead: { flexDirection: "row", alignItems: "center", gap: 8 },
  offTitle: { color: "#fbbf24", fontSize: 14, fontWeight: "800" },
  offDesc: { color: "#c2cbd4", fontSize: 13, lineHeight: 19, marginTop: 6 },
  offCode: { color: "#e6edf3", fontWeight: "800" },
  offBtn: { flexDirection: "row", alignItems: "center", gap: 6, alignSelf: "flex-start", marginTop: 10, borderWidth: 1, borderColor: "rgba(245,158,11,0.5)", borderRadius: 9, paddingHorizontal: 12, paddingVertical: 7 },
  offBtnText: { color: "#f59e0b", fontSize: 12, fontWeight: "800" },
  settLabel: { color: "#8b95a1", fontSize: 11, fontWeight: "700", letterSpacing: 0.5, marginTop: 16, marginBottom: 6 },
  input: { backgroundColor: "#121821", borderWidth: 1, borderColor: "#1e2731", borderRadius: 10, paddingHorizontal: 12, paddingVertical: 11, color: "#e6edf3", fontSize: 14 },
  hint: { color: "#56606c", fontSize: 11, marginTop: 5 },
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
  macroHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 8 },
  macroLabel: { color: "#2dd4bf", fontSize: 11, fontWeight: "800", letterSpacing: 1 },
  macroText: { color: "#c2cbd4", fontSize: 13, lineHeight: 19 },
  macroStrip: { marginTop: 12, marginHorizontal: -2 },
  macroStripInner: { gap: 8, paddingHorizontal: 2 },
  macroTile: { backgroundColor: "#0e141b", borderRadius: 10, borderWidth: 1, borderColor: "#1e2731", paddingHorizontal: 11, paddingVertical: 8, minWidth: 82 },
  macroTileLabel: { color: "#7d8792", fontSize: 10, fontWeight: "700", letterSpacing: 0.3 },
  macroTileVal: { color: "#e6edf3", fontSize: 15, fontWeight: "800", marginTop: 3 },
  macroTileChg: { fontSize: 11, fontWeight: "700", marginTop: 2 },

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

  // ---- Jurnal ----
  jSum: { backgroundColor: "#121821", borderRadius: 14, padding: 14, marginTop: 14, borderWidth: 1, borderColor: "#1e2731" },
  jSumLabel: { color: "#7d8792", fontSize: 11, fontWeight: "800", letterSpacing: 1 },
  jSumTotal: { fontSize: 26, fontWeight: "800", marginTop: 4 },
  jPct: { fontSize: 17, fontWeight: "800" },
  jPlRow: { flexDirection: "row", alignItems: "baseline", gap: 8, marginTop: 12 },
  jPlLabel: { color: "#7d8792", fontSize: 11, fontWeight: "700", letterSpacing: 0.5 },
  jPlVal: { fontSize: 16, fontWeight: "800" },
  jNet: { color: "#7d8792", fontSize: 11 },
  jDot: { width: 7, height: 7, borderRadius: 4 },
  jStatus: { fontSize: 12, fontWeight: "700", flex: 1 },
  jThesis: { color: "#8b95a1", fontSize: 12, marginTop: 8, fontStyle: "italic" },
  jActions: { flexDirection: "row", alignItems: "center", marginTop: 12, paddingTop: 10, borderTopWidth: 1, borderTopColor: "#1e2731" },
  actBtn: { flexDirection: "row", alignItems: "center", gap: 6, borderWidth: 1, borderColor: "#1e2731", backgroundColor: "#0e141b", borderRadius: 9, paddingHorizontal: 11, paddingVertical: 7 },
  actBtnDanger: { borderColor: "rgba(239,68,68,0.35)" },
  actBtnText: { fontSize: 12, fontWeight: "700" },
  jInline: { marginTop: 12, paddingTop: 10, borderTopWidth: 1, borderTopColor: "#1e2731" },
  jConfirm: { color: "#fca5a5", fontSize: 13, lineHeight: 19, flex: 1 },
  jPreview: { fontSize: 13, fontWeight: "700", marginTop: 8 },
  jBtns: { flexDirection: "row", gap: 10, marginTop: 14 },
  jBtnDanger: { backgroundColor: "#ef4444" },
  jBtnDangerText: { color: "#fff", fontSize: 14, fontWeight: "800", letterSpacing: 0.5 },
  formCard: { backgroundColor: "#121821", borderRadius: 14, padding: 14, marginTop: 16, borderWidth: 1, borderColor: "#2dd4bf55" },
  formTitle: { color: "#e6edf3", fontSize: 17, fontWeight: "800", marginBottom: 10 },
  formRow: { flexDirection: "row", gap: 8 },
  field: { flex: 1, minWidth: 0, marginTop: 10 },
  fieldLabel: { color: "#8b95a1", fontSize: 11, fontWeight: "700", letterSpacing: 0.3, marginBottom: 6 },
  fieldInput: { width: "100%", paddingHorizontal: 10 },
  formErr: { color: "#fca5a5", fontSize: 13, marginTop: 10 },

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
