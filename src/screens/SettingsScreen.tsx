import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import Ionicons from "@expo/vector-icons/Ionicons";
import {
  API_BASE, API_TOKEN, deleteLlmKey, errMsg, getLlmConfig, getLlmModels, getLlmStatus, LlmInfo,
  loadApiBase, saveApiBase, saveApiToken, setLlmConfig, testLlm,
} from "../api";
import { Dropdown } from "../components/Dropdown";
import { fmtInt } from "../format";
import { C } from "../theme";
import { ui } from "../ui";

type LlmStatusView = { state: "cek" | "ok" | "gagal" | "tau"; text?: string; saldo?: number | null; tipis?: boolean };

// Tab Pengaturan: koneksi ke server + otak analisa (provider/model LLM + API key per provider).
// Alur ganti otak: pilih provider & model -> (tempel key) -> Cek (LLM beneran dites) -> Simpan.
export function SettingsScreen({ connected, onConnected }: { connected: boolean | null; onConnected: () => void }) {
  const [info, setInfo] = useState<LlmInfo | null>(null);
  const [prov, setProv] = useState("");
  const [model, setModel] = useState("");
  const [key, setKey] = useState("");
  const [base, setBase] = useState(API_BASE);
  const [tok, setTok] = useState(API_TOKEN);
  const [showConn, setShowConn] = useState(false);
  const [editing, setEditing] = useState(false);
  // hasil tombol Cek terakhir; berlaku cuma buat kombinasi provider|model|key yang dicek
  const [check, setCheck] = useState<{ sig: string; ok: boolean; text: string } | null>(null);
  const [checking, setChecking] = useState(false);
  const [llmStatus, setLlmStatus] = useState<LlmStatusView>({ state: "cek" });
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

  // status otak aktif: GRATIS (server cuma cek key ke provider, gak nyuruh LLM nulis -> 0 token)
  const checkActive = () => {
    setLlmStatus({ state: "cek" });
    getLlmStatus()
      .then((s) =>
        setLlmStatus(
          s.ok === true
            ? { state: "ok", saldo: s.balance_rp, tipis: s.balance_usd != null && s.balance_usd < 0.2 }
            : s.ok === false
            ? { state: "gagal", text: "API key ditolak — ketuk Ubah buat ganti" }
            : { state: "tau" },
        ),
      )
      .catch(() => setLlmStatus({ state: "tau" })); // jaringan / server lama: jangan dibilang gagal
  };

  const loadConfig = (cek = true) =>
    getLlmConfig()
      .then((i) => {
        setInfo(i); setProv(i.provider); setModel(i.model);
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
  const active = !!info && prov === info.provider && model === info.model; // pilihan = yang lagi dipakai
  const showBar = !!info && (editing || !active); // kolom API key + tombol Cek + Simpan/Batal
  const sig = `${prov}|${model.trim()}|${key.trim()}`;
  const chk = check && check.sig === sig ? check : null; // ganti apa pun -> wajib Cek ulang
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

  const cfg = () => ({ provider: prov, model: model.trim(), api_key: key.trim() || undefined });

  // tombol Cek: tes provider/model/key yang dipilih (belum disimpan)
  const cek = () => {
    if (!model.trim()) return setMsg({ text: "Pilih model dulu.", ok: false });
    if (prov && !hasKey && !key.trim()) return setMsg({ text: `Tempel API key ${label} dulu.`, ok: false });
    const s = sig;
    setChecking(true); setMsg(null);
    testLlm(cfg())
      .then((r) => {
        setCheck({ sig: s, ok: r.ok, text: r.message.replace(/^(GAGAL|OK)\s*\S\s*/, "") });
        if (r.ok && key.trim()) fetchModels(prov, key.trim()); // key baru valid -> ambil daftar model aslinya
      })
      .catch((e) => setCheck({ sig: s, ok: false, text: errMsg(e) }))
      .finally(() => setChecking(false));
  };

  // Simpan cuma boleh setelah Cek nyambung
  const save = async () => {
    if (!chk?.ok) return setMsg({ text: "Klik Cek dulu — pastiin nyambung sebelum disimpan.", ok: false });
    setBusy(true); setMsg(null);
    try {
      await setLlmConfig(cfg());
      setKey("");
      setEditing(false);
      setCheck(null);
      await loadConfig(true); // status + saldo (gratis)
    } catch (e) {
      setMsg({ text: "Gagal simpan: " + errMsg(e), ok: false });
    } finally {
      setBusy(false);
    }
  };

  const delKey = (p: string) => {
    setBusy(true);
    deleteLlmKey(p)
      .then(() => { setConfirmDel(null); loadConfig(false); })
      .catch((e) => setMsg({ text: errMsg(e), ok: false }))
      .finally(() => setBusy(false));
  };

  // baris status di kolom API key: koneksi aktif / hasil Cek / key tersimpan / belum diisi
  let rowDot = C.warn;
  let rowText = key.trim() ? `Klik Cek buat nyambungin ${label}` : `API key ${label} belum diisi`;
  if (active && !editing) {
    if (llmStatus.state === "ok") {
      rowDot = llmStatus.tipis ? C.warn : C.up;
      rowText = `Tersambung — ${label} / ${model}`;
      if (llmStatus.saldo != null) {
        rowText += llmStatus.tipis
          ? ` · saldo tinggal ±Rp${fmtInt(llmStatus.saldo)}, top up`
          : ` · saldo ±Rp${fmtInt(llmStatus.saldo)}`;
      }
    } else if (llmStatus.state === "gagal") { rowDot = C.down; rowText = llmStatus.text || "API key ditolak"; }
    else if (llmStatus.state === "tau") { rowDot = C.up; rowText = `API key ${label} tersimpan`; }
    else { rowDot = C.muted; rowText = `Ngecek koneksi ${label}…`; }
  } else if (checking) {
    rowDot = C.muted; rowText = `Ngecek ${label} / ${model}…`;
  } else if (chk) {
    rowDot = chk.ok ? C.up : C.down;
    rowText = chk.ok ? `Tersambung — ${label} / ${model} · tinggal Simpan` : `Gagal nyambung — ${chk.text}`;
  } else if (hasKey && !key.trim()) {
    rowDot = C.up; rowText = `API key ${label} tersimpan${showBar ? " — klik Cek" : ""}`;
  }

  const connColor = connected ? C.up : connected === null ? C.muted : C.warn;
  const connText = connected ? "Tersambung ke server" : connected === null ? "Nyari server…" : "Belum tersambung";

  return (
    <View style={styles.root}>
      <Text style={styles.title}>Pengaturan</Text>

      <Text style={styles.section}>KONEKSI</Text>
      <View style={styles.row}>
        <View style={[ui.dot, { backgroundColor: connColor }]} />
        <Text style={styles.rowText}>{connText}</Text>
        <Pressable onPress={() => setShowConn((s) => !s)} hitSlop={8}>
          <Text style={styles.link}>{showConn ? "Tutup" : "Ubah"}</Text>
        </Pressable>
      </View>
      {showConn || connected === false ? (
        <>
          <Text style={ui.inputLabel}>Alamat Server</Text>
          <TextInput style={ui.input} value={base} onChangeText={setBase}
            autoCapitalize="none" autoCorrect={false}
            placeholder="https://…" placeholderTextColor={C.dim} />
          <Text style={ui.inputLabel}>Kunci Akses</Text>
          <TextInput style={ui.input} value={tok} onChangeText={setTok} secureTextEntry
            autoCapitalize="none" autoCorrect={false}
            placeholder="kunci dari server" placeholderTextColor={C.dim} />
          <Pressable style={({ pressed }) => [ui.actBtn, styles.connectBtn, pressed && ui.pressed]}
            onPress={connect} disabled={busy}>
            <Ionicons name="link" size={14} color={C.accent} />
            <Text style={[ui.actBtnText, { color: C.accent }]}>Sambungkan</Text>
          </Pressable>
        </>
      ) : null}

      <Text style={styles.section}>OTAK ANALISA</Text>
      <Dropdown label="Provider" value={prov} options={provOpts} onChange={pickProv}
        placeholder={info ? "Pilih provider" : "Sambungkan server dulu"} disabled={!info} />
      {modelOpts.length > 0 ? (
        <Dropdown label="Model" value={model} options={modelOpts} onChange={setModel}
          placeholder="Pilih model" disabled={!prov} />
      ) : prov ? (
        <>
          <Text style={ui.inputLabel}>Model</Text>
          <TextInput style={ui.input} value={model} onChangeText={setModel}
            autoCapitalize="none" autoCorrect={false}
            placeholder="nama model" placeholderTextColor={C.dim} />
        </>
      ) : null}
      {prov ? (
        <>
          <Text style={ui.inputLabel}>API Key</Text>
          <View style={[styles.row, styles.rowField]}>
            <View style={[ui.dot, { backgroundColor: rowDot }]} />
            <Text style={styles.rowText}>{rowText}</Text>
            {active && !editing ? (
              <Pressable onPress={() => { setEditing(true); setKey(""); setMsg(null); setCheck(null); }} hitSlop={8}>
                <Text style={styles.link}>Ubah</Text>
              </Pressable>
            ) : null}
          </View>
          {showBar ? (
            <View style={ui.inputRow}>
              <TextInput style={[ui.input, ui.inputFlex]} value={key} onChangeText={setKey} secureTextEntry
                autoCapitalize="none" autoCorrect={false}
                placeholder={hasKey ? "key baru (kosongin = pakai yang tersimpan)" : `tempel API key ${label}`}
                placeholderTextColor={C.dim} />
              <Pressable
                style={({ pressed }) => [ui.sideBtn, chk?.ok && styles.cekOk, pressed && ui.pressed]}
                onPress={cek}
                disabled={checking || busy}
              >
                {checking ? (
                  <ActivityIndicator size="small" color={C.accent} />
                ) : (
                  <Text style={[ui.sideBtnText, chk?.ok && styles.cekOkText]}>{chk?.ok ? "Nyambung" : "Cek"}</Text>
                )}
              </Pressable>
            </View>
          ) : null}
        </>
      ) : null}

      {showBar ? (
        <View style={styles.saveRow}>
          <Pressable style={[ui.btn, ui.btnPri, !chk?.ok && styles.off]} onPress={save} disabled={busy || !chk?.ok}>
            <Text style={ui.btnPriText}>{busy ? "…" : "Simpan"}</Text>
          </Pressable>
          <Pressable style={[ui.btn, ui.btnGhost]} onPress={cancel} disabled={busy}>
            <Text style={ui.btnGhostText}>Batal</Text>
          </Pressable>
        </View>
      ) : null}
      {msg ? (
        <Text style={[styles.msg, msg.ok === true && styles.msgOk, msg.ok === false && styles.msgErr]}>
          {msg.text}
        </Text>
      ) : null}

      {savedKeys.length > 0 ? (
        <>
          <Text style={styles.section}>API KEY TERSIMPAN</Text>
          {savedKeys.map((p) => (
            <View key={p} style={[styles.row, styles.keyRow]}>
              <Ionicons name="key-outline" size={15} color={C.muted} />
              <Text style={styles.rowText}>{info?.providers[p]?.label || p}</Text>
              {p === info?.provider ? (
                <Text style={styles.keyUsing}>dipakai</Text>
              ) : confirmDel === p ? (
                <View style={styles.keyConfirm}>
                  <Pressable onPress={() => delKey(p)} disabled={busy} hitSlop={6}>
                    <Text style={styles.keyDel}>Ya, hapus</Text>
                  </Pressable>
                  <Pressable onPress={() => setConfirmDel(null)} hitSlop={6}>
                    <Text style={styles.link}>Batal</Text>
                  </Pressable>
                </View>
              ) : (
                <Pressable onPress={() => setConfirmDel(p)} hitSlop={6}>
                  <Text style={styles.keyDel}>Hapus</Text>
                </Pressable>
              )}
            </View>
          ))}
        </>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { marginTop: 8 },
  title: { color: C.text, fontSize: 20, fontWeight: "800" },
  section: { color: C.accent, fontSize: 11, fontWeight: "800", letterSpacing: 1, marginTop: 24 },
  // baris status: titik warna + teks + link (Ubah / Tutup)
  row: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 10, backgroundColor: C.card, borderWidth: 1, borderColor: C.border, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 11 },
  rowField: { marginTop: 0 },
  rowText: { color: C.text, fontSize: 14, fontWeight: "600", flex: 1 },
  link: { color: C.accent, fontSize: 13, fontWeight: "700" },
  connectBtn: { alignSelf: "flex-start", marginTop: 10, borderColor: C.accent + "55" },
  cekOk: { borderColor: C.up + "88", backgroundColor: "rgba(34,197,94,0.12)" },
  cekOkText: { color: C.up },
  saveRow: { flexDirection: "row", gap: 10, marginTop: 20 },
  off: { opacity: 0.35 },
  msg: { color: C.textSoft, fontSize: 13, marginTop: 14, lineHeight: 19 },
  msgOk: { color: C.up },
  msgErr: { color: C.errText },
  keyRow: { marginTop: 8 },
  keyUsing: { color: C.muted, fontSize: 12, fontWeight: "700", borderWidth: 1, borderColor: C.border, borderRadius: 999, paddingHorizontal: 9, paddingVertical: 2 },
  keyDel: { color: C.down, fontSize: 13, fontWeight: "700" },
  keyConfirm: { flexDirection: "row", alignItems: "center", gap: 14 },
});
