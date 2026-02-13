import { useEffect, useMemo, useState } from 'react';

import { approveAction, getAction, getMe, listActions, rejectAction, rollbackAction, runAction } from '../services/api';

function statusChipClass(status) {
  if (status === 'pending_approval') return 'bg-amber-50 text-amber-800';
  if (status === 'approved') return 'bg-indigo-50 text-indigo-700';
  if (status === 'running' || status === 'queued') return 'bg-sky-50 text-sky-700';
  if (status === 'succeeded' || status === 'rolled_back') return 'bg-emerald-50 text-emerald-700';
  if (status === 'failed' || status === 'rejected') return 'bg-rose-50 text-rose-700';
  return 'bg-slate-100 text-slate-700';
}

function currency(v) {
  return `$${Number(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function Actions() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [category, setCategory] = useState('');
  const [selectedId, setSelectedId] = useState('');
  const [selected, setSelected] = useState(null);
  const [opBusy, setOpBusy] = useState(false);
  const [dryRun, setDryRun] = useState(true);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [runOutput, setRunOutput] = useState('');
  const [me, setMe] = useState({ role: 'admin', feature_flags: {} });
  const demoMode = Boolean(me.feature_flags?.enable_demo_mode);

  const load = async () => {
    try {
      setError('');
      const response = await listActions({ status: status || undefined, category: category || undefined });
      setRows(response.data?.data?.items || []);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load actions');
      setRows([]);
    } finally {
      setLoading(false);
    }
  };

  const loadDetails = async (actionId) => {
    try {
      const response = await getAction(actionId);
      setSelected(response.data?.data || null);
      setSelectedId(actionId);
    } catch {
      setSelected(null);
      setSelectedId('');
    }
  };

  useEffect(() => {
    load();
    getMe().then((res) => setMe(res.data?.data || { role: 'admin', feature_flags: {} })).catch(() => setMe({ role: 'admin', feature_flags: {} }));
  }, [status, category]);

  const canRollback = useMemo(() => selected?.action?.status === 'succeeded', [selected]);

  const doApprove = async () => {
    if (!selectedId) return;
    setOpBusy(true);
    try {
      await approveAction(selectedId, { message: 'Approved from UI' });
      await load();
      await loadDetails(selectedId);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Approve failed');
    } finally {
      setOpBusy(false);
    }
  };

  const doReject = async () => {
    if (!selectedId) return;
    setOpBusy(true);
    try {
      await rejectAction(selectedId, { message: 'Rejected from UI' });
      await load();
      await loadDetails(selectedId);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Reject failed');
    } finally {
      setOpBusy(false);
    }
  };

  const doRun = async () => {
    if (!selectedId) return;
    setOpBusy(true);
    setRunOutput('');
    try {
      const response = await runAction(selectedId, { dry_run: dryRun, confirm_delete: confirmDelete });
      setRunOutput(JSON.stringify(response.data?.data?.result || {}, null, 2));
      await load();
      await loadDetails(selectedId);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Run failed');
    } finally {
      setOpBusy(false);
    }
  };

  const doRollback = async () => {
    if (!selectedId) return;
    setOpBusy(true);
    try {
      const response = await rollbackAction(selectedId, { dry_run: dryRun, message: 'Rollback requested from UI' });
      setRunOutput(JSON.stringify(response.data?.data?.result || {}, null, 2));
      await load();
      await loadDetails(selectedId);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Rollback failed');
    } finally {
      setOpBusy(false);
    }
  };

  const canMutate = (me.role === 'admin' || me.role === 'finops') && !demoMode;
  const canDestructive = me.role === 'admin' && me.feature_flags?.enable_destructive_actions;

  return (
    <div className="space-y-6 bg-slate-50 p-2">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Actions</h1>
        <p className="text-sm text-slate-600">Approval-gated runbook execution with full audit timeline</p>
      </div>

      {demoMode ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-700">
          Demo mode is enabled. Actions are read-only and execution is blocked.
        </div>
      ) : null}

      {error ? <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-700">{error}</div> : null}

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5">
        <h2 className="text-sm font-medium text-slate-600">Filters</h2>
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
            <option value="">All Status</option>
            <option value="pending_approval">pending_approval</option>
            <option value="approved">approved</option>
            <option value="running">running</option>
            <option value="succeeded">succeeded</option>
            <option value="failed">failed</option>
            <option value="rolled_back">rolled_back</option>
          </select>
          <select value={category} onChange={(e) => setCategory(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
            <option value="">All Category</option>
            <option value="cleanup">cleanup</option>
            <option value="resize">resize</option>
            <option value="schedule">schedule</option>
            <option value="tag_fix">tag_fix</option>
            <option value="notify_only">notify_only</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5">
          <h2 className="text-sm font-medium text-slate-600">Action Requests</h2>
          {loading ? (
            <p className="mt-3 text-sm text-slate-500">Loading...</p>
          ) : rows.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">No actions found.</p>
          ) : (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-600">
                    <th className="py-2 text-left">Action</th>
                    <th className="py-2 text-left">Category</th>
                    <th className="py-2 text-left">Status</th>
                    <th className="py-2 text-right">Savings</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr
                      key={row.action_id}
                      className={`cursor-pointer border-b border-slate-100 ${selectedId === row.action_id ? 'bg-slate-50' : ''}`}
                      onClick={() => loadDetails(row.action_id)}
                    >
                      <td className="py-2 text-slate-900">{row.action_id.slice(0, 8)}</td>
                      <td className="py-2 text-slate-700">{row.category}</td>
                      <td className="py-2">
                        <span className={`rounded-full px-2 py-1 text-xs ${statusChipClass(row.status)}`}>{row.status}</span>
                      </td>
                      <td className="py-2 text-right text-slate-900">{currency(row.estimated_savings_monthly)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5">
          <h2 className="text-sm font-medium text-slate-600">Action Detail</h2>
          {!selected ? (
            <p className="mt-3 text-sm text-slate-500">Select an action to view timeline and runbook output.</p>
          ) : (
            <div className="mt-3 space-y-3 text-sm">
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-slate-900"><span className="text-slate-500">What:</span> {selected.action.category} on {selected.action.target_type}</p>
                <p className="text-slate-900"><span className="text-slate-500">Why:</span> {selected.action.proposed_change?.notes || 'No notes provided'}</p>
                <p className="text-slate-900"><span className="text-slate-500">Risk:</span> {selected.action.risk_level}</p>
                <p className="text-slate-900"><span className="text-slate-500">Estimated savings:</span> {currency(selected.action.estimated_savings_monthly)}</p>
              </div>

              <div className="rounded-lg border border-slate-200 p-3">
                <p className="mb-2 text-xs font-medium text-slate-600">Execution controls</p>
                <label className="mr-4 inline-flex items-center gap-2 text-xs text-slate-700">
                  <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />
                  Dry run
                </label>
                <label className="inline-flex items-center gap-2 text-xs text-slate-700">
                  <input type="checkbox" checked={confirmDelete} onChange={(e) => setConfirmDelete(e.target.checked)} />
                  confirm_delete
                </label>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button type="button" disabled={opBusy || !canMutate} onClick={doApprove} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-60">Approve</button>
                  <button type="button" disabled={opBusy || !canMutate} onClick={doReject} className="rounded-lg border border-rose-300 px-3 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-60">Reject</button>
                  <button type="button" disabled={opBusy || !canMutate || (!canDestructive && !dryRun)} onClick={doRun} className="rounded-lg border border-sky-300 px-3 py-1.5 text-xs font-medium text-sky-700 hover:bg-sky-50 disabled:opacity-60">Run</button>
                  <button type="button" disabled={opBusy || !canMutate || !canRollback} onClick={doRollback} className="rounded-lg border border-amber-300 px-3 py-1.5 text-xs font-medium text-amber-800 hover:bg-amber-50 disabled:opacity-60">Rollback</button>
                </div>
              </div>

              {runOutput ? (
                <pre className="max-h-40 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">{runOutput}</pre>
              ) : null}

              <div className="rounded-lg border border-slate-200 p-3">
                <p className="mb-2 text-xs font-medium text-slate-600">Timeline</p>
                <div className="space-y-2">
                  {selected.timeline.map((event, idx) => (
                    <div key={`${event.timestamp}-${idx}`} className="rounded-md bg-slate-50 p-2 text-xs">
                      <p className="text-slate-800">{event.event_type}</p>
                      <p className="text-slate-600">{event.message}</p>
                      <p className="text-slate-500">{event.timestamp}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Actions;
