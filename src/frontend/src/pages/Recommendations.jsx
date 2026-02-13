import { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

import { createAction, getMe, recommendationById, recommendationsList, recommendationsSummary } from '../services/api';
import { getDateRangeForPreset } from '../utils/dateRanges';
import { UI_COPY } from '../constants/copy';

function currency(value) {
  return `$${Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function confidenceClass(value) {
  if (value === 'high') return 'bg-emerald-50 text-emerald-700';
  if (value === 'medium') return 'bg-amber-50 text-amber-800';
  return 'bg-slate-100 text-slate-700';
}

function categoryChipClass(value) {
  if (value === 'compute') return 'bg-indigo-50 text-indigo-700';
  if (value === 'storage') return 'bg-sky-50 text-sky-700';
  if (value === 'backup') return 'bg-amber-50 text-amber-800';
  return 'bg-slate-100 text-slate-700';
}

function Recommendations() {
  const period = useMemo(() => getDateRangeForPreset('prev_month'), []);
  const [summary, setSummary] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedId, setExpandedId] = useState('');
  const [expandedData, setExpandedData] = useState(null);
  const [actionModal, setActionModal] = useState(null);
  const [creatingAction, setCreatingAction] = useState(false);
  const [actionError, setActionError] = useState('');
  const [role, setRole] = useState('admin');
  const [demoMode, setDemoMode] = useState(false);

  const [category, setCategory] = useState('');
  const [confidence, setConfidence] = useState('');
  const [team, setTeam] = useState('');
  const [app, setApp] = useState('');
  const [env, setEnv] = useState('');

  const load = async () => {
    try {
      setError('');
      const [summaryRes, listRes] = await Promise.all([
        recommendationsSummary({ start_date: period.start, end_date: period.end }),
        recommendationsList({
          start_date: period.start,
          end_date: period.end,
          category: category || undefined,
          confidence: confidence || undefined,
          team: team || undefined,
          app: app || undefined,
          env: env || undefined,
        }),
      ]);
      setSummary(summaryRes.data?.data || null);
      setItems(listRes.data?.data?.items || []);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load recommendations');
      setSummary(null);
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    getMe()
      .then((res) => {
        setRole(res.data?.data?.role || 'admin');
        setDemoMode(Boolean(res.data?.data?.feature_flags?.enable_demo_mode));
      })
      .catch(() => {
        setRole('admin');
        setDemoMode(false);
      });
  }, [category, confidence, team, app, env]);

  const toggleExpanded = async (recommendationId) => {
    if (expandedId === recommendationId) {
      setExpandedId('');
      setExpandedData(null);
      return;
    }
    setExpandedId(recommendationId);
    try {
      const res = await recommendationById({
        recommendation_id: recommendationId,
        start_date: period.start,
        end_date: period.end,
      });
      setExpandedData(res.data?.data || null);
    } catch {
      setExpandedData(null);
    }
  };

  const uniqueTeams = Array.from(new Set(items.map((i) => i.team).filter(Boolean))).sort();
  const uniqueApps = Array.from(new Set(items.map((i) => i.app).filter(Boolean))).sort();
  const uniqueEnvs = Array.from(new Set(items.map((i) => i.env).filter(Boolean))).sort();

  const openActionModal = (item) => {
    const categoryToAction = {
      storage: 'cleanup',
      backup: 'cleanup',
      compute: 'schedule',
      license: 'notify_only',
    };
    const typeToTarget = {
      unattached_resource: 'volume',
      idle_compute: 'instance',
      oversized_storage: 'volume',
      license_signal: 'policy',
    };
    setActionError('');
    setActionModal({
      recommendation_id: item.recommendation_id,
      source: 'recommendation',
      category: categoryToAction[item.category] || 'notify_only',
      target_type: typeToTarget[item.type] || 'policy',
      risk_level: item.confidence === 'high' ? 'safe' : 'moderate',
      confidence: item.confidence,
      estimated_savings_monthly: item.estimated_savings,
      notes: item.reason,
      dryRun: true,
      target_ref: {
        resource_id: item.resource_ref,
        resource_name: item.resource_name,
        compartment_id: item.compartment_id,
        team: item.team,
        app: item.app,
        env: item.env,
      },
    });
  };

  const submitAction = async () => {
    if (!actionModal) return;
    setCreatingAction(true);
    try {
      await createAction({
        source: actionModal.source,
        category: actionModal.category,
        target_type: actionModal.target_type,
        target_ref: actionModal.target_ref,
        proposed_change: {
          recommendation_id: actionModal.recommendation_id,
          notes: actionModal.notes,
          executor_type:
            actionModal.category === 'notify_only'
              ? 'notify_only'
              : actionModal.category === 'cleanup'
                ? 'cleanup_unattached_volume'
                : actionModal.category === 'tag_fix'
                  ? 'tag_fix'
                  : 'stop_idle_instance',
        },
        estimated_savings_monthly: actionModal.estimated_savings_monthly,
        confidence: actionModal.confidence,
        risk_level: actionModal.risk_level,
        recommendation_id: actionModal.recommendation_id,
        notes: actionModal.notes,
      });
      setActionModal(null);
    } catch (e) {
      setActionError(e?.response?.data?.detail || 'Failed to create action');
    } finally {
      setCreatingAction(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center bg-slate-50">
        <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-slate-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6 bg-slate-50 p-2">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Recommendations</h1>
        <p className="text-sm text-slate-600">Deterministic, explainable optimization actions</p>
      </div>

      {error ? <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-700">{error}</div> : null}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5">
          <p className="text-sm font-medium text-slate-600">Potential Monthly Savings</p>
          <p className="text-2xl font-semibold text-emerald-600">{currency(summary?.totals?.potential_savings_monthly)}</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5">
          <p className="text-sm font-medium text-slate-600">High Confidence Savings</p>
          <p className="text-2xl font-semibold text-emerald-600">{currency(summary?.totals?.high_confidence_savings)}</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5">
          <p className="text-sm font-medium text-slate-600">Recommendation Count</p>
          <p className="text-2xl font-semibold text-slate-900">{Number(summary?.totals?.recommendation_count || 0)}</p>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5">
        <h2 className="text-sm font-medium text-slate-600">Filters</h2>
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-5">
          <select value={category} onChange={(e) => setCategory(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
            <option value="">All Categories</option>
            <option value="compute">Compute</option>
            <option value="storage">Storage</option>
            <option value="backup">Backup</option>
            <option value="license">License</option>
          </select>
          <select value={confidence} onChange={(e) => setConfidence(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
            <option value="">All Confidence</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <select value={team} onChange={(e) => setTeam(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
            <option value="">All Teams</option>
            {uniqueTeams.map((x) => <option key={x} value={x}>{x}</option>)}
          </select>
          <select value={app} onChange={(e) => setApp(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
            <option value="">All Apps</option>
            {uniqueApps.map((x) => <option key={x} value={x}>{x}</option>)}
          </select>
          <select value={env} onChange={(e) => setEnv(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
            <option value="">All Envs</option>
            {uniqueEnvs.map((x) => <option key={x} value={x}>{x}</option>)}
          </select>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5">
        <h2 className="text-sm font-medium text-slate-600">Optimization Opportunities</h2>
        {items.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">{UI_COPY.empty.noOptimizationOpportunities}</p>
        ) : (
          <div className="mt-3 space-y-3">
            {items.map((item) => (
              <div key={item.recommendation_id} className="rounded-xl border border-slate-200 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`rounded-full px-2 py-1 text-xs ${categoryChipClass(item.category)}`}>{item.category}</span>
                      <span className={`rounded-full px-2 py-1 text-xs ${confidenceClass(item.confidence)}`}>{item.confidence}</span>
                    </div>
                    <p className="mt-2 text-sm font-semibold text-slate-900">{item.resource_name}</p>
                    <p className="text-xs text-slate-600">{item.reason}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-600">Estimated Savings</p>
                    <p className="text-lg font-semibold text-emerald-600">{currency(item.estimated_savings)}</p>
                    <button
                      type="button"
                      onClick={() => toggleExpanded(item.recommendation_id)}
                      className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-indigo-700 hover:text-indigo-800"
                    >
                      Why?
                      {expandedId === item.recommendation_id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </button>
                    {role !== 'viewer' && !demoMode ? (
                      <button
                        type="button"
                        onClick={() => openActionModal(item)}
                        className="mt-2 ml-2 inline-flex items-center gap-1 rounded-lg border border-slate-300 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                      >
                        Create Action
                      </button>
                    ) : null}
                  </div>
                </div>

                {expandedId === item.recommendation_id && expandedData ? (
                  <div className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-700">
                    <p className="font-medium text-slate-800">What to do next</p>
                    <ul className="mt-1 list-disc pl-5">
                      {expandedData.next_steps?.map((x) => <li key={x}>{x}</li>)}
                    </ul>
                    <p className="mt-2 font-medium text-slate-800">Cost snapshot</p>
                    <p>
                      Current {currency(expandedData.cost_history_snapshot?.current)} | Previous {currency(expandedData.cost_history_snapshot?.previous)} |
                      Delta {currency(expandedData.cost_history_snapshot?.delta_abs)}
                    </p>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </div>

      {actionModal ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-5 shadow-xl">
            <h3 className="text-base font-semibold text-slate-900">Create Action</h3>
            <p className="text-xs text-slate-600">Review and submit runbook request from recommendation.</p>
            {actionError ? <p className="mt-2 rounded-lg bg-rose-50 p-2 text-xs text-rose-700">{actionError}</p> : null}
            <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
              <select value={actionModal.category} onChange={(e) => setActionModal((x) => ({ ...x, category: e.target.value }))} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
                <option value="cleanup">cleanup</option>
                <option value="schedule">schedule</option>
                <option value="tag_fix">tag_fix</option>
                <option value="notify_only">notify_only</option>
                <option value="resize">resize</option>
              </select>
              <select value={actionModal.target_type} onChange={(e) => setActionModal((x) => ({ ...x, target_type: e.target.value }))} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
                <option value="volume">volume</option>
                <option value="instance">instance</option>
                <option value="backup">backup</option>
                <option value="policy">policy</option>
                <option value="tag">tag</option>
              </select>
              <select value={actionModal.risk_level} onChange={(e) => setActionModal((x) => ({ ...x, risk_level: e.target.value }))} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
                <option value="safe">safe</option>
                <option value="moderate">moderate</option>
                <option value="high">high</option>
              </select>
              <label className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700">
                <input type="checkbox" checked={actionModal.dryRun} onChange={(e) => setActionModal((x) => ({ ...x, dryRun: e.target.checked }))} />
                Dry-run default
              </label>
            </div>
            <textarea
              value={actionModal.notes}
              onChange={(e) => setActionModal((x) => ({ ...x, notes: e.target.value }))}
              className="mt-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              rows={3}
            />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setActionModal(null)} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700">Cancel</button>
              <button type="button" disabled={creatingAction || demoMode} onClick={submitAction} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60">
                {creatingAction ? 'Creating...' : 'Create Action'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default Recommendations;
