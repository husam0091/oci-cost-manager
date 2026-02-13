import { useEffect, useMemo, useState } from 'react';
import { exportLogs, getLogs, getLogsTimeline } from '../services/api';

const QUICK_RANGES = [
  { key: '15m', label: 'Last 15m', mins: 15 },
  { key: '1h', label: 'Last 1h', mins: 60 },
  { key: '24h', label: 'Last 24h', mins: 24 * 60 },
];

const LOG_TYPES = ['backend', 'oci', 'frontend', 'db', 'security', 'audit'];
const LEVELS = ['debug', 'info', 'warn', 'error', 'critical'];

const buildFromIso = (mins) => new Date(Date.now() - (mins * 60 * 1000)).toISOString();

export default function Logs({ role = 'viewer' }) {
  const authorized = role === 'admin' || role === 'finops';
  const [loading, setLoading] = useState(true);
  const [logs, setLogs] = useState([]);
  const [expanded, setExpanded] = useState({});
  const [timeline, setTimeline] = useState([]);
  const [filters, setFilters] = useState({
    log_type: '',
    level: '',
    q: '',
    correlation_id: '',
    from: buildFromIso(15),
    to: '',
    limit: 200,
  });

  const loadLogs = async () => {
    if (!authorized) return;
    setLoading(true);
    try {
      const res = await getLogs(filters);
      setLogs(res?.data?.data?.items || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadLogs();
  }, [authorized]);

  const exportNow = async (format) => {
    await exportLogs({ ...filters, format });
    alert(`Export queued (${format}). Check jobs status.`);
  };

  const onTimeline = async (cid) => {
    if (!cid) return;
    const res = await getLogsTimeline(cid);
    setTimeline(res?.data?.data?.items || []);
  };

  const summary = useMemo(() => ({
    total: logs.length,
    errors: logs.filter((l) => l.level === 'error').length,
  }), [logs]);

  if (!authorized) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
        Access denied. Logs page is restricted to `admin` and `finops`.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <h3 className="text-lg font-semibold text-slate-900">Logs & Diagnostics</h3>
        <p className="mt-1 text-sm text-slate-600">Classified logs with correlation search and export.</p>
        <p className="mt-1 text-xs text-slate-500">Default window: last 15 minutes.</p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-2">
          {LOG_TYPES.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setFilters((f) => ({ ...f, log_type: f.log_type === t ? '' : t }))}
              className={`rounded-md border px-2 py-1 text-xs ${filters.log_type === t ? 'border-cyan-300 bg-cyan-50 text-cyan-700' : 'border-slate-200 text-slate-600'}`}
            >
              {t}
            </button>
          ))}
          <select
            className="rounded-md border border-slate-200 px-2 py-1 text-xs"
            value={filters.level}
            onChange={(e) => setFilters((f) => ({ ...f, level: e.target.value }))}
          >
            <option value="">All levels</option>
            {LEVELS.map((lvl) => <option key={lvl} value={lvl}>{lvl}</option>)}
          </select>
          <input
            value={filters.q}
            onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))}
            placeholder="Search text"
            className="min-w-44 rounded-md border border-slate-200 px-2 py-1 text-xs"
          />
          <input
            value={filters.correlation_id}
            onChange={(e) => setFilters((f) => ({ ...f, correlation_id: e.target.value }))}
            placeholder="Correlation ID"
            className="min-w-52 rounded-md border border-slate-200 px-2 py-1 text-xs"
          />
          {QUICK_RANGES.map((r) => (
            <button
              key={r.key}
              type="button"
              onClick={() => setFilters((f) => ({ ...f, from: buildFromIso(r.mins), to: '' }))}
              className="rounded-md border border-slate-200 px-2 py-1 text-xs text-slate-600"
            >
              {r.label}
            </button>
          ))}
          <button type="button" onClick={loadLogs} className="rounded-md border border-slate-300 bg-slate-50 px-2 py-1 text-xs">Apply</button>
          <button type="button" onClick={() => exportNow('json')} className="rounded-md border border-slate-300 bg-slate-50 px-2 py-1 text-xs">Export JSON</button>
          <button type="button" onClick={() => exportNow('csv')} className="rounded-md border border-slate-300 bg-slate-50 px-2 py-1 text-xs">Export CSV</button>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="mb-3 flex items-center justify-between text-sm">
          <span>Total: {summary.total}</span>
          <span className="text-rose-600">Errors: {summary.errors}</span>
        </div>
        {loading ? <div className="h-28 animate-pulse rounded-lg bg-slate-100" /> : (
          <div className="space-y-2">
            {logs.map((row) => (
              <div key={row.id} className="rounded-lg border border-slate-200 p-2 text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold">{row.level}</span>
                  <span>{row.log_type}</span>
                  <span>{row.source}</span>
                  <span className="text-slate-500">{row.ts}</span>
                  <button type="button" className="text-cyan-700" onClick={() => onTimeline(row.correlation_id)}>
                    {row.correlation_id}
                  </button>
                  <button
                    type="button"
                    className="ml-auto text-slate-600"
                    onClick={() => setExpanded((s) => ({ ...s, [row.id]: !s[row.id] }))}
                  >
                    {expanded[row.id] ? 'Hide details' : 'Show details'}
                  </button>
                </div>
                <div className="mt-1 text-slate-800">{row.message}</div>
                {expanded[row.id] ? (
                  <pre className="mt-2 max-h-56 overflow-auto rounded bg-slate-950 p-2 text-[11px] text-slate-100">
                    {JSON.stringify(row.details || {}, null, 2)}
                  </pre>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <h4 className="mb-2 text-sm font-semibold text-slate-900">Correlation Timeline</h4>
        {!timeline.length ? (
          <p className="text-xs text-slate-500">Select a correlation ID from logs above.</p>
        ) : (
          <div className="space-y-1 text-xs">
            {timeline.slice(0, 200).map((item) => (
              <div key={`${item.id}-${item.ts}`} className="rounded border border-slate-200 px-2 py-1">
                <span className="mr-2 text-slate-500">{item.ts}</span>
                <span className="mr-2 font-semibold">{item.log_type}</span>
                <span>{item.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
