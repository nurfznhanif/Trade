import { StyleSheet, Text, View } from "react-native";
import { Bar } from "../api";
import { fmtInt } from "../format";
import { C } from "../theme";
import { ui } from "../ui";

export type ChartLine = { v: number | null | undefined; color: string; label: string };

// chart harga ringkas: batang high-low per hari (hijau naik / merah turun) + garis level (Target/Entry/Stop)
export function MiniChart({ series, lines, H = 120 }: { series: Bar[]; lines: ChartLine[]; H?: number }) {
  let lo = Math.min(...series.map((b) => b.low));
  let hi = Math.max(...series.map((b) => b.high));
  lines.forEach((l) => {
    if (l.v != null) {
      lo = Math.min(lo, l.v);
      hi = Math.max(hi, l.v);
    }
  });
  const pad = (hi - lo) * 0.06 || 1; // biar garis & label gak nempel tepi
  lo -= pad;
  hi += pad;
  const y = (v: number) => H - ((v - lo) / (hi - lo)) * H;
  return (
    <View style={[ui.chartBox, { height: H }]}>
      <View style={styles.bars}>
        {series.map((b, i) => (
          <View key={i} style={styles.cell}>
            <View
              style={{
                marginTop: y(b.high),
                height: Math.max(1.5, y(b.low) - y(b.high)),
                width: 2.2,
                borderRadius: 1.5,
                backgroundColor: b.close >= b.open ? C.up : C.down,
                opacity: 0.85,
              }}
            />
          </View>
        ))}
      </View>
      {lines.map((l) =>
        l.v != null ? <RefLine key={l.label} y={y(l.v)} color={l.color} label={`${l.label} ${fmtInt(l.v)}`} /> : null,
      )}
    </View>
  );
}

function RefLine({ y, color, label }: { y: number; color: string; label: string }) {
  return (
    <View style={[styles.refLine, { top: y }]}>
      <View style={[styles.refDash, { borderColor: color }]} />
      <Text style={[styles.refLabel, { color }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  bars: { flexDirection: "row", height: "100%", alignItems: "flex-start" },
  cell: { flex: 1, alignItems: "center" },
  refLine: { position: "absolute", left: 0, right: 0, flexDirection: "row", alignItems: "center", pointerEvents: "none" },
  refDash: { flex: 1, borderTopWidth: 1, borderStyle: "dashed", height: 0, opacity: 0.55 },
  refLabel: { fontSize: 9, fontWeight: "800", marginLeft: 4, marginRight: 4 },
});
