import { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';

import { costsBreakdownV2, costsMoversV2, dashboardSummaryV2, getMe } from '../services/api';
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
  return <div className={`bg-white border border-slate-200 rounded-2xl shadow-sm p-5 ${muted ? 'opacity-70' : ''}`}>{children}</div>;
}

function EmptyState({ text = 'No cost data available for this range' }) {
  return <p className="text-sm text-slate-500">{text}</p>;
}

function WidgetSkeleton({ className = '' }) {
  return <div className={`animate-pulse rounded-2xl border border-slate-200 bg-white p-5 ${className}`} />;
}

function TopServiceRow({ row }) {
  const width = Math.max(2, Math.min(100, Number(row.share_pct || 0)));
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="truncate text-sm text-slate-800">{row.name}</span>
          <span className="bg-slate-100 text-slate-700 rounded-full px-2 py-1 text-xs">{Number(row.share_pct || 0).toFixed(2)}%</span>
        </div>
        <span className="text-sm font-medium text-slate-900">{currency(row.current)}</span>
      </div>
      <div className="h-2 w-full rounded bg-slate-200">
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
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5">
      <p className="text-sm font-medium text-slate-600">{item.compartment_name}</p>
      <p className="mt-1 text-xl font-semibold text-slate-900">{currency(item.totals?.current)}</p>
      <div className="mt-2">
        <DeltaChip deltaAbs={item.totals?.delta_abs || 0} deltaPct={item.totals?.delta_pct || 0} />
      </div>
      <div className="mt-3 space-y-2">
        {(item.top_services || []).map((svc) => {
          const width = Math.max(2, Math.min(100, Number(svc.share_pct || 0)));
          return (
            <div key={`${item.compartment_id}-${svc.name}`}>
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="truncate text-sm text-slate-700">{svc.name}</span>
                <span className="bg-slate-100 text-slate-700 rounded-full px-2 py-1 text-xs">{Number(svc.share_pct || 0).toFixed(2)}%</span>
              </div>
              <div className="h-2 w-full rounded bg-slate-200">
                <div className="h-2 rounded bg-indigo-500" style={{ width: `${width}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Toggle({ options, value, onChange }) {
  return (
    <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`rounded-md px-3 py-1 text-xs ${value === opt.value ? 'bg-slate-200 text-slate-900' : 'text-slate-600 hover:bg-slate-100'}`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

function Dashboard({ persona = 'Executive' }) {
  const period = useMemo(() => getDateRangeForPreset('prev_month'), []);

  const [moversGroupBy, setMoversGroupBy] = useState('service');
  const [moversDirection, setMoversDirection] = useState('up');
  const [executiveView, setExecutiveView] = useState(false);
  const [productState, setProductState] = useState(null);
  const [demoMode, setDemoMode] = useState(false);

  const loadDashboardData = useCallback(async () => {
    const summaryRes = await dashboardSummaryV2({
      start_date: period.start,
      end_date: period.end,
      compare: 'previous',
    });

    const [breakdownRes, moversRes] = await Promise.all([
      costsBreakdownV2({
        group_by: 'service',
        start_date: period.start,
        end_date: period.end,
        compare: 'previous',
        limit: 8,
        min_share_pct: 0.5,
      }),
      costsMoversV2({
        group_by: moversGroupBy,
        start_date: period.start,
        end_date: period.end,
        compare: 'previous',
        limit: 10,
        direction: moversDirection,
      }),
    ]);

    return {
      summary: summaryRes.data?.data || null,
      breakdown: breakdownRes.data?.data || null,
      movers: moversRes.data?.data || null,
    };
  }, [period.end, period.start, moversDirection, moversGroupBy]);

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
    cacheKey: `dashboard:${period.start}:${period.end}:${moversGroupBy}:${moversDirection}`,
    ttlMs: 5 * 60 * 1000,
    queryFn: loadDashboardData,
    dependencies: [period.start, period.end, moversGroupBy, moversDirection],
    fallbackError: 'Failed to load dashboard data',
  });

  useEffect(() => {
    getMe()
      .then((res) => {
        const data = res?.data?.data || {};
        setProductState(data.product_state || null);
        setDemoMode(Boolean(data?.feature_flags?.enable_demo_mode));
      })
      .catch(() => {
        setProductState(null);
        setDemoMode(false);
      });
  }, []);

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

  return (
    <div className="min-h-full space-y-6 bg-slate-50 p-1">
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
          <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-600">
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
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm hover:bg-slate-100 disabled:opacity-60"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
        <button
          type="button"
          onClick={() => setExecutiveView((v) => !v)}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm hover:bg-slate-100"
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
        <SectionCard muted={isZeroTotal}>
          <p className="text-sm font-medium text-slate-600">Total Spend</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">{currency(totals.current)}</p>
          <p className="mt-1 text-xs text-slate-600">Daily {currency(totalDaily)} | Previous {currency(totals.previous)}</p>
          <div className="mt-2"><DeltaChip deltaAbs={totals.delta_abs} deltaPct={totals.delta_pct} /></div>
        </SectionCard>
        )}
        {!summary && loading ? <WidgetSkeleton className="h-28" /> : (
        <SectionCard muted={isZeroTotal}>
          <p className="text-sm font-medium text-slate-600">Top Driver</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">{topDriver.group || 'No data'}</p>
          <p className="mt-1 text-xs text-slate-600">{currency(topDriver.current)} | Share {Number(topDriver.share_pct || 0).toFixed(2)}%</p>
          <div className="mt-2"><DeltaChip deltaAbs={topDriver.delta_abs} deltaPct={topDriver.delta_pct} /></div>
        </SectionCard>
        )}
        {!summary && loading ? <WidgetSkeleton className="h-28" /> : (
        <SectionCard muted={isZeroTotal}>
          <p className="text-sm font-medium text-slate-600">Biggest Mover</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">{biggestMover.entity_name || 'No data'}</p>
          <p className="mt-1 text-xs text-slate-600">{biggestMover.entity_type || 'service'}</p>
          <div className="mt-2"><DeltaChip deltaAbs={biggestMover.delta_abs} deltaPct={biggestMover.delta_pct} /></div>
        </SectionCard>
        )}
        {!summary && loading ? <WidgetSkeleton className="h-28" /> : (
        <SectionCard muted={isZeroTotal}>
          <p className="text-sm font-medium text-slate-600">Mapping Health</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">{Number(mapping.unallocated_pct || 0).toFixed(2)}%</p>
          <p className="mt-1 text-xs text-slate-600">Low confidence: {mapping.low_confidence_count || 0}</p>
          <p className="mt-2 text-xs text-slate-600" title={UI_COPY.detection.notDetectedReason}>F5 / Palo / Forti: {UI_COPY.detection.notDetected}</p>
        </SectionCard>
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
        <SectionCard muted={isZeroTotal}>
          <p className="text-sm font-medium text-slate-600">Windows</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">{currency(licenses.windows?.monthly_cost)}</p>
          <p className="mt-1 text-xs text-slate-600">Daily {currency(licenses.windows?.daily_estimate)}</p>
          <div className="mt-2"><DeltaChip deltaAbs={licenses.windows?.delta_abs || 0} deltaPct={0} compact /></div>
        </SectionCard>
        <SectionCard muted={isZeroTotal}>
          <p className="text-sm font-medium text-slate-600">SQL Server</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">{currency(licenses.sql_server?.monthly_cost)}</p>
          <p className="mt-1 text-xs text-slate-600">Daily {currency(licenses.sql_server?.daily_estimate)}</p>
          <div className="mt-2"><DeltaChip deltaAbs={licenses.sql_server?.delta_abs || 0} deltaPct={0} compact /></div>
        </SectionCard>
        <SectionCard muted={isZeroTotal}>
          <p className="text-sm font-medium text-slate-600">Oracle OS</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">{currency(licenses.oracle_os?.monthly_cost)}</p>
          <p className="mt-1 text-xs text-slate-600">Daily {currency(licenses.oracle_os?.daily_estimate)}</p>
          <div className="mt-2"><DeltaChip deltaAbs={licenses.oracle_os?.delta_abs || 0} deltaPct={0} compact /></div>
        </SectionCard>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <SectionCard muted={isZeroTotal}>
          <p className="text-sm font-medium text-slate-600">Unattached Volumes</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">{storage.unattached_volumes?.count || 0}</p>
          <p className="mt-1 text-xs text-slate-600">Monthly {currency(storage.unattached_volumes?.monthly_cost)}</p>
          <p className="text-xs text-slate-600">Daily {currency((storage.unattached_volumes?.monthly_cost || 0) / days)}</p>
        </SectionCard>
        <SectionCard muted={isZeroTotal}>
          <p className="text-sm font-medium text-slate-600">Backups</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">{storage.backups?.count || 0}</p>
          <p className="mt-1 text-xs text-slate-600">Monthly {currency(storage.backups?.monthly_cost)}</p>
          <p className="text-xs text-slate-600">Daily {currency((storage.backups?.monthly_cost || 0) / days)}</p>
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
                <tr className="border-b border-slate-200 text-slate-600">
                  <th className="py-2 text-left">Entity</th>
                  <th className="py-2 text-right">Current</th>
                  <th className="py-2 text-right">Previous</th>
                  <th className="py-2 text-right">Delta Cost</th>
                  <th className="py-2 text-right">Delta %</th>
                </tr>
              </thead>
              <tbody>
                {moversItems.map((item) => (
                  <tr key={item.name} className="border-b border-slate-100">
                    <td className="py-2 text-slate-900">{item.name}</td>
                    <td className="py-2 text-right text-slate-900">{currency(item.current)}</td>
                    <td className="py-2 text-right text-slate-700">{currency(item.previous)}</td>
                    <td className="py-2 text-right"><DeltaChip deltaAbs={item.delta_abs} deltaPct={item.delta_pct} compact /></td>
                    <td className="py-2 text-right text-xs text-slate-600">{Number(item.delta_pct || 0).toFixed(2)}%</td>
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
