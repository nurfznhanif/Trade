// App HP Trade IDX: header + layar aktif + menu bawah. Data diambil dari server (lihat api.ts).
import { useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text } from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { Analysis, Group, sampleAnalysis } from "./analysis";
import { errMsg, getAnalysis, getMacro, loadApiBase, MacroItem } from "./api";
import { BottomNav, Nav } from "./components/BottomNav";
import { OfflineCard } from "./components/Feedback";
import { fmtWaktu } from "./format";
import { AnalysisScreen } from "./screens/analysis/AnalysisScreen";
import { JournalScreen } from "./screens/journal/JournalScreen";
import { NewsScreen } from "./screens/NewsScreen";
import { RaporScreen } from "./screens/RaporScreen";
import { SettingsScreen } from "./screens/SettingsScreen";
import { C } from "./theme";
import { ui } from "./ui";

export default function App() {
  const [nav, setNav] = useState<Nav>("analisa");
  const [tab, setTab] = useState<Group>("beli"); // filter Beli/Tunggu/Hindari (diinget pas pindah menu)
  const [data, setData] = useState<Analysis>(sampleAnalysis); // data contoh sampai server ketemu
  const [live, setLive] = useState(false);
  const [note, setNote] = useState("");
  const [macro, setMacro] = useState<MacroItem[]>([]);
  const [conn, setConn] = useState<"cari" | "ok" | "mati">("cari");

  // ambil analisa + angka makro dari server
  const loadLive = (showErr = true) => {
    getAnalysis()
      .then((a) => { setData(a); setLive(true); setNote(""); })
      .catch((e) => { setLive(false); setNote(showErr ? "Gagal ambil analisa: " + errMsg(e) : ""); });
    getMacro()
      .then((m) => setMacro(m.items))
      .catch(() => setMacro([]));
  };

  // cari server otomatis (gak perlu isi alamat), terus muat data
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

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
        <StatusBar style="light" />
        <ScrollView style={ui.flex1} contentContainerStyle={styles.scroll}>
          <Text style={styles.logo}>
            TRADE <Text style={styles.logoAccent}>IDX</Text>
          </Text>
          <Text style={styles.sub}>{fmtWaktu(data.generated_at, data.generated)}</Text>
          {conn === "cari" ? <Text style={styles.sub}>Nyari server…</Text> : null}
          {conn === "mati" ? <OfflineCard onRetry={connect} /> : null}
          {note ? <Text style={ui.note}>{note}</Text> : null}

          {nav === "analisa" && <AnalysisScreen data={data} live={live} macro={macro} tab={tab} onTab={setTab} />}
          {nav === "jurnal" && <JournalScreen data={data} />}
          {nav === "rapor" && <RaporScreen />}
          {nav === "berita" && <NewsScreen />}
          {nav === "pengaturan" && (
            <SettingsScreen connected={conn === "cari" ? null : conn === "ok" && live} onConnected={connect} />
          )}
        </ScrollView>
        <BottomNav nav={nav} setNav={setNav} />
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.bg },
  scroll: { padding: 16, paddingBottom: 32 },
  logo: { color: C.text, fontSize: 26, fontWeight: "800", letterSpacing: 1 },
  logoAccent: { color: C.accent },
  sub: { color: C.muted, fontSize: 12, marginTop: 4 },
});
