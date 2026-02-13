const SNAPSHOT_PREFIX = 'oci_cm_snapshot:';

function getStorageKey(cacheKey) {
  return `${SNAPSHOT_PREFIX}${cacheKey}`;
}

export function loadSnapshot(cacheKey) {
  try {
    const raw = localStorage.getItem(getStorageKey(cacheKey));
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return null;
    return parsed;
  } catch {
    return null;
  }
}

export function saveSnapshot(cacheKey, data) {
  try {
    const payload = JSON.stringify({
      saved_at: new Date().toISOString(),
      data,
    });
    localStorage.setItem(getStorageKey(cacheKey), payload);
  } catch {
    // Ignore storage issues and keep runtime state functional.
  }
}

export function isSnapshotFresh(snapshot, ttlMs) {
  if (!snapshot?.saved_at) return false;
  const ts = Date.parse(snapshot.saved_at);
  if (Number.isNaN(ts)) return false;
  return Date.now() - ts <= ttlMs;
}

