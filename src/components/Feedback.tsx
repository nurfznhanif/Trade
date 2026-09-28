// Tampilan status: lagi ngambil data, gagal ambil data, server gak ketemu.
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";
import { C } from "../theme";
import { ui } from "../ui";

export function Loading() {
  return (
    <View style={styles.center}>
      <ActivityIndicator color={C.accent} />
      <Text style={styles.centerText}>Ngambil data…</Text>
    </View>
  );
}

export function ErrBox({ msg }: { msg: string }) {
  return (
    <View style={ui.empty}>
      <Ionicons name="cloud-offline-outline" size={40} color={C.dim} />
      <Text style={ui.emptyTitle}>Server belum nyambung</Text>
      <Text style={ui.emptyDesc}>{msg || "Gagal ambil data."}</Text>
      <Text style={ui.emptyDesc}>
        {/kunci akses/i.test(msg) ? "Isi Kunci Akses di menu Pengaturan, bagian Koneksi." : "Cek internet HP, lalu buka lagi menu ini."}
      </Text>
    </View>
  );
}

// kartu di atas layar pas server gak ketemu — jelasin langkahnya + tombol coba lagi
export function OfflineCard({ onRetry }: { onRetry: () => void }) {
  return (
    <View style={styles.offCard}>
      <View style={styles.offHead}>
        <Ionicons name="cloud-offline-outline" size={17} color={C.warn} />
        <Text style={styles.offTitle}>Server belum nyambung</Text>
      </View>
      <Text style={styles.offDesc}>
        Cek internet HP, lalu ketuk Sambung ulang.
      </Text>
      <Pressable style={({ pressed }) => [styles.offBtn, pressed && ui.pressed]} onPress={onRetry}>
        <Ionicons name="refresh" size={15} color={C.warn} />
        <Text style={styles.offBtnText}>Sambung ulang</Text>
      </Pressable>
    </View>
  );
}

// server ketemu tapi nolak: kunci akses belum diisi di perangkat ini (tiap HP / browser nyimpen sendiri)
export function LockedCard({ onOpen }: { onOpen: () => void }) {
  return (
    <View style={styles.offCard}>
      <View style={styles.offHead}>
        <Ionicons name="key-outline" size={17} color={C.warn} />
        <Text style={styles.offTitle}>Kunci akses belum diisi</Text>
      </View>
      <Text style={styles.offDesc}>
        Server udah ketemu, tapi butuh kunci akses. Tiap HP atau browser nyimpen kuncinya sendiri, jadi isi sekali
        di perangkat ini.
      </Text>
      <Pressable style={({ pressed }) => [styles.offBtn, pressed && ui.pressed]} onPress={onOpen}>
        <Ionicons name="settings-outline" size={15} color={C.warn} />
        <Text style={styles.offBtnText}>Isi Kunci Akses</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { alignItems: "center", justifyContent: "center", paddingVertical: 56, gap: 10 },
  centerText: { color: C.muted, fontSize: 13 },
  offCard: { backgroundColor: "rgba(245,158,11,0.08)", borderRadius: 14, padding: 14, marginTop: 12, borderWidth: 1, borderColor: "rgba(245,158,11,0.35)" },
  offHead: { flexDirection: "row", alignItems: "center", gap: 8 },
  offTitle: { color: C.warnText, fontSize: 14, fontWeight: "800" },
  offDesc: { color: C.textSoft, fontSize: 13, lineHeight: 19, marginTop: 6 },
  offBtn: { flexDirection: "row", alignItems: "center", gap: 6, alignSelf: "flex-start", marginTop: 10, borderWidth: 1, borderColor: "rgba(245,158,11,0.5)", borderRadius: 9, paddingHorizontal: 12, paddingVertical: 7 },
  offBtnText: { color: C.warn, fontSize: 12, fontWeight: "800" },
});
