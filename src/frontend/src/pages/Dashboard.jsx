import { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw, ShieldCheck, AlertTriangle, Info, Globe } from 'lucide-react';
import { Link } from 'react-router-dom';

import { costsBreakdownV2, costsMoversV2, dashboardSummaryV2, getMe, adminGetScanRuns, getDiagnostics, getDailyCosts, getSubscriptions, getCostsByRegion } from '../services/api';
import { parseBooleanFlag } from '../utils/flags';
import { getDateRangeForPreset } from '../utils/dateRanges';
import { UI_COPY } from '../constants/copy';
import { useStaleSnapshotQuery } from '../hooks/useStaleSnapshotQuery';

function currency(value) {
  return `$${Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function deltaChipClass(value) {
  if (value > 0) return 'bg-emerald-50 text-emerald-700';
  if (value < 0) return 'bg-rose-50 text-rose-700';
  return 'bg-slate-100 text-slate-700';
}

function DeltaChip({ deltaAbs, deltaPct, compact = false }) {
  return (
    <span className={`inline-flex rounded-full px-2 py-1 text-xs ${deltaChipClass(deltaAbs)}`}>
      {deltaAbs > 0 ? '+' : ''}{currency(deltaAbs)}{compact ? '' : ` (${deltaPct > 0 ? '+' : ''}${Number(deltaPct || 0).toFixed(2)}%)`}
    </span>
  );
}

function SectionCard({ children, muted = false }) {
  return <div className={`bg-white border border-slate-200 rounded-2xl shadow-sm p-5 dark:bg-slate-800 dark:border-slate-700 ${muted ? 'opacity-70' : ''}`}>{children}</div>;
}

function EmptyState({ text = 'No cost data available for this range' }) {
  return <p className="text-sm text-slate-500 dark:text-slate-400">{text}</p>;
}

function WidgetSkeleton({ className = '' }) {
  return <div className={`animate-pulse rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800 ${className}`} />;
}

function TopServiceRow({ row }) {
  const width = Math.max(2, Math.min(100, Number(row.share_pct || 0)));
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="truncate text-sm text-slate-800 dark:text-slate-200">{row.name}</span>
          <span className="bg-slate-100 text-slate-700 rounded-full px-2 py-1 text-xs dark:bg-slate-700 dark:text-slate-300">{Number(row.share_pct || 0).toFixed(2)}%</span>
        </div>
        <span className="text-sm font-medium text-slate-900 dark:text-slate-100">{currency(row.current)}</span>
      </div>
      <div className="h-2 w-full rounded bg-slate-200 dark:bg-slate-700">
        <div className="h-2 rounded bg-indigo-500" style={{ width: `${width}%` }} />
      </div>
      <div>
        <DeltaChip deltaAbs={row.delta_abs} deltaPct={row.delta_pct} />
      </div>
    </div>
  );
}

function SpotlightCard({ item }) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5 dark:bg-slate-800 dark:border-slate-700">
      <p className="text-sm font-medium text-slate-600 dark:text-slate-400">{item.compartment_name}</p>
      <p className="mt-1 text-xl font-semibold text-slate-900 dark:text-slate-100">{currency(item.totals?.current)}</p>
      <div className="mt-2">
        <DeltaChip deltaAbs={item.totals?.delta_abs || 0} deltaPct={item.totals?.delta_pct || 0} />
      </div>
      <div className="mt-3 space-y-2">
        {(item.top_services || []).map((svc) => {
          const width = Math.max(2, Math.min(100, Number(svc.share_pct || 0)));
          return (
            <div key={`${item.compartment_id}-${svc.name}`}>
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="truncate text-sm text-slate-700 dark:text-slate-300">{svc.name}</span>
                <span className="bg-slate-100 text-slate-700 rounded-full px-2 py-1 text-xs dark:bg-slate-700 dark:text-slate-300">{Number(svc.share_pct || 0).toFixed(2)}%</span>
              </div>
              <div className="h-2 w-full rounded bg-slate-200 dark:bg-slate-700">
                <div className="h-2 rounded bg-indigo-500" style={{ width: `${width}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Info Tooltip ────────────────────────────────────────────────────────────
function InfoTooltip({ text }) {
  const [show, setShow] = useState(false);
  return (
    <span className="relative inline-flex items-center">
      <button
        type="button"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onFocus={() => setShow(true)}
        onBlur={() => setShow(false)}
        className="ml-1 text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 focus:outline-none"
        aria-label="More information"
      >
        <Info size={12} />
      </button>
      {show && (
        <span className="absolute bottom-full left-1/2 z-50 mb-2 w-64 -translate-x-1/2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600 shadow-xl dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200">
          {text}
        </span>
      )}
    </span>
  );
}

// ─── Metric Card ─────────────────────────────────────────────────────────────
function MetricCard({ label, tooltip, value, sub, delta, muted = false }) {
  return (
    <div className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800 ${muted ? 'opacity-60' : ''}`}>
      <p className="flex items-center text-sm font-medium text-slate-600 dark:text-slate-400">
        {label}
        {tooltip && <InfoTooltip text={tooltip} />}
      </p>
      <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-100">{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{sub}</p>}
      {delta !== undefined && (
        <div className="mt-2">
          <DeltaChip deltaAbs={delta.abs} deltaPct={delta.pct} compact={delta.compact} />
        </div>
      )}
    </div>
  );
}

// ─── Region Breakdown Panel ───────────────────────────────────────────────────
function RegionBreakdownPanel({ period, activeRegion }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (activeRegion && activeRegion !== 'all') {
      setData(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    getCostsByRegion({ start_date: period.start, end_date: period.end })
      .then((res) => setData(res?.data?.data || null))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [period.start, period.end, activeRegion]);

  if (activeRegion && activeRegion !== 'all') return null;
  if (loading) return (
    <div className="animate-pulse rounded-2xl border border-slate-200 bg-white p-5 shadow-sm h-28 dark:border-slate-700 dark:bg-slate-800" />
  );
  if (!data || !data.regions?.length) return null;

  const maxVal = Math.max(...data.regions.map((r) => r.total), 0.01);
  return (
    <div className="rounded-2xl border border-indigo-100 bg-white p-5 shadow-sm dark:border-indigo-800 dark:bg-slate-800">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Globe size={16} className="text-indigo-500" />
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Spend Across Regions</h2>
          <InfoTooltip text="Total cost from OCI Usage API grouped by region dimension. All values in USD. OCI billing lag of 24–48h applies." />
        </div>
        <span className="text-sm font-bold text-indigo-700 dark:text-indigo-400">${Number(data.total || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} total</span>
      </div>
      <div className="mt-4 space-y-3">
        {data.regions.map((r) => {
          const pct = maxVal > 0 ? (r.total / maxVal) * 100 : 0;
          return (
            <div key={r.region} className="group">
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="text-sm text-slate-700 font-medium dark:text-slate-300">{r.region}</span>
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500 dark:bg-slate-700 dark:text-slate-400">{r.share_pct}%</span>
                  <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">${Number(r.total).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              </div>
              <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
                <div
                  className="h-2.5 rounded-full bg-indigo-500 transition-all duration-500"
                  style={{ width: `${Math.max(pct, 1)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <p className="mt-3 text-xs text-slate-400 dark:text-slate-500">
        Period: {data.period?.start_date} to {data.period?.end_date} · Use the region selector in the header to drill into a single region.
      </p>
    </div>
  );
}

function Toggle({ options, value, onChange }) {
  return (
    <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1 dark:border-slate-600 dark:bg-slate-800">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`rounded-md px-3 py-1 text-xs ${value === opt.value ? 'bg-slate-200 text-slate-900 dark:bg-slate-600 dark:text-slate-100' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700'}`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

// ─── Universal Credits Panel ────────────────────────────────────────────────
const MANUAL_COMMIT_KEY = 'oci_manual_commitment';

function UniversalCreditsPanel({ data }) {
  const [manualInput, setManualInput] = useState(
    () => localStorage.getItem(MANUAL_COMMIT_KEY) || ''
  );
  const [editMode, setEditMode] = useState(false);
  const [draft, setDraft] = useState(manualInput);

  if (!data) return null;
  const {
    total_consumed_ytd, total_consumed_mtd,
    year_start, as_of,
    subscription_api_available, subscriptions,
  } = data;

  // Use API value if available, else fall back to manually entered value
  const apiCommitted = Number(data.total_committed || 0);
  const manualCommitted = Number(manualInput || 0);
  const total_committed = apiCommitted > 0 ? apiCommitted : manualCommitted;
  const remaining = total_committed > 0 && total_consumed_ytd != null
    ? round2(total_committed - total_consumed_ytd) : null;
  const utilization_pct = total_committed > 0 && total_consumed_ytd != null
    ? Math.min(round2(total_consumed_ytd / total_committed * 100), 100) : 0;

  function round2(v) { return Math.round(v * 100) / 100; }
  const pct = Number(utilization_pct || 0);
  const barColor = pct >= 90 ? 'bg-rose-500' : pct >= 70 ? 'bg-amber-400' : 'bg-emerald-500';

  const saveManual = () => {
    localStorage.setItem(MANUAL_COMMIT_KEY, draft);
    setManualInput(draft);
    setEditMode(false);
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-slate-700">Universal Credits</h2>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
          YTD {year_start} → {as_of}
        </span>
      </div>
      {!subscription_api_available && data.subscription_error && (
        <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">
          <span className="font-medium">API diagnostic:</span> {data.subscription_error}
        </div>
      )}
      {!subscription_api_available && (
        <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="text-xs font-medium text-slate-700">Annual Commitment (manual)</p>
              <p className="text-xs text-slate-400">Enter your OCI Universal Credit commitment to see utilization</p>
            </div>
            {!editMode ? (
              <div className="flex items-center gap-2">
                {manualCommitted > 0 && (
                  <span className="text-sm font-bold text-slate-800">
                    ${manualCommitted.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => { setDraft(manualInput); setEditMode(true); }}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-100"
                >
                  {manualCommitted > 0 ? 'Edit' : 'Set Amount'}
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">$</span>
                <input
                  type="number"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  className="w-32 rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                  placeholder="e.g. 500000"
                  autoFocus
                />
                <button
                  type="button"
                  onClick={saveManual}
                  className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white"
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={() => setEditMode(false)}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-600"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        </div>
      )}
      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
          <p className="text-xs text-slate-500">Committed (Annual)</p>
          <p className="mt-1 text-lg font-bold text-slate-900">
            {total_committed > 0 ? `$${Number(total_committed).toLocaleString(undefined,{maximumFractionDigits:0})}` : '—'}
          </p>
        </div>
        <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
          <p className="text-xs text-slate-500">Consumed YTD</p>
          <p className="mt-1 text-lg font-bold text-indigo-700">
            {total_consumed_ytd != null ? `$${Number(total_consumed_ytd).toLocaleString(undefined,{maximumFractionDigits:0})}` : '—'}
          </p>
        </div>
        <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
          <p className="text-xs text-slate-500">Consumed MTD</p>
          <p className="mt-1 text-lg font-bold text-slate-800">
            {total_consumed_mtd != null ? `$${Number(total_consumed_mtd).toLocaleString(undefined,{maximumFractionDigits:0})}` : '—'}
          </p>
        </div>
        <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
          <p className="text-xs text-slate-500">Remaining</p>
          <p className={`mt-1 text-lg font-bold ${remaining != null && remaining < 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
            {remaining != null ? `$${Number(remaining).toLocaleString(undefined,{maximumFractionDigits:0})}` : '—'}
          </p>
        </div>
      </div>
      {total_committed > 0 && total_consumed_ytd != null && (
        <div className="mt-4">
          <div className="mb-1 flex justify-between text-xs text-slate-500">
            <span>Credit utilization</span>
            <span className="font-medium">{pct.toFixed(1)}%</span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-slate-100">
            <div className={`h-3 rounded-full transition-all ${barColor}`} style={{ width: `${Math.min(pct, 100)}%` }} />
          </div>
          <div className="mt-1 flex justify-between text-xs text-slate-400">
            <span>$0</span>
            <span>${Number(total_committed).toLocaleString(undefined,{maximumFractionDigits:0})}</span>
          </div>
        </div>
      )}
      {subscription_api_available && subscriptions?.length > 0 && (
        <div className="mt-3 space-y-1">
          {subscriptions.map((s, i) => (
            <div key={s.id || i} className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-1.5 text-xs text-slate-600">
              <span className="rounded-full bg-indigo-100 px-2 py-0.5 font-medium text-indigo-700">{s.subscription_type || 'ANNUAL'}</span>
              <span>{s.time_start?.slice(0,10)} → {s.time_end?.slice(0,10)}</span>
              <span className="ml-auto font-medium">${Number(s.total_value || 0).toLocaleString(undefined,{maximumFractionDigits:0})} {s.currency}</span>
              <span className={`rounded-full px-2 py-0.5 ${(s.status||'').toLowerCase()==='active'?'bg-emerald-100 text-emerald-700':'bg-slate-200 text-slate-500'}`}>{s.status||'—'}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Daily Cost Chart ────────────────────────────────────────────────────────
function DailyCostChart({ data }) {
  if (!data?.days?.length) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Daily Cost — Current Month</h2>
        <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">No daily data available. Run a scan to populate cost data.</p>
      </div>
    );
  }
  const days = data.days;
  const maxVal = Math.max(...days.map(d => d.total), 0.01);
  const mtd = data.mtd_total || 0;
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Daily Cost — Current Month</h2>
          <p className="text-xs text-slate-400 dark:text-slate-500">{data.period?.start_date} to {data.period?.end_date}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-500 dark:text-slate-400">MTD Total</p>
          <p className="text-xl font-bold text-indigo-700 dark:text-indigo-400">${Number(mtd).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
        </div>
      </div>
      <div className="mt-4 flex items-end gap-0.5 overflow-x-auto pb-1" style={{ minHeight: '80px' }}>
        {days.map((d) => {
          const heightPct = maxVal > 0 ? (d.total / maxVal) * 100 : 0;
          const dayNum = new Date(d.date + 'T00:00:00').getDate();
          const isToday = d.date === new Date().toISOString().slice(0, 10);
          return (
            <div key={d.date} className="group relative flex flex-1 flex-col items-center" style={{ minWidth: '14px' }}>
              <div
                className={`w-full rounded-t transition-all ${
                  isToday ? 'bg-indigo-600' : 'bg-indigo-300 hover:bg-indigo-500 dark:bg-indigo-700 dark:hover:bg-indigo-500'
                }`}
                style={{ height: `${Math.max(heightPct, 2)}px`, maxHeight: '80px' }}
              />
              {/* tooltip */}
              <div className="pointer-events-none absolute bottom-full mb-1 hidden w-max rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs shadow-lg group-hover:block z-10 dark:border-slate-600 dark:bg-slate-700">
                <p className="font-semibold text-slate-800 dark:text-slate-200">{d.date}</p>
                <p className="text-indigo-700 dark:text-indigo-400">${Number(d.total).toFixed(2)}</p>
                {Object.entries(d.by_service || {}).slice(0, 4).map(([svc, cost]) => (
                  <p key={svc} className="text-slate-500 dark:text-slate-400">{svc}: ${Number(cost).toFixed(2)}</p>
                ))}
              </div>
              <span className="mt-1 text-[9px] text-slate-400 dark:text-slate-500 leading-none">{dayNum}</span>
            </div>
          );
        })}
      </div>
      <div className="mt-2 flex justify-between text-xs text-slate-400 dark:text-slate-500">
        <span>Day 1</span>
        <span>Peak: ${Number(maxVal).toFixed(2)}</span>
      </div>
    </div>
  );
}

// ─── Data Freshness Panel ────────────────────────────────────────────────────
function DataFreshnessPanel({ lastScan, ociStatus }) {
  const [open, setOpen] = useState(false);
  const ago = lastScan ? (() => {
    const diff = Math.floor((Date.now() - new Date(lastScan)) / 60000);
    if (diff < 60) return `${diff}m ago`;
    if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
    return `${Math.floor(diff / 1440)}d ago`;
  })() : null;
  const connected = ociStatus === 'healthy';
  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-5 py-3 text-left"
      >
        <div className="flex items-center gap-3">
          <span className={`h-2.5 w-2.5 rounded-full ${connected ? 'bg-emerald-500' : 'bg-amber-400'}`} />
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
            OCI Cost Data — {connected ? 'Connected' : 'Check Connection'}
          </span>
          {ago && <span className="text-xs text-slate-400 dark:text-slate-500">Last sync {ago}</span>}
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-900 dark:text-amber-300">24–48h billing lag</span>
          <Info size={14} className="text-slate-400" />
        </div>
      </button>
      {open && (
        <div className="border-t border-slate-100 px-5 py-4 text-sm text-slate-600 space-y-3 dark:border-slate-700 dark:text-slate-300">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 space-y-1 dark:border-slate-600 dark:bg-slate-900">
              <p className="text-xs font-semibold text-slate-700 flex items-center gap-1 dark:text-slate-200"><ShieldCheck size={13} className="text-emerald-600" /> Data Source</p>
              <p className="text-xs dark:text-slate-400">Costs come directly from the <span className="font-medium">OCI Usage API</span> using <code className="bg-slate-100 px-1 rounded dark:bg-slate-700 dark:text-slate-200">query_type=COST</code> and <code className="bg-slate-100 px-1 rounded dark:bg-slate-700 dark:text-slate-200">computed_amount</code> — the same field OCI Cost Analysis uses. No estimates or calculations are applied.</p>
            </div>
            <div className="rounded-xl border border-amber-100 bg-amber-50 p-3 space-y-1 dark:border-amber-800 dark:bg-amber-950">
              <p className="text-xs font-semibold text-amber-800 flex items-center gap-1 dark:text-amber-300"><AlertTriangle size={13} /> Billing Lag</p>
              <p className="text-xs text-amber-700 dark:text-amber-400">OCI billing data has a <span className="font-medium">24–48 hour processing delay</span>. Costs shown reflect charges up to 1–2 days ago. Today's actual charges will appear in a future scan.</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 space-y-1 dark:border-slate-600 dark:bg-slate-900">
              <p className="text-xs font-semibold text-slate-700 dark:text-slate-200">Currency</p>
              <p className="text-xs dark:text-slate-400">Values are shown in the currency returned by OCI (typically <span className="font-medium">USD</span>). If your tenancy bills in a different currency, the raw amounts from OCI are stored as-is without conversion.</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 space-y-1 dark:border-slate-600 dark:bg-slate-900">
              <p className="text-xs font-semibold text-slate-700 dark:text-slate-200">How to verify</p>
              <p className="text-xs dark:text-slate-400">Compare the <span className="font-medium">Total Spend</span> on this dashboard against <span className="font-medium">OCI Console → Billing → Cost Analysis → This Month → All Compartments</span>. Values should match within the billing lag window. A larger gap usually means the OCI key lacks <code className="bg-slate-100 px-1 rounded dark:bg-slate-700 dark:text-slate-200">TENANCY_INSPECT</code> or <code className="bg-slate-100 px-1 rounded dark:bg-slate-700 dark:text-slate-200">USAGE_INSPECTOR</code> permissions.</p>
            </div>
          </div>
          {lastScan && (
            <p className="text-xs text-slate-400 dark:text-slate-500">Last successful scan: {new Date(lastScan).toLocaleString()}</p>
          )}
        </div>
      )}
    </div>
  );
}

function Dashboard({ persona = 'Executive', activeRegion }) {
  const period = useMemo(() => getDateRangeForPreset('prev_month'), []);

  const [moversGroupBy, setMoversGroupBy] = useState('service');
  const [moversDirection, setMoversDirection] = useState('up');
  const [executiveView, setExecutiveView] = useState(false);
  const [productState, setProductState] = useState(null);
  const [demoMode, setDemoMode] = useState(false);
  const [lastScan, setLastScan] = useState(null);
  const [ociStatus, setOciStatus] = useState(null);
  const [subscriptionData, setSubscriptionData] = useState(null);
  const [dailyData, setDailyData] = useState(null);

  const loadDashboardData = useCallback(async () => {
    const summaryRes = await dashboardSummaryV2({
      start_date: period.start,
      end_date: period.end,
      compare: 'previous',
      region: activeRegion,
    });

    const [breakdownRes, moversRes] = await Promise.all([
      costsBreakdownV2({
        group_by: 'service',
        start_date: period.start,
        end_date: period.end,
        compare: 'previous',
        limit: 8,
        min_share_pct: 0.5,
        region: activeRegion,
      }),
      costsMoversV2({
        group_by: moversGroupBy,
        start_date: period.start,
        end_date: period.end,
        compare: 'previous',
        limit: 10,
        direction: moversDirection,
        region: activeRegion,
      }),
    ]);

    return {
      summary: summaryRes.data?.data || null,
      breakdown: breakdownRes.data?.data || null,
      movers: moversRes.data?.data || null,
    };
  }, [period.end, period.start, moversDirection, moversGroupBy, activeRegion]);

  const {
    data: dashboardData,
    loading,
    refreshing,
    error,
    isStale,
    savedAt,
    refresh,
    hasData,
  } = useStaleSnapshotQuery({
    cacheKey: `dashboard:${period.start}:${period.end}:${moversGroupBy}:${moversDirection}:${activeRegion || 'all'}`,
    ttlMs: 5 * 60 * 1000,
    queryFn: loadDashboardData,
    dependencies: [period.start, period.end, moversGroupBy, moversDirection, activeRegion],
    fallbackError: 'Failed to load dashboard data',
  });

  useEffect(() => {
    getMe()
      .then((res) => {
        const data = res?.data?.data || {};
        setProductState(data.product_state || null);
        setDemoMode(parseBooleanFlag(data?.feature_flags?.enable_demo_mode));
      })
      .catch(() => {
        setProductState(null);
        setDemoMode(false);
      });
    // Load last scan time and OCI connection status
    adminGetScanRuns()
      .then((res) => {
        const runs = res?.data?.data || [];
        const last = runs.find((r) => r.status === 'success');
        if (last?.finished_at) setLastScan(last.finished_at);
      })
      .catch(() => {});
    getDiagnostics()
      .then((res) => {
        setOciStatus(res?.data?.data?.status || null);
      })
      .catch(() => {});
    // Universal Credits
    getSubscriptions()
      .then((res) => setSubscriptionData(res?.data?.data || null))
      .catch(() => {});
    // Daily cost chart
    getDailyCosts({ region: activeRegion })
      .then((res) => setDailyData(res?.data?.data || null))
      .catch(() => {});
  }, [activeRegion]);

  useEffect(() => {
    setExecutiveView(persona === 'Executive');
  }, [persona]);

  const summary = dashboardData?.summary || null;
  const breakdown = dashboardData?.breakdown || null;
  const movers = dashboardData?.movers || null;

  const totals = summary?.totals || { current: 0, previous: 0, delta_abs: 0, delta_pct: 0 };
  const topDriver = summary?.top_driver || { group: 'No data', current: 0, previous: 0, share_pct: 0, delta_abs: 0, delta_pct: 0 };
  const biggestMover = summary?.biggest_mover || { entity_type: 'service', entity_name: 'No data', delta_abs: 0, delta_pct: 0 };
  const mapping = summary?.mapping_health || { unallocated_pct: 0, low_confidence_count: 0 };
  const licenses = summary?.license_spotlight || {
    windows: { monthly_cost: 0, daily_estimate: 0, delta_abs: 0 },
    sql_server: { monthly_cost: 0, daily_estimate: 0, delta_abs: 0 },
    oracle_os: { monthly_cost: 0, daily_estimate: 0, delta_abs: 0 },
  };
  const storage = summary?.storage_backup || {
    unattached_volumes: { count: 0, monthly_cost: 0 },
    backups: { count: 0, monthly_cost: 0 },
  };

  const isZeroTotal = Number(totals.current || 0) === 0;
  const days = Math.max(Number(summary?.period?.days || 1), 1);
  const totalDaily = Number(totals.current || 0) / days;
  const topServices = breakdown?.items || [];
  const moversItems = movers?.items || [];
  const coreSpotlight = summary?.core_business_spotlight || [];
  const savings = summary?.savings_opportunities || {
    potential_savings_monthly: 0,
    high_confidence_savings: 0,
    recommendation_count: 0,
  };
  const budgetHealth = summary?.budget_health || {
    total_budgets: 0,
    budgets_at_risk: 0,
    budgets_breached: 0,
    highest_utilization_budget: null,
  };
  const executiveSignals = summary?.executive_signals || {
    run_rate_vs_budget: 'No budget data available.',
    forecasted_month_end_spend: 'No forecast data available.',
    top_risk_budget: 'No risk budget identified.',
    top_cost_driver_this_month: 'No cost driver identified.',
  };

  const regionLabel = activeRegion && activeRegion !== 'all' ? activeRegion : null;

  return (
    <div className="min-h-full space-y-6 bg-slate-50 p-1 dark:bg-slate-950">
      <DataFreshnessPanel lastScan={lastScan} ociStatus={ociStatus} />

      {regionLabel && (
        <div className="flex items-center gap-2 rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm text-indigo-800 dark:border-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
          <Globe size={15} className="text-indigo-500 flex-shrink-0" />
          <span>Viewing region: <span className="font-semibold">{regionLabel}</span> — all costs and metrics on this page are filtered to this region only.</span>
        </div>
      )}

      <UniversalCreditsPanel data={subscriptionData} />

      <RegionBreakdownPanel period={period} activeRegion={activeRegion} />

      <DailyCostChart data={dailyData} />

      {error ? (
        <div className="rounded-2xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
          Data unavailable due to API error
          <button
            type="button"
            onClick={() => refresh()}
            className="ml-3 rounded-lg border border-amber-400 px-2 py-1 text-xs hover:bg-amber-100"
          >
            Retry
          </button>
        </div>
      ) : null}
      <div className="flex flex-col items-start justify-between gap-3 md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">Dashboard</h1>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            {summary?.period?.start_date} to {summary?.period?.end_date}
          </p>
          <p className="text-xs text-slate-500">
            {savedAt ? `Snapshot: ${new Date(savedAt).toLocaleString()}` : 'No snapshot yet'}
            {isStale ? ' | stale' : ''}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            refresh();
          }}
          disabled={refreshing}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm hover:bg-slate-100 disabled:opacity-60 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
        <button
          type="button"
          onClick={() => setExecutiveView((v) => !v)}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm hover:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
        >
          {executiveView ? 'Hide Executive View' : 'Show Executive View'}
        </button>
      </div>

      {!hasData && loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <WidgetSkeleton className="h-28" />
          <WidgetSkeleton className="h-28" />
          <WidgetSkeleton className="h-28" />
          <WidgetSkeleton className="h-28" />
        </div>
      ) : null}

      {productState?.is_empty_system ? (
        <SectionCard>
          <h2 className="text-sm font-medium text-slate-600">First-Run Checklist</h2>
          <p className="mt-1 text-sm text-slate-500">Complete these steps to enable full FinOps workflows.</p>
          <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
            <div className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700">1. Configure OCI in Settings</div>
            <div className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700">2. Run first scan from Settings</div>
            <div className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700">3. Set important compartments</div>
            <div className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700">4. Create first budget</div>
            <div className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 md:col-span-2">5. Review recommendations and create actions</div>
          </div>
        </SectionCard>
      ) : null}

      {demoMode ? (
        <SectionCard>
          <p className="text-sm text-amber-700">
            Demo mode is enabled. Executors are blocked and write operations are read-only.
          </p>
        </SectionCard>
      ) : null}

      {isZeroTotal ? (
        <SectionCard muted>
          <EmptyState text="No data for selected range" />
        </SectionCard>
      ) : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {!summary && loading ? <WidgetSkeleton className="h-28" /> : (
          <MetricCard
            label="Total Spend"
            tooltip={`Sum of all OCI costs for the period ${summary?.period?.start_date || ''} to ${summary?.period?.end_date || ''} via OCI Usage API (computed_amount). Delta compares to the same-length previous period.${regionLabel ? ` Filtered to region: ${regionLabel}.` : ''}`}
            value={currency(totals.current)}
            sub={`Daily avg ${currency(totalDaily)} · Prev period ${currency(totals.previous)}`}
            delta={{ abs: totals.delta_abs, pct: totals.delta_pct }}
            muted={isZeroTotal}
          />
        )}
        {!summary && loading ? <WidgetSkeleton className="h-28" /> : (
          <MetricCard
            label="Top Cost Driver"
            tooltip={`The OCI service with the highest spend this period. Share % = this service's cost divided by total spend. Delta shows cost change vs. the previous same-length period.${regionLabel ? ` Region: ${regionLabel}.` : ''}`}
            value={topDriver.group || 'No data'}
            sub={`${currency(topDriver.current)} · Share ${Number(topDriver.share_pct || 0).toFixed(2)}%`}
            delta={{ abs: topDriver.delta_abs, pct: topDriver.delta_pct }}
            muted={isZeroTotal}
          />
        )}
        {!summary && loading ? <WidgetSkeleton className="h-28" /> : (
          <MetricCard
            label="Biggest Cost Mover"
            tooltip="The service with the largest absolute cost change compared to the previous period — either growing or shrinking. Useful for spotting unexpected shifts in spend."
            value={biggestMover.entity_name || 'No data'}
            sub={`Type: ${biggestMover.entity_type || 'service'}`}
            delta={{ abs: biggestMover.delta_abs, pct: biggestMover.delta_pct }}
            muted={isZeroTotal}
          />
        )}
        {!summary && loading ? <WidgetSkeleton className="h-28" /> : (
          <MetricCard
            label="Mapping Health"
            tooltip="Percentage of resources where the allocation (team/env/app) is unclassified or low-confidence. Lower is better. Low-confidence count shows resources where the detection method was a weak signal (e.g. SKU hint only, not image metadata)."
            value={`${Number(mapping.unallocated_pct || 0).toFixed(1)}% unallocated`}
            sub={`Low confidence: ${mapping.low_confidence_count || 0} resources`}
            muted={isZeroTotal}
          />
        )}
      </div>

      <SectionCard muted={isZeroTotal}>
        <h2 className="text-sm font-medium text-slate-600">Core Business Spotlight</h2>
        <div className="mt-3">
          {coreSpotlight.length === 0 ? (
            <EmptyState text="No core business compartments configured. Add them in Settings." />
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {coreSpotlight.map((item) => (
                <SpotlightCard key={item.compartment_id} item={item} />
              ))}
            </div>
          )}
        </div>
      </SectionCard>

      <SectionCard muted={isZeroTotal}>
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-medium text-slate-600">Savings Opportunities</h2>
          <Link to="/recommendations" className="text-xs font-medium text-indigo-700 hover:text-indigo-800">
            View recommendations
          </Link>
        </div>
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-slate-200 p-3">
            <p className="text-xs text-slate-600">Potential Monthly Savings</p>
            <p className="text-xl font-semibold text-emerald-600">{currency(savings.potential_savings_monthly)}</p>
          </div>
          <div className="rounded-xl border border-slate-200 p-3">
            <p className="text-xs text-slate-600">High Confidence Savings</p>
            <p className="text-xl font-semibold text-emerald-600">{currency(savings.high_confidence_savings)}</p>
          </div>
          <div className="rounded-xl border border-slate-200 p-3">
            <p className="text-xs text-slate-600">Recommendation Count</p>
            <p className="text-xl font-semibold text-slate-900">{Number(savings.recommendation_count || 0)}</p>
          </div>
        </div>
      </SectionCard>

      <SectionCard muted={isZeroTotal}>
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-medium text-slate-600">Budget Health</h2>
          <Link to="/budget" className="text-xs font-medium text-indigo-700 hover:text-indigo-800">
            View budgets
          </Link>
        </div>
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-4">
          <div className="rounded-xl border border-slate-200 p-3">
            <p className="text-xs text-slate-600">Total Budgets</p>
            <p className="text-xl font-semibold text-slate-900">{Number(budgetHealth.total_budgets || 0)}</p>
          </div>
          <div className="rounded-xl border border-slate-200 p-3">
            <p className="text-xs text-slate-600">At Risk</p>
            <p className="text-xl font-semibold text-amber-600">{Number(budgetHealth.budgets_at_risk || 0)}</p>
          </div>
          <div className="rounded-xl border border-slate-200 p-3">
            <p className="text-xs text-slate-600">Breached</p>
            <p className="text-xl font-semibold text-rose-600">{Number(budgetHealth.budgets_breached || 0)}</p>
          </div>
          <div className="rounded-xl border border-slate-200 p-3">
            <p className="text-xs text-slate-600">Highest Utilization</p>
            <p className="text-sm font-semibold text-slate-900">
              {budgetHealth.highest_utilization_budget?.budget_name || 'None'}
            </p>
            <p className="text-xs text-slate-600">
              {budgetHealth.highest_utilization_budget ? `${Number(budgetHealth.highest_utilization_budget.utilization_pct || 0).toFixed(2)}%` : '-'}
            </p>
          </div>
        </div>
      </SectionCard>

      {executiveView ? (
        <SectionCard muted={isZeroTotal}>
          <h2 className="text-sm font-medium text-slate-600">Executive Signals</h2>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl border border-slate-200 p-3">
              <p className="text-xs text-slate-600">Run-rate vs Budget</p>
              <p className="text-sm font-semibold text-slate-900">{executiveSignals.run_rate_vs_budget}</p>
            </div>
            <div className="rounded-xl border border-slate-200 p-3">
              <p className="text-xs text-slate-600">Forecasted Month-End Spend</p>
              <p className="text-sm font-semibold text-slate-900">{executiveSignals.forecasted_month_end_spend}</p>
            </div>
            <div className="rounded-xl border border-slate-200 p-3">
              <p className="text-xs text-slate-600">Top Risk Budget</p>
              <p className="text-sm font-semibold text-slate-900">{executiveSignals.top_risk_budget}</p>
            </div>
            <div className="rounded-xl border border-slate-200 p-3">
              <p className="text-xs text-slate-600">Top Cost Driver This Month</p>
              <p className="text-sm font-semibold text-slate-900">{executiveSignals.top_cost_driver_this_month}</p>
            </div>
          </div>
        </SectionCard>
      ) : null}

      <SectionCard muted={isZeroTotal}>
        <h2 className="text-sm font-medium text-slate-600">Top Services</h2>
        <div className="mt-3 space-y-3">
          {topServices.length === 0 ? (
            <EmptyState text="No data for selected range" />
          ) : (
            topServices.map((row) => <TopServiceRow key={row.name} row={row} />)
          )}
        </div>
      </SectionCard>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <MetricCard
          label="Windows License Cost"
          tooltip="Cost attributed to Windows OS SKUs. Detected via SKU name match ('Windows OS') or resource image metadata. High-confidence = image name contains 'windows'. Delta vs. previous period."
          value={currency(licenses.windows?.monthly_cost)}
          sub={`Daily avg ${currency(licenses.windows?.daily_estimate)}`}
          delta={{ abs: licenses.windows?.delta_abs || 0, pct: 0, compact: true }}
          muted={isZeroTotal}
        />
        <MetricCard
          label="SQL Server License Cost"
          tooltip="Cost attributed to Microsoft SQL Server. Detected via SKU name ('SQL Server', 'Microsoft SQL') or resource type. These are typically passed-through Oracle license charges on OCI."
          value={currency(licenses.sql_server?.monthly_cost)}
          sub={`Daily avg ${currency(licenses.sql_server?.daily_estimate)}`}
          delta={{ abs: licenses.sql_server?.delta_abs || 0, pct: 0, compact: true }}
          muted={isZeroTotal}
        />
        <MetricCard
          label="Oracle OS License Cost"
          tooltip="Cost attributed to Oracle Linux OS licenses. Detected via SKU name ('Oracle OS', 'Oracle Linux') or image metadata. Separate from Oracle Database costs."
          value={currency(licenses.oracle_os?.monthly_cost)}
          sub={`Daily avg ${currency(licenses.oracle_os?.daily_estimate)}`}
          delta={{ abs: licenses.oracle_os?.delta_abs || 0, pct: 0, compact: true }}
          muted={isZeroTotal}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <SectionCard muted={isZeroTotal}>
          <p className="flex items-center text-sm font-medium text-slate-600">
            Unattached Volumes
            <InfoTooltip text="Block and boot volumes currently not attached to any compute instance. Detected by checking attachment_state = UNATTACHED in resource metadata. These incur storage costs with no active workload benefit." />
          </p>
          <p className="mt-1 text-2xl font-semibold text-amber-600">{storage.unattached_volumes?.count || 0} <span className="text-base font-normal text-slate-500">volumes</span></p>
          <p className="mt-1 text-xs text-slate-600">Monthly {currency(storage.unattached_volumes?.monthly_cost)} · Daily {currency((storage.unattached_volumes?.monthly_cost || 0) / days)}</p>
        </SectionCard>
        <SectionCard muted={isZeroTotal}>
          <p className="flex items-center text-sm font-medium text-slate-600">
            Backup Storage
            <InfoTooltip text="Cost and count of backup and snapshot SKUs. Detected via SKU name containing 'backup' or 'snapshot'. Quantity is the total TB-months of backup storage billed this period." />
          </p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">{storage.backups?.count || 0} <span className="text-base font-normal text-slate-500">items</span></p>
          <p className="mt-1 text-xs text-slate-600">Monthly {currency(storage.backups?.monthly_cost)} · Daily {currency((storage.backups?.monthly_cost || 0) / days)}</p>
        </SectionCard>
      </div>

      <SectionCard muted={isZeroTotal}>
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <h2 className="text-sm font-medium text-slate-600">Top Movers</h2>
          <div className="flex flex-wrap items-center gap-2">
            <Toggle
              value={moversGroupBy}
              onChange={setMoversGroupBy}
              options={[
                { label: 'Services', value: 'service' },
                { label: 'Compartments', value: 'compartment' },
              ]}
            />
            <Toggle
              value={moversDirection}
              onChange={setMoversDirection}
              options={[
                { label: 'Up', value: 'up' },
                { label: 'Down', value: 'down' },
                { label: 'Both', value: 'both' },
              ]}
            />
          </div>
        </div>
        <div className="mt-3 overflow-x-auto">
          {moversItems.length === 0 ? (
            <EmptyState text="No data for selected range" />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-slate-600 dark:border-slate-700 dark:text-slate-400">
                  <th className="py-2 text-left">Entity</th>
                  <th className="py-2 text-right">Current</th>
                  <th className="py-2 text-right">Previous</th>
                  <th className="py-2 text-right">Delta Cost</th>
                  <th className="py-2 text-right">Delta %</th>
                </tr>
              </thead>
              <tbody>
                {moversItems.map((item) => (
                  <tr key={item.name} className="border-b border-slate-100 dark:border-slate-700">
                    <td className="py-2 text-slate-900 dark:text-slate-200">{item.name}</td>
                    <td className="py-2 text-right text-slate-900 dark:text-slate-200">{currency(item.current)}</td>
                    <td className="py-2 text-right text-slate-700 dark:text-slate-400">{currency(item.previous)}</td>
                    <td className="py-2 text-right"><DeltaChip deltaAbs={item.delta_abs} deltaPct={item.delta_pct} compact /></td>
                    <td className="py-2 text-right text-xs text-slate-600 dark:text-slate-400">{Number(item.delta_pct || 0).toFixed(2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </SectionCard>

      <SectionCard muted={isZeroTotal}>
        <h2 className="text-sm font-medium text-slate-600">Top Resources</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-600">
                <th className="py-2 text-left">Name</th>
                <th className="py-2 text-left">Type</th>
                <th className="py-2 text-left">Compartment</th>
                <th className="py-2 text-right">Current</th>
                <th className="py-2 text-right">Previous</th>
                <th className="py-2 text-right">Delta</th>
              </tr>
            </thead>
            <tbody>
              {(summary?.top_resources || []).map((r) => (
                <tr key={`${r.name}-${r.type}`} className="border-b border-slate-100">
                  <td className="py-2 text-slate-900">{r.name}</td>
                  <td className="py-2 text-slate-700">{r.type}</td>
                  <td className="py-2 text-slate-700">{r.compartment || '-'}</td>
                  <td className="py-2 text-right text-slate-900">{currency(r.current)}</td>
                  <td className="py-2 text-right text-slate-700">{currency(r.previous)}</td>
                  <td className="py-2 text-right"><DeltaChip deltaAbs={r.delta_abs || 0} deltaPct={r.delta_pct || 0} compact /></td>
                </tr>
              ))}
              {(!summary?.top_resources || summary.top_resources.length === 0) ? (
                <tr>
                  <td colSpan={6} className="py-3 text-slate-500">
                    No top resource rows in summary contract yet.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  );
}

export default Dashboard;
