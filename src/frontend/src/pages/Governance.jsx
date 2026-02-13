import { useEffect, useMemo, useState } from 'react';
import {
  adminCreateAllocationRule,
  adminDeleteAllocationRule,
  adminGetAllocationRules,
  adminUpdateAllocationRule,
  getTagCoverage,
} from '../services/api';
import { getDateRangeForPreset } from '../utils/dateRanges';
import { UI_COPY } from '../constants/copy';

function pct(value) {
  return `${Number(value || 0).toFixed(2)}%`;
}

function money(value) {
  return `$${Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function barWidth(value) {
  return `${Math.max(0, Math.min(100, Number(value || 0)))}%`;
}

const EMPTY_RULE = {
  name: '',
  is_enabled: true,
  match_type: 'tag',
  match_expression: '',
  set_env: '',
  set_team: '',
  set_app: '',
  priority: 100,
};

function Governance() {
  const range = useMemo(() => getDateRangeForPreset('prev_month'), []);
  const [coverage, setCoverage] = useState(null);
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(EMPTY_RULE);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState('');

  const loadAll = async () => {
    setLoading(true);
    setError('');
    try {
      const [covRes, rulesRes] = await Promise.all([
        getTagCoverage({ start_date: range.start, end_date: range.end }),
        adminGetAllocationRules(),
      ]);
      setCoverage(covRes.data?.data || null);
      setRules(rulesRes.data?.data || []);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load governance data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const onSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const payload = {
        ...form,
        set_env: form.set_env || null,
        set_team: form.set_team || null,
        set_app: form.set_app || null,
        priority: Number(form.priority || 100),
      };
      if (editingId) {
        await adminUpdateAllocationRule(editingId, payload);
      } else {
        await adminCreateAllocationRule(payload);
      }
      setForm(EMPTY_RULE);
      setEditingId(null);
      await loadAll();
    } catch (e2) {
      setError(e2?.response?.data?.detail || 'Failed to save rule');
    } finally {
      setSaving(false);
    }
  };

  const onEdit = (r) => {
    setEditingId(r.id);
    setForm({
      name: r.name || '',
      is_enabled: !!r.is_enabled,
      match_type: r.match_type || 'tag',
      match_expression: r.match_expression || '',
      set_env: r.set_env || '',
      set_team: r.set_team || '',
      set_app: r.set_app || '',
      priority: r.priority ?? 100,
    });
  };

  const onDelete = async (id) => {
    setSaving(true);
    try {
      await adminDeleteAllocationRule(id);
      if (editingId === id) {
        setEditingId(null);
        setForm(EMPTY_RULE);
      }
      await loadAll();
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-slate-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Governance</h1>
        <p className="text-sm text-slate-600">Allocation ownership and tag-coverage controls</p>
      </div>

      {error ? <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-700">{error}</div> : null}

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-medium text-slate-600">Tag Coverage</h2>
        <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs text-slate-600">Unowned Cost</p>
            <p className="mt-1 text-xl font-semibold text-slate-900">{money(coverage?.unowned_cost?.current)}</p>
            <p className="text-xs text-slate-600">Prev {money(coverage?.unowned_cost?.previous)}</p>
          </div>
          {[
            ['Environment', coverage?.coverage?.env_pct],
            ['Team', coverage?.coverage?.team_pct],
            ['Application', coverage?.coverage?.app_pct],
          ].map(([label, value]) => (
            <div key={label} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs text-slate-600">{label}</p>
              <p className="mt-1 text-xl font-semibold text-slate-900">{pct(value)}</p>
              <div className="mt-2 h-2 w-full rounded bg-slate-200">
                <div className="h-2 rounded bg-indigo-600" style={{ width: barWidth(value) }} />
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <h3 className="text-xs font-medium text-slate-600">Top Missing Compartments</h3>
            <div className="mt-2 space-y-2">
              {(coverage?.top_missing_compartments || []).map((item) => (
                <div key={item.name} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
                  <span>{item.name}</span>
                  <span>{money(item.cost)}</span>
                </div>
              ))}
              {(coverage?.top_missing_compartments || []).length === 0 ? <p className="text-sm text-slate-500">{UI_COPY.empty.noCostData}</p> : null}
            </div>
          </div>
          <div>
            <h3 className="text-xs font-medium text-slate-600">Top Missing Services</h3>
            <div className="mt-2 space-y-2">
              {(coverage?.top_missing_services || []).map((item) => (
                <div key={item.name} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
                  <span>{item.name}</span>
                  <span>{money(item.cost)}</span>
                </div>
              ))}
              {(coverage?.top_missing_services || []).length === 0 ? <p className="text-sm text-slate-500">{UI_COPY.empty.noCostData}</p> : null}
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-medium text-slate-600">Allocation Rules</h2>
        <form onSubmit={onSubmit} className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-4">
          <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Rule name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <select className="rounded-lg border border-slate-300 px-3 py-2 text-sm" value={form.match_type} onChange={(e) => setForm({ ...form, match_type: e.target.value })}>
            <option value="tag">tag</option>
            <option value="compartment">compartment</option>
            <option value="resource_name">resource_name</option>
            <option value="sku">sku</option>
            <option value="image_name">image_name</option>
          </select>
          <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="match expression" value={form.match_expression} onChange={(e) => setForm({ ...form, match_expression: e.target.value })} required />
          <input type="number" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="priority" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })} />
          <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="set env" value={form.set_env} onChange={(e) => setForm({ ...form, set_env: e.target.value })} />
          <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="set team" value={form.set_team} onChange={(e) => setForm({ ...form, set_team: e.target.value })} />
          <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="set app" value={form.set_app} onChange={(e) => setForm({ ...form, set_app: e.target.value })} />
          <label className="flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm">
            <input type="checkbox" checked={form.is_enabled} onChange={(e) => setForm({ ...form, is_enabled: e.target.checked })} />
            Enabled
          </label>
          <div className="md:col-span-4 flex items-center gap-2">
            <button type="submit" disabled={saving} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
              {editingId ? 'Update Rule' : 'Create Rule'}
            </button>
            {editingId ? (
              <button type="button" onClick={() => { setEditingId(null); setForm(EMPTY_RULE); }} className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700">
                Cancel Edit
              </button>
            ) : null}
          </div>
        </form>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-600">
                <th className="py-2 text-left">Name</th>
                <th className="py-2 text-left">Match</th>
                <th className="py-2 text-left">Sets</th>
                <th className="py-2 text-right">Priority</th>
                <th className="py-2 text-left">Enabled</th>
                <th className="py-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id} className="border-b border-slate-100">
                  <td className="py-2">{r.name}</td>
                  <td className="py-2">{r.match_type}: {r.match_expression}</td>
                  <td className="py-2">env={r.set_env || '-'} team={r.set_team || '-'} app={r.set_app || '-'}</td>
                  <td className="py-2 text-right">{r.priority}</td>
                  <td className="py-2">{r.is_enabled ? 'Yes' : 'No'}</td>
                  <td className="py-2">
                    <div className="flex items-center gap-2">
                      <button type="button" className="rounded border border-slate-300 px-2 py-1 text-xs" onClick={() => onEdit(r)}>Edit</button>
                      <button type="button" className="rounded border border-rose-300 px-2 py-1 text-xs text-rose-700" onClick={() => onDelete(r.id)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
              {rules.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-3 text-slate-500">{UI_COPY.empty.noCostData}</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default Governance;

