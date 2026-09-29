import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";
import { actionColor, Call, flagColor, group, pct, rr } from "../../analysis";
import { getPrices } from "../../api";
import { Level } from "../../components/Level";
import { MiniChart } from "../../components/MiniChart";
import { code, fmtInt } from "../../format";
import { C } from "../../theme";
import { ui } from "../../ui";
import { useAsync } from "../../useAsync";

// kartu 1 saran saham: aksi + level Entry/Target/Stop + chart (khusus BELI) + alasan dari berita
export function CallCard({ c, held }: { c: Call; held?: boolean }) {
  const col = actionColor(c.action);
  const toTarget = pct(c.entry, c.target);
  const toStop = pct(c.entry, c.stop);
  const ratio = rr(c);
  const lotRp = c.lot && c.entry ? c.lot * 100 * c.entry : null;

  return (
    <View style={[ui.card, { borderLeftColor: c.flag ? flagColor[c.flag] : col }]}>
      <View style={ui.cardTop}>
        <Text style={ui.ticker}>{code(c.ticker)}</Text>
        <View style={[ui.badge, { backgroundColor: col + "22", borderColor: col }]}>
          <Text style={[ui.badgeText, { color: col }]}>{c.action}</Text>
        </View>
      </View>
      {c.conviction && c.conviction !== "-" ? <Text style={ui.subline}>Konviksi: {c.conviction}</Text> : null}
      {held ? (
        <View style={ui.iconRow}>
          <Ionicons name="briefcase-outline" size={14} color={C.info} />
          <Text style={styles.held}>Udah dipegang — gak perlu beli lagi, lihat saran TAHAN/JUAL di Jurnal</Text>
        </View>
      ) : null}

      {c.entry != null ? (
        <View style={ui.levels}>
          <Level label="Entry" val={fmtInt(c.entry)} />
          <Level label="Target" val={fmtInt(c.target)} sub={toTarget ? `+${toTarget}%` : undefined} subColor={C.up} />
          <Level label="Stop" val={fmtInt(c.stop)} sub={toStop ? `${toStop}%` : undefined} subColor={C.down} />
          {ratio ? <Level label="R:R" val={`1:${ratio}`} /> : null}
        </View>
      ) : null}

      {/* chart cuma buat saham saran BELI */}
      {group(c.action) === "beli" && c.entry != null ? <CallChart c={c} /> : null}

      {c.lot ? (
        <View style={ui.iconRow}>
          <Ionicons name="cube-outline" size={14} color={C.accent} />
          <Text style={styles.lot}>
            {c.lot} lot{lotRp ? ` · ~Rp${fmtInt(lotRp)}` : ""}
          </Text>
        </View>
      ) : null}

      <Text style={ui.reason}>{c.reason}</Text>
    </View>
  );
}

// chart 60 hari + garis Target / Entry / Stop dari analisa
function CallChart({ c }: { c: Call }) {
  const { loading, data: px, err } = useAsync(() => getPrices(c.ticker, 60), [c.ticker]);
  if (loading) {
    return (
      <View style={[ui.chartBox, styles.loading]}>
        <ActivityIndicator size="small" color={C.accent} />
      </View>
    );
  }
  if (err || !px || px.series.length < 2) return null;
  const chg = px.chg_pct ?? 0;
  return (
    <View>
      <MiniChart
        series={px.series}
        lines={[
          { v: c.target, color: C.up, label: "Target" },
          { v: c.entry, color: C.info, label: "Entry" },
          { v: c.stop, color: C.down, label: "Stop" },
        ]}
      />
      <Text style={styles.caption}>
        {px.days} hari · terakhir Rp{fmtInt(px.last)}{" "}
        <Text style={{ color: chg >= 0 ? C.up : C.down }}>
          {chg >= 0 ? "+" : ""}
          {chg}%
        </Text>
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  lot: { color: C.accent, fontSize: 13, fontWeight: "700" },
  held: { color: C.info, fontSize: 12, fontWeight: "700", flex: 1 },
  loading: { height: 120, alignItems: "center", justifyContent: "center" },
  caption: { color: C.muted, fontSize: 11, marginTop: 6 },
});
