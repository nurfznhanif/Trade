import { useEffect, useState } from "react";
import { errMsg } from "./api";

// Ambil data sekali pas komponen muncul (atau pas deps berubah): loading / data / err dalam satu state.
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]) {
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
      .catch((e) => alive && setS({ loading: false, data: null, err: errMsg(e) }));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return s;
}
