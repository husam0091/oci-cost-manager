import { useCallback, useEffect, useMemo, useState } from 'react';
import { getCostSummary, getCostBreakdown, getCostMovers } from '../services/api';
import { getDateRangeForPreset, toIsoDate } from '../utils/dateRanges';
import { UI_COPY } from '../constants/copy';
import { useStaleSnapshotQuery } from '../hooks/useStaleSnapshotQuery';

function currency(value) {
  return `$${Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function deltaClass(value) {
  if (value > 0) return 'bg-emerald-50 text-emerald-700';
  if (value < 0) return 'bg-rose-50 text-rose-700';
  return 'bg-slate-100 text-slate-700';
}

function DeltaChip({ deltaAbs, deltaPct }) {
  return (
    <span className={`inline-flex rounded-full px-2 py-1 text-xs ${deltaClass(deltaAbs)}`}>
      {deltaAbs > 0 ? '+' : ''}{currency(deltaAbs)} ({deltaPct > 0 ? '+' : ''}{Number(deltaPct || 0).toFixed(2)}%)
    </span>
  );
}

function WidgetSkeleton({ className = '' }) {
  return <div className={`animate-pulse rounded-2xl border border-slate-200 bg-white p-5 shadow-sm ${className}`} />;
}

function Costs() {
  const [period, setPeriod] = useState('prev_month');
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');
  const [groupBy, setGroupBy] = useState('service');
  const customRangeInvalid = period === 'custom' && customStartDate && customEndDate && customStartDate > customEndDate;
  const customReady = period !== 'custom' || (customStartDate && customEndDate && !customRangeInvalid);

  const range = useMemo(() => {
    if (period === 'custom') {
      if (!customStartDate || !customEndDate) return null;
      return { start: customStartDate, end: customEndDate };
    }
    return getDateRangeForPreset(period);
  }, [period, customStartDate, customEndDate]);

  useEffect(() => {
    if (period !== 'custom') return;
    if (customStartDate && customEndDate) return;
    const now = new Date();
    const end = toIsoDate(now);
    const start = new Date(now);
    start.setDate(start.getDate() - 90);
    setCustomStartDate(toIsoDate(start));
    setCustomEndDate(end);
  }, [period, customStartDate, customEndDate]);

  const loadCostsData = useCallback(async () => {
    if (!range || !customReady) {
      return null;
    }
    const params = { start_date: range.start, end_date: range.end };
    const [summaryRes, breakdownRes, moversRes, resourceRes, serviceRes] = await Promise.all([
      getCostSummary(params),
      getCostBreakdown({ ...params, group_by: groupBy, compare: 'previous', limit: 8, min_share_pct: 0.5 }),
      getCostMovers({ ...params, group_by: 'service', compare: 'previous', direction: 'up', limit: 10 }),
      getCostMovers({ ...params, group_by: 'resource', compare: 'previous', direction: 'both', limit: 10 }),
      getCostBreakdown({ ...params, group_by: 'service', compare: 'previous', limit: 50, min_share_pct: 0 }),
    ]);
    const serviceRows = serviceRes.data?.data?.items || [];
    const dbCosts = {
      oracle_db: { total: serviceRows.find((r) => String(r.name || r.service || '').toLowerCase().includes('oracle'))?.current || 0 },
      mysql: { total: serviceRows.find((r) => String(r.name || r.service || '').toLowerCase().includes('mysql'))?.current || 0 },
      sql_server: { total: serviceRows.find((r) => String(r.name || r.service || '').toLowerCase().includes('sql'))?.current || 0 },
    };
    return {
      summary: summaryRes.data?.data || null,
      breakdown: breakdownRes.data?.data || null,
      serviceMovers: moversRes.data?.data?.items || [],
      resourceMovers: resourceRes.data?.data?.items || [],
      dbCosts,
    };
  }, [customReady, groupBy, range]);

  const {
    data: costsData,
    loading,
    refreshing,
    error,
    isStale,
    savedAt,
    refresh,
    hasData,
  } = useStaleSnapshotQuery({
    cacheKey: `costs:${range?.start || 'none'}:${range?.end || 'none'}:${groupBy}`,
    ttlMs: 60 * 60 * 1000,
    queryFn: loadCostsData,
    dependencies: [range?.start, range?.end, groupBy, customReady],
    fallbackError: 'Failed to load cost analysis',
  });

  const summary = costsData?.summary || null;
  const breakdown = costsData?.breakdown || null;
  const serviceMovers = costsData?.serviceMovers || [];
  const resourceMovers = costsData?.resourceMovers || [];
  const dbCosts = costsData?.dbCosts || null;
  const rows = breakdown?.items || [];
  const empty = Number(summary?.total || 0) === 0;
  const mappingHealth = breakdown?.mapping_health || null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-start justify-between gap-3 md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Cost Analysis</h1>
          <p className="text-sm text-slate-500">Decision-first cost view with deltas and movers</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm shadow-sm"
          >
            <option value="prev_month">Previous Full Month</option>
            <option value="ytd">YTD</option>
            <option value="prev_year">Previous Full Year</option>
            <option value="custom">Custom Range</option>
          </select>
        </div>
      </div>

      <p className="text-xs text-slate-500">Prev Month = last full calendar month, YTD = Jan 1 to today.</p>

      {period === 'custom' && (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <label className="text-sm text-slate-600">
              Start Date
              <input
                type="date"
                value={customStartDate}
                max={toIsoDate(new Date())}
                onChange={(e) => setCustomStartDate(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm"
              />
            </label>
            <label className="text-sm text-slate-600">
              End Date
              <input
                type="date"
                value={customEndDate}
                max={toIsoDate(new Date())}
                onChange={(e) => setCustomEndDate(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm"
              />
            </label>
          </div>
          {!customReady && !customRangeInvalid && <p className="mt-3 text-sm text-amber-700">Set both start and end date to load costs.</p>}
          {customRangeInvalid && <p className="mt-3 text-sm text-rose-700">End date must be on or after start date.</p>}
        </div>
      )}

      {error ? (
        <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-amber-800">
          Showing cached snapshot. Latest refresh failed: {error}
          <button
            type="button"
            onClick={() => refresh()}
            className="ml-3 rounded-lg border border-amber-400 px-2 py-1 text-xs hover:bg-amber-100"
          >
            Retry
          </button>
        </div>
      ) : null}

      <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600">
        <span>{savedAt ? `Snapshot: ${new Date(savedAt).toLocaleString()}` : 'No snapshot yet'}</span>
        <span>{refreshing ? 'Refreshing' : isStale ? 'Stale snapshot' : 'Fresh snapshot'}</span>
      </div>

      {!hasData && loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <WidgetSkeleton className="h-28" />
          <WidgetSkeleton className="h-28" />
          <WidgetSkeleton className="h-28" />
          <WidgetSkeleton className="h-28" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-medium text-slate-600">Period Total</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{currency(summary?.total)}</p>
              <div className="mt-2"><DeltaChip deltaAbs={summary?.delta_abs || 0} deltaPct={summary?.delta_pct || 0} /></div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-medium text-slate-600">Top Driver</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{summary?.top_driver?.entity || 'No data'}</p>
              <p className="mt-1 text-xs text-slate-600">Share {(summary?.top_driver?.share || 0).toFixed(2)}%</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-medium text-slate-600">Biggest Mover</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{summary?.biggest_mover?.entity || 'No data'}</p>
              <div className="mt-2"><DeltaChip deltaAbs={summary?.biggest_mover?.delta_abs || 0} deltaPct={summary?.biggest_mover?.delta_pct || 0} /></div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-medium text-slate-600">{UI_COPY.detection.unallocatedCost}</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{summary?.unallocated?.count || 0}</p>
              <p className="mt-1 text-xs text-slate-600">{(summary?.unallocated?.pct || 0).toFixed(2)}%</p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-medium text-slate-600">Oracle DB</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{currency(dbCosts?.oracle_db?.total)}</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-medium text-slate-600">MySQL</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{currency(dbCosts?.mysql?.total)}</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-medium text-slate-600">SQL Server</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{currency(dbCosts?.sql_server?.total)}</p>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-medium text-slate-600">Breakdown</h3>
              <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1">
                {[
                  ['service', 'Service'],
                  ['compartment', 'Compartment'],
                  ['team', 'Team'],
                  ['app', 'App'],
                  ['env', 'Env'],
                ].map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setGroupBy(value)}
                    className={`rounded-md px-3 py-1 text-xs ${groupBy === value ? 'bg-slate-200 text-slate-900' : 'text-slate-600 hover:bg-slate-100'}`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            {groupBy === 'team' || groupBy === 'app' || groupBy === 'env' ? (
              <div className="mb-3 grid grid-cols-1 gap-2 md:grid-cols-2">
                <div className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-700">
                  Unowned cost: <span className="font-semibold text-slate-900">{currency(mappingHealth?.unowned_cost)}</span>
                </div>
                <div className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-700">
                  Low-confidence cost: <span className="font-semibold text-slate-900">{currency(mappingHealth?.low_confidence_cost)}</span>
                </div>
              </div>
            ) : null}
            {empty || rows.length === 0 ? (
              <p className="text-sm text-slate-500">{UI_COPY.empty.noCostData}</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-600">
                      <th className="py-2 text-left">Entity</th>
                      <th className="py-2 text-right">Current</th>
                      <th className="py-2 text-right">Previous</th>
                      <th className="py-2 text-right">Delta</th>
                      <th className="py-2 text-right">Delta %</th>
                      <th className="py-2 text-right">Share</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr key={row.name} className="border-b border-slate-100">
                        <td className="py-2 text-slate-800">
                          {row.name}
                          {row.name === 'Unallocated' ? (
                            <span className="ml-2 rounded-full bg-rose-50 px-2 py-1 text-[10px] font-medium text-rose-700">
                              {UI_COPY.detection.lowConfidence}
                            </span>
                          ) : null}
                        </td>
                        <td className="py-2 text-right text-slate-900">{currency(row.current)}</td>
                        <td className="py-2 text-right text-slate-700">{currency(row.previous)}</td>
                        <td className="py-2 text-right"><DeltaChip deltaAbs={row.delta_abs} deltaPct={row.delta_pct} /></td>
                        <td className="py-2 text-right text-slate-700">{Number(row.delta_pct || 0).toFixed(2)}%</td>
                        <td className="py-2 text-right text-slate-700">{Number(row.share_pct || 0).toFixed(2)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="mb-3 text-sm font-medium text-slate-600">Top Movers (Services)</h3>
              {serviceMovers.length === 0 ? (
                <p className="text-sm text-slate-500">{UI_COPY.empty.noCostData}</p>
              ) : (
                <div className="space-y-2">
                  {serviceMovers.map((row) => (
                    <div key={row.name} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
                      <span className="text-slate-800">{row.name}</span>
                      <DeltaChip deltaAbs={row.delta_abs} deltaPct={row.delta_pct} />
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="mb-3 text-sm font-medium text-slate-600">Top Resources</h3>
              {resourceMovers.length === 0 ? (
                <p className="text-sm text-slate-500">{UI_COPY.empty.noCostData}</p>
              ) : (
                <div className="space-y-2">
                  {resourceMovers.map((row) => (
                    <div key={`${row.name}-${row.compartment_name || '-'}`} className="rounded-lg bg-slate-50 px-3 py-2 text-sm">
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate text-slate-800">{row.name}</span>
                        <span className="text-slate-700">{currency(row.current)}</span>
                      </div>
                      <div className="mt-1 flex items-center justify-between text-xs text-slate-600">
                        <span>{row.type || 'unknown'} - {row.compartment_name || 'Unknown compartment'}</span>
                        <span>{Number(row.delta_pct || 0).toFixed(2)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default Costs;
