import { Fragment, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Plus, Save, Trash2 } from 'lucide-react';

import { budgetHistory, budgetStatus, createAction, createBudget, deleteBudget, getMe, listBudgets, updateBudget } from '../services/api';

function money(v) {
  return `$${Number(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function statusClass(utilization, breached) {
  if (breached || utilization >= 100) return 'bg-rose-50 text-rose-700';
  if (utilization >= 75) return 'bg-amber-50 text-amber-800';
  return 'bg-emerald-50 text-emerald-700';
}

const EMPTY_FORM = {
  name: '',
  scope_type: 'global',
  scope_value: 'global',
  include_children: false,
  period: 'monthly',
  limit_amount: '',
  currency: 'USD',
  alert_thresholds: '50,75,90,100',
  compare_mode: 'actual',
  enabled: true,
  notifications_enabled: false,
  owner: '',
};

function Budget() {
  const [budgets, setBudgets] = useState([]);
  const [statuses, setStatuses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [editingId, setEditingId] = useState('');
  const [form, setForm] = useState(EMPTY_FORM);
  const [expandedBudgetId, setExpandedBudgetId] = useState('');
  const [historyRows, setHistoryRows] = useState([]);
  const [role, setRole] = useState('admin');
  const [demoMode, setDemoMode] = useState(false);

  const statusById = useMemo(
    () =>
      Object.fromEntries((statuses || []).map((s) => [s.budget_id, s])),
    [statuses],
  );

  const load = async () => {
    try {
      setError('');
      const [b, s] = await Promise.all([listBudgets(), budgetStatus()]);
      setBudgets(b.data?.data || []);
      setStatuses(s.data?.data || []);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load budgets');
      setBudgets([]);
      setStatuses([]);
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
  }, []);

  const resetForm = () => {
    setEditingId('');
    setForm(EMPTY_FORM);
  };

  const submit = async () => {
    try {
      setSaving(true);
      const payload = {
        ...form,
        scope_value: form.scope_type === 'global' ? 'global' : form.scope_value,
        limit_amount: Number(form.limit_amount || 0),
        alert_thresholds: String(form.alert_thresholds || '50,75,90,100')
          .split(',')
          .map((x) => Number(x.trim()))
          .filter((x) => Number.isFinite(x)),
      };
      if (!payload.name || !payload.owner || !payload.limit_amount) {
        setError('Name, owner, and limit amount are required');
        return;
      }
      if (editingId) {
        await updateBudget(editingId, payload);
      } else {
        await createBudget(payload);
      }
      resetForm();
      await load();
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to save budget');
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (row) => {
    setEditingId(row.budget_id);
    setForm({
      name: row.name,
      scope_type: row.scope_type,
      scope_value: row.scope_value,
      include_children: Boolean(row.include_children),
      period: row.period,
      limit_amount: row.limit_amount,
      currency: row.currency,
      alert_thresholds: (row.alert_thresholds || [50, 75, 90, 100]).join(','),
      compare_mode: row.compare_mode,
      enabled: Boolean(row.enabled),
      notifications_enabled: Boolean(row.notifications_enabled),
      owner: row.owner,
    });
  };

  const toggleEnabled = async (row, enabled) => {
    try {
      await updateBudget(row.budget_id, {
        ...row,
        enabled,
      });
      await load();
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to update budget');
    }
  };

  const toggleDetails = async (budgetId) => {
    if (expandedBudgetId === budgetId) {
      setExpandedBudgetId('');
      setHistoryRows([]);
      return;
    }
    setExpandedBudgetId(budgetId);
    try {
      const res = await budgetHistory(budgetId);
      setHistoryRows(res.data?.data || []);
    } catch {
      setHistoryRows([]);
    }
  };

  const remove = async (budgetId) => {
    try {
      await deleteBudget(budgetId);
      if (editingId === budgetId) resetForm();
      await load();
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to delete budget');
    }
  };

  const createActionFromBudget = async (budget, st) => {
    try {
      await createAction({
        source: 'budget_alert',
        category: 'notify_only',
        target_type: 'policy',
        target_ref: {
          budget_id: budget.budget_id,
          scope_type: budget.scope_type,
          scope_value: budget.scope_value,
        },
        proposed_change: {
          executor_type: 'notify_only',
          notes: st?.explanation || 'Investigate budget risk',
        },
        estimated_savings_monthly: 0,
        confidence: 'medium',
        risk_level: 'safe',
        budget_alert_id: st?.latest_threshold_crossed || null,
      });
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to create action from budget');
    }
  };

  return (
    <div className="space-y-6 bg-slate-50 p-2">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Budgets</h1>
        <p className="text-sm text-slate-500">Ownership-based guardrails with clear risk explanations</p>
      </div>

      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-700">{error}</div>
      ) : null}

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5">
        <div className="mb-3 flex items-center gap-2">
          <Plus size={16} className="text-slate-600" />
          <h2 className="text-sm font-medium text-slate-600">{editingId ? 'Edit Budget' : 'Create Budget'}</h2>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <input
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder="Budget name"
          />
          <select
            value={form.scope_type}
            onChange={(e) => setForm((f) => ({ ...f, scope_type: e.target.value, scope_value: e.target.value === 'global' ? 'global' : '' }))}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="global">Global</option>
            <option value="compartment">Compartment</option>
            <option value="team">Team</option>
            <option value="app">App</option>
            <option value="env">Env</option>
          </select>
          <input
            value={form.scope_value}
            disabled={form.scope_type === 'global'}
            onChange={(e) => setForm((f) => ({ ...f, scope_value: e.target.value }))}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100"
            placeholder="Scope value"
          />
          <input
            value={form.owner}
            onChange={(e) => setForm((f) => ({ ...f, owner: e.target.value }))}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder="Owner email/team"
          />
          <input
            type="number"
            value={form.limit_amount}
            onChange={(e) => setForm((f) => ({ ...f, limit_amount: e.target.value }))}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder="Budget limit"
          />
          <select
            value={form.currency}
            onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value }))}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="USD">USD</option>
            <option value="SAR">SAR</option>
          </select>
          <input
            value={form.alert_thresholds}
            onChange={(e) => setForm((f) => ({ ...f, alert_thresholds: e.target.value }))}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder="Thresholds: 50,75,90,100"
          />
          <select
            value={form.compare_mode}
            onChange={(e) => setForm((f) => ({ ...f, compare_mode: e.target.value }))}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="actual">actual</option>
            <option value="forecast">forecast</option>
          </select>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <label className="inline-flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.include_children}
              onChange={(e) => setForm((f) => ({ ...f, include_children: e.target.checked }))}
              disabled={form.scope_type !== 'compartment'}
            />
            Include children
          </label>
          <label className="inline-flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(e) => setForm((f) => ({ ...f, enabled: e.target.checked }))}
            />
            Enabled
          </label>
          <label className="inline-flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.notifications_enabled}
              onChange={(e) => setForm((f) => ({ ...f, notifications_enabled: e.target.checked }))}
            />
            Notifications enabled
          </label>
          <button
            type="button"
            onClick={submit}
            disabled={saving || demoMode}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            <Save size={14} />
            {saving ? 'Saving...' : editingId ? 'Update budget' : 'Create budget'}
          </button>
          {editingId ? (
            <button type="button" onClick={resetForm} className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700">
              Cancel edit
            </button>
          ) : null}
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5">
        <h2 className="text-sm font-medium text-slate-600">Budget List</h2>
        {loading ? (
          <div className="mt-3 text-sm text-slate-500">Loading...</div>
        ) : budgets.length === 0 ? (
          <div className="mt-3 text-sm text-slate-500">No budgets configured yet.</div>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-slate-600">
                  <th className="py-2 text-left">Budget</th>
                  <th className="py-2 text-left">Scope</th>
                  <th className="py-2 text-right">Limit</th>
                  <th className="py-2 text-right">Current</th>
                  <th className="py-2 text-right">Utilization</th>
                  <th className="py-2 text-left">Status</th>
                  <th className="py-2 text-left">Why at risk</th>
                  <th className="py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {budgets.map((b) => {
                  const st = statusById[b.budget_id];
                  const utilization = Number(st?.utilization_pct || 0);
                  const forecastBreach = Number(st?.forecast_end_of_month || 0) >= Number(st?.budget_limit || b.limit_amount || 0);
                  return (
                    <Fragment key={b.budget_id}>
                      <tr className="border-b border-slate-100">
                        <td className="py-2">
                          <p className="font-medium text-slate-900">{b.name}</p>
                          <p className="text-xs text-slate-500">{b.owner}</p>
                        </td>
                        <td className="py-2 text-slate-700">
                          {b.scope_type}: {b.scope_value}
                        </td>
                        <td className="py-2 text-right text-slate-900">{money(b.limit_amount)}</td>
                        <td className="py-2 text-right text-slate-900">{money(st?.current_spend || 0)}</td>
                        <td className="py-2 text-right text-slate-900">
                          {utilization.toFixed(2)}%
                          <div className="mt-1 h-2 w-24 rounded bg-slate-200">
                            <div
                              className={`h-2 rounded ${utilization >= 100 || forecastBreach ? 'bg-rose-500' : utilization >= 75 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                              style={{ width: `${Math.min(utilization, 100)}%` }}
                            />
                          </div>
                        </td>
                        <td className="py-2">
                          <span className={`rounded-full px-2 py-1 text-xs ${statusClass(utilization, forecastBreach)}`}>
                            {utilization >= 100 || forecastBreach ? 'Red' : utilization >= 75 ? 'Amber' : 'Green'}
                          </span>
                        </td>
                        <td className="py-2 text-xs text-slate-600">
                          {st?.explanation || 'No evaluation yet'}
                          {forecastBreach ? (
                            <div className="mt-1 inline-flex items-center gap-1 text-amber-700">
                              <AlertTriangle size={12} />
                              Forecast breach before month end
                            </div>
                          ) : null}
                        </td>
                        <td className="py-2 text-right">
                          <div className="inline-flex gap-2">
                            <button type="button" disabled={demoMode} onClick={() => startEdit(b)} className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 disabled:opacity-60">
                              Edit
                            </button>
                            <button type="button" onClick={() => toggleDetails(b.budget_id)} className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700">
                              {expandedBudgetId === b.budget_id ? 'Hide' : 'Details'}
                            </button>
                            <button
                              type="button"
                              disabled={demoMode}
                              onClick={() => toggleEnabled(b, !b.enabled)}
                              className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 disabled:opacity-60"
                            >
                              {b.enabled ? 'Disable' : 'Enable'}
                            </button>
                            {role !== 'viewer' && !demoMode ? (
                              <button
                                type="button"
                                onClick={() => createActionFromBudget(b, st)}
                                className="rounded border border-indigo-300 px-2 py-1 text-xs text-indigo-700"
                              >
                                Create Action
                              </button>
                            ) : null}
                            <button type="button" disabled={demoMode} onClick={() => remove(b.budget_id)} className="rounded border border-rose-300 px-2 py-1 text-xs text-rose-700 disabled:opacity-60">
                              <Trash2 size={12} />
                            </button>
                          </div>
                        </td>
                      </tr>
                      {expandedBudgetId === b.budget_id ? (
                        <tr>
                          <td colSpan={8} className="bg-slate-50 px-3 py-3">
                            <div className="space-y-2">
                              <p className="text-xs font-medium text-slate-700">Forecast narrative</p>
                              <p className="text-xs text-slate-600">{st?.narrative || 'No narrative available.'}</p>
                              <p className="text-xs font-medium text-slate-700">History snapshots</p>
                              {historyRows.length === 0 ? (
                                <p className="text-xs text-slate-500">No history snapshots yet.</p>
                              ) : (
                                <div className="overflow-x-auto">
                                  <table className="w-full text-xs">
                                    <thead>
                                      <tr className="text-slate-600">
                                        <th className="py-1 text-left">Date</th>
                                        <th className="py-1 text-right">Spend</th>
                                        <th className="py-1 text-right">Utilization</th>
                                        <th className="py-1 text-right">Forecast</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {historyRows.map((h) => (
                                        <tr key={`${b.budget_id}-${h.snapshot_date}`} className="border-t border-slate-200">
                                          <td className="py-1 text-slate-700">{h.snapshot_date}</td>
                                          <td className="py-1 text-right text-slate-700">{money(h.current_spend)}</td>
                                          <td className="py-1 text-right text-slate-700">{Number(h.utilization_pct || 0).toFixed(2)}%</td>
                                          <td className="py-1 text-right text-slate-700">{money(h.forecast_end_of_month)}</td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default Budget;
