import { useCallback, useEffect, useState } from "react";

export const POLL_MS = 2000;

/** Loads data, then loads it again every two seconds while `keepPolling` says so. */
export function usePolled<T>(
  load: () => Promise<T>,
  keepPolling: (data: T) => boolean,
) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<string>();
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let current = true;
    load().then(
      (value) => {
        if (current) {
          setData(value);
          setError(undefined);
        }
      },
      (reason: unknown) => {
        if (current) setError(String(reason));
      },
    );
    return () => {
      current = false;
    };
  }, [load, tick]);

  useEffect(() => {
    if (data === undefined || !keepPolling(data)) return;
    const timer = setTimeout(() => {
      setTick((value) => value + 1);
    }, POLL_MS);
    return () => {
      clearTimeout(timer);
    };
  }, [data, keepPolling]);

  const reload = useCallback(() => {
    setTick((value) => value + 1);
  }, []);

  return { data, error, reload };
}
