import { Linking, Pressable, StyleSheet, Text, View } from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";
import { sentColor } from "../analysis";
import { getNews, Mover, NewsItem } from "../api";
import { ErrBox, Loading } from "../components/Feedback";
import { code, fmtAgo } from "../format";
import { C } from "../theme";
import { ui } from "../ui";
import { useAsync } from "../useAsync";

// Tab Berita: saham paling positif/negatif 14 hari + daftar berita terbaru (titik warna = sentimen)
export function NewsScreen() {
  const { loading, data, err } = useAsync(() => getNews(40), []);
  if (loading) return <Loading />;
  if (err || !data) return <ErrBox msg={err} />;
  return (
    <>
      <View style={ui.secHead}>
        <Text style={[ui.sectionTitle, ui.secHeadTitle]}>SENTIMEN BERITA</Text>
        <Text style={styles.secSub}>Skor Berita 14 hari terakhir</Text>
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
  const col = pos ? C.up : C.down;
  return (
    <View style={styles.moverRow}>
      <Text style={styles.moverLabel}>{label}</Text>
      <View style={styles.chips}>
        {movers.map((m) => (
          <View key={m.ticker} style={[styles.chip, { borderColor: col + "55" }]}>
            <Text style={[styles.chipTicker, { color: col }]}>{code(m.ticker)}</Text>
            <Text style={styles.chipAvg}>{(m.avg >= 0 ? "+" : "") + m.avg.toFixed(2)}</Text>
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
    <Pressable style={styles.card} onPress={open} disabled={!n.link}>
      <View style={[styles.sentDot, { backgroundColor: col }]} />
      <View style={ui.flex1}>
        <Text style={styles.title} numberOfLines={2}>
          {n.title}
        </Text>
        <View style={styles.meta}>
          <Text style={[styles.ticker, { color: col }]}>{code(n.ticker)}</Text>
          <Text style={styles.metaDot}>·</Text>
          <Text style={styles.metaText}>{n.source || "?"}</Text>
          <Text style={styles.metaDot}>·</Text>
          <Text style={styles.metaText}>{fmtAgo(n.published)}</Text>
        </View>
      </View>
      {n.link ? <Ionicons name="open-outline" size={15} color={C.dim} /> : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  secSub: { color: C.muted, fontSize: 12, marginTop: 2 },
  moverBox: { backgroundColor: C.card, borderRadius: 14, padding: 12, marginTop: 14, borderWidth: 1, borderColor: C.border, gap: 10 },
  moverRow: { gap: 6 },
  moverLabel: { color: C.muted, fontSize: 11, fontWeight: "700", letterSpacing: 0.5 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  chip: { flexDirection: "row", alignItems: "center", gap: 5, borderWidth: 1, borderRadius: 8, paddingHorizontal: 8, paddingVertical: 4 },
  chipTicker: { fontSize: 12, fontWeight: "800" },
  chipAvg: { color: C.muted, fontSize: 11, fontWeight: "700" },
  card: { flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: C.card, borderRadius: 12, padding: 12, marginTop: 10, borderWidth: 1, borderColor: C.border },
  sentDot: { width: 9, height: 9, borderRadius: 5 },
  title: { color: C.text, fontSize: 13, fontWeight: "600", lineHeight: 18 },
  meta: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 5 },
  ticker: { fontSize: 11, fontWeight: "800" },
  metaDot: { color: C.faint, fontSize: 11 },
  metaText: { color: C.muted, fontSize: 11 },
});
