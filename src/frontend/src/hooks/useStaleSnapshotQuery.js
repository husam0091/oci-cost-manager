import { useCallback, useEffect, useMemo, useState } from 'react';
import { isSnapshotFresh, loadSnapshot, saveSnapshot } from '../utils/staleCache';

function scheduleAfterPaint(callback) {
  if (typeof window !== 'undefined' && typeof window.requestIdleCallback === 'function') {
    const id = window.requestIdleCallback(callback, { timeout: 1200 });
    return () => window.cancelIdleCallback(id);
  }
  const timer = setTimeout(callback, 0);
  return () => clearTimeout(timer);
}

function toErrorMessage(error, fallback) {
  return (
    error?.response?.data?.detail ||
    error?.response?.data?.error?.message ||
    error?.message ||
    fallback
  );
}

export function useStaleSnapshotQuery({
  cacheKey,
  ttlMs,
  queryFn,
  dependencies = [],
  fallbackError = 'Failed to load data',
  retryCount = 2,
  retryBaseDelayMs = 300,
}) {
  const initialSnapshot = useMemo(() => loadSnapshot(cacheKey), [cacheKey]);
  const [data, setData] = useState(initialSnapshot?.data ?? null);
  const [savedAt, setSavedAt] = useState(initialSnapshot?.saved_at ?? null);
  const [loading, setLoading] = useState(!initialSnapshot?.data);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const snapshot = loadSnapshot(cacheKey);
    setData(snapshot?.data ?? null);
    setSavedAt(snapshot?.saved_at ?? null);
    setLoading(!snapshot?.data);
  }, [cacheKey]);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      let attempt = 0;
      let lastError = null;
      while (attempt <= retryCount) {
        try {
          const nextData = await queryFn();
          setData(nextData);
          setError('');
          saveSnapshot(cacheKey, nextData);
          setSavedAt(new Date().toISOString());
          return nextData;
        } catch (e) {
          lastError = e;
          if (attempt >= retryCount) break;
          const delay = retryBaseDelayMs * (2 ** attempt);
          await new Promise((resolve) => setTimeout(resolve, delay));
          attempt += 1;
        }
      }
      throw lastError;
    } catch (e) {
      setError(toErrorMessage(e, fallbackError));
      return null;
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [cacheKey, queryFn, fallbackError, retryBaseDelayMs, retryCount]);

  useEffect(() => {
    const cancelScheduled = scheduleAfterPaint(() => {
      refresh();
    });
    return () => cancelScheduled();
  }, [refresh, ...dependencies]);

  const snapshotMeta = useMemo(() => ({ saved_at: savedAt }), [savedAt]);
  const isStale = data ? !isSnapshotFresh(snapshotMeta, ttlMs) : false;

  return {
    data,
    loading,
    refreshing,
    error,
    isStale,
    savedAt,
    refresh,
    hasData: Boolean(data),
  };
}
