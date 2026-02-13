import { useEffect, useMemo, useState } from 'react';
import { checkHealth, getDiagnostics, getJobsSummary, refreshDiagnostics } from '../services/api';

const STATUS_CLASS = {
  connected: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  partial: 'bg-amber-100 text-amber-700 border-amber-200',
  failed: 'bg-rose-100 text-rose-700 border-rose-200',
  degraded: 'bg-amber-100 text-amber-700 border-amber-200',
  healthy: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  ready: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  idle: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  busy: 'bg-sky-100 text-sky-700 border-sky-200',
  running: 'bg-sky-100 text-sky-700 border-sky-200',
  error: 'bg-rose-100 text-rose-700 border-rose-200',
  unknown: 'bg-slate-100 text-slate-600 border-slate-200',
};

const label = (value) => {
  if (!value) return 'Unknown';
  return value.charAt(0).toUpperCase() + value.slice(1);
};

function Pill({ name, value }) {
  const key = (value || 'unknown').toLowerCase();
  const cls = STATUS_CLASS[key] || STATUS_CLASS.unknown;
  return (
    <div className={`rounded-md border px-2 py-1 text-[11px] font-medium ${cls}`}>
      {name}: {label(value)}
    </div>
  );
}

function BarSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
      {Array.from({ length: 5 }).map((_, idx) => (
        <div key={idx} className="h-7 animate-pulse rounded-md bg-slate-100" />
      ))}
    </div>
  );
}

export default function GlobalStatusBar() {
  const [loading, setLoading] = useState(true);
  const [diagDown, setDiagDown] = useState(false);
  const [state, setState] = useState({
    oci: 'unknown',
    db: 'unknown',
    worker: 'unknown',
    reports: 'unknown',
    lastSync: null,
  });

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const [diagRes, healthRes, jobsRes] = await Promise.allSettled([
          getDiagnostics(),
          checkHealth(),
          getJobsSummary(),
        ]);
        if (!mounted) return;

        let oci = 'unknown';
        let lastSync = null;
        let diagUnavailable = false;
        if (diagRes.status === 'fulfilled') {
          oci = diagRes.value?.data?.data?.status || 'unknown';
          lastSync = diagRes.value?.data?.data?.last_sync_time || null;
        } else {
          diagUnavailable = true;
        }

        const dbStatus = healthRes.status === 'fulfilled'
          ? (healthRes.value?.data?.status === 'healthy' ? 'healthy' : 'degraded')
          : 'degraded';

        const workerState = jobsRes.status === 'fulfilled'
          ? (jobsRes.value?.data?.data?.worker_state || 'unknown')
          : 'unknown';
        const reportsState = jobsRes.status === 'fulfilled'
          ? (jobsRes.value?.data?.data?.report_state || 'unknown')
          : 'unknown';

        setDiagDown(diagUnavailable);
        setState({
          oci,
          db: dbStatus,
          worker: workerState,
          reports: reportsState,
          lastSync,
        });
      } finally {
        if (mounted) setLoading(false);
      }
    };

    load();
    const timer = setInterval(load, 60000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  const lastSyncText = useMemo(() => {
    if (!state.lastSync) return 'n/a';
    const parsed = new Date(state.lastSync);
    if (Number.isNaN(parsed.getTime())) return 'n/a';
    return parsed.toLocaleString();
  }, [state.lastSync]);

  const handleRetryDiagnostics = async () => {
    try {
      await refreshDiagnostics();
    } catch {
      // Keep UI non-blocking if refresh trigger fails.
    }
  };

  return (
    <div className="mb-4 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm">
      {loading ? <BarSkeleton /> : (
        <div className="flex flex-wrap items-center gap-2">
          <Pill name="OCI" value={state.oci} />
          <Pill name="DB" value={state.db} />
          <Pill name="Worker" value={state.worker} />
          <Pill name="Reports" value={state.reports} />
          <div className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] font-medium text-slate-600">
            Last Sync: {lastSyncText}
          </div>
          {diagDown ? (
            <button
              type="button"
              title="Diagnostics unavailable"
              className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-[11px] font-medium text-amber-700 hover:bg-amber-100"
              onClick={handleRetryDiagnostics}
            >
              Retry Diagnostics
            </button>
          ) : null}
        </div>
      )}
    </div>
  );
}
