import { useEffect, useMemo, useState } from 'react';
import { Download, RefreshCw } from 'lucide-react';
import { adminDownloadExport, adminGenerateExport, adminListExports, getDataCompartmentTree } from '../services/api';
import { getDateRangeForPreset, toIsoDate } from '../utils/dateRanges';
import { UI_COPY } from '../constants/copy';

const REPORT_CATALOG = [
  { id: 'executive_summary_monthly', title: 'Executive Summary', description: 'Total, deltas, top drivers, movers, governance KPIs', audience: 'Exec/Finance' },
  { id: 'cost_by_service', title: 'Cost by Service', description: 'Top services with deltas, share, and Other bucket', audience: 'Finance/Ops' },
  { id: 'cost_by_compartment', title: 'Cost by Compartment', description: 'Hierarchy totals, deltas, top service per compartment', audience: 'Finance/Ops' },
  { id: 'top_resources_by_cost', title: 'Top Resources by Cost', description: 'Highest-cost resources with deltas and top SKU', audience: 'FinOps/Ops' },
  { id: 'mapping_health_unallocated', title: 'Mapping Health / Unallocated', description: 'Unallocated + low-confidence mapping visibility', audience: 'FinOps' },
  { id: 'showback_team_app_env', title: 'Showback by Team/App/Env', description: 'Allocation showback with unowned breakdown', audience: 'Finance/FinOps' },
  { id: 'inventory_summary_by_compartment', title: 'Inventory Summary by Compartment', description: 'Compartment summary metrics (not raw dump)', audience: 'Ops' },
  { id: 'storage_backup_governance', title: 'Storage & Backup Governance', description: 'Unattached waste, backup trend/drivers', audience: 'Ops/Governance' },
  { id: 'license_spend', title: 'License Spend', description: 'Windows + SQL SKU drivers and deltas', audience: 'Finance/Governance' },
  { id: 'movers_and_anomalies', title: 'Movers & Anomalies', description: 'Service/compartment/resource spikes and movers', audience: 'Exec/Ops' },
  { id: 'optimization_recommendations', title: 'Optimization Recommendations', description: 'Actionable savings opportunities with confidence and reasons', audience: 'Exec/FinOps/Ops' },
  { id: 'budget_health', title: 'Budget Health', description: 'Budget utilization, breaches, and forecast risks', audience: 'Exec/Finance/Engineering' },
  { id: 'actions_audit', title: 'Actions Audit', description: 'Action approvals, execution timeline, and savings realization placeholders', audience: 'Exec/FinOps/Ops/Sec' },
  { id: 'ops_audit', title: 'Ops Audit', description: 'Scans/alerts/actions operational timelines and failure root causes', audience: 'Platform/Ops' },
];

function ExportReports() {
  const [selectedReport, setSelectedReport] = useState(REPORT_CATALOG[0].id);
  const [period, setPeriod] = useState('prev_month');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');
  const [groupBy, setGroupBy] = useState('service');
  const [topN, setTopN] = useState(10);
  const [minSharePct, setMinSharePct] = useState(0.5);
  const [includeChildren, setIncludeChildren] = useState(true);
  const [compartmentIds, setCompartmentIds] = useState([]);
  const [compartmentOptions, setCompartmentOptions] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [status, setStatus] = useState(null);
  const [exports, setExports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(null);

  const range = useMemo(() => {
    if (period === 'custom') {
      if (!customStart || !customEnd) return null;
      return { start: customStart, end: customEnd };
    }
    return getDateRangeForPreset(period);
  }, [period, customStart, customEnd]);

  const loadExports = async () => {
    setLoading(true);
    try {
      const res = await adminListExports();
      setExports(res.data?.data || []);
    } catch {
      setExports([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExports();
    const loadCompartmentOptions = async () => {
      try {
        const res = await getDataCompartmentTree();
        const walk = (node, acc = []) => {
          if (!node) return acc;
          acc.push({ id: node.id, label: node.name || node.id });
          (node.children || []).forEach((child) => walk(child, acc));
          return acc;
        };
        setCompartmentOptions(walk(res.data?.data || null, []));
      } catch {
        setCompartmentOptions([]);
      }
    };
    loadCompartmentOptions();
  }, []);

  const handleGenerate = async () => {
    if (!range) {
      setStatus({ type: 'error', text: 'Set a complete date range first.' });
      return;
    }
    setGenerating(true);
    setStatus(null);
    try {
      const res = await adminGenerateExport({
        report_type: selectedReport,
        start_date: range.start,
        end_date: range.end,
        options: {
          group_by: groupBy,
          compare: 'previous',
          top_n: topN,
          min_share_pct: minSharePct,
          include_children: includeChildren,
          compartment_ids: compartmentIds,
        },
      });
      setStatus({ type: 'success', text: `Generated ${res.data?.data?.files?.xlsx?.name || 'report.xlsx'}` });
      await loadExports();
    } catch (err) {
      setStatus({ type: 'error', text: err.response?.data?.detail || 'Report generation failed' });
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async (fileName) => {
    setDownloading(fileName);
    try {
      const res = await adminDownloadExport(fileName);
      const contentType = res.headers?.['content-type'] || 'application/octet-stream';
      const disposition = res.headers?.['content-disposition'] || '';
      const match = disposition.match(/filename="?([^";]+)"?/i);
      const downloadName = (match?.[1] || fileName).trim();
      const blob = new Blob([res.data], { type: contentType });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = downloadName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } finally {
      setDownloading(null);
    }
  };

  const nameFromUrl = (url) => decodeURIComponent((url || '').split('/').pop() || '');

  const reportMeta = REPORT_CATALOG.find((r) => r.id === selectedReport);

  const toggleCompartment = (id) => {
    setCompartmentIds((prev) => (prev.includes(id) ? prev.filter((v) => v !== id) : [...prev, id]));
  };

  return (
    <div className="space-y-6 bg-slate-50 p-2">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Report Catalog</h1>
        <p className="text-sm text-slate-500">FinOps/governance exports with manifest and validation sidecars</p>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {REPORT_CATALOG.map((r) => (
          <button
            key={r.id}
            onClick={() => setSelectedReport(r.id)}
            className={`rounded-2xl border p-4 text-left shadow-sm ${selectedReport === r.id ? 'border-cyan-500 bg-cyan-50' : 'border-slate-200 bg-white'}`}
          >
            <p className="font-semibold text-slate-900">{r.title}</p>
            <p className="mt-1 text-xs text-slate-600">{r.description}</p>
            <p className="mt-2 text-[11px] font-medium text-cyan-700">For: {r.audience}</p>
          </button>
        ))}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="mb-3 text-lg font-semibold text-slate-900">Filters</h3>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <select value={period} onChange={(e) => setPeriod(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
            <option value="prev_month">Previous Month</option>
            <option value="ytd">This Year (YTD)</option>
            <option value="prev_year">Previous Year</option>
            <option value="custom">Custom Range</option>
          </select>
          <select value={groupBy} onChange={(e) => setGroupBy(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
            <option value="service">Service</option>
            <option value="compartment">Compartment</option>
            <option value="team">Team</option>
            <option value="app">App</option>
            <option value="env">Environment</option>
          </select>
          <input
            type="number"
            min={3}
            max={50}
            value={topN}
            onChange={(e) => setTopN(parseInt(e.target.value || '10', 10))}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder="Top N"
          />
        </div>
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
          <input
            type="number"
            min={0}
            max={100}
            step="0.1"
            value={minSharePct}
            onChange={(e) => setMinSharePct(parseFloat(e.target.value || '0.5'))}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder="Min share %"
          />
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={includeChildren} onChange={(e) => setIncludeChildren(e.target.checked)} />
            Include child compartments
          </label>
          <div className="text-xs text-slate-500">Optional scope filter by compartments</div>
        </div>
        {period === 'custom' && (
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <input type="date" value={customStart} max={toIsoDate(new Date())} onChange={(e) => setCustomStart(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input type="date" value={customEnd} max={toIsoDate(new Date())} onChange={(e) => setCustomEnd(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          </div>
        )}
        <div className="mt-3 max-h-28 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-2">
          <div className="mb-2 text-xs font-medium text-slate-600">Compartment Scope</div>
          <div className="flex flex-wrap gap-2">
            {compartmentOptions.map((c) => (
              <button
                key={c.id}
                onClick={() => toggleCompartment(c.id)}
                className={`rounded-full px-2 py-1 text-xs ${compartmentIds.includes(c.id) ? 'bg-indigo-50 text-indigo-700' : 'bg-slate-100 text-slate-700'}`}
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-4 flex items-center gap-2">
          <button onClick={handleGenerate} disabled={generating} className="rounded-lg bg-cyan-700 px-4 py-2 text-sm font-medium text-white">
            {generating ? 'Generating...' : `Generate ${reportMeta?.title || 'Report'}`}
          </button>
          <button onClick={loadExports} disabled={loading} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm text-slate-700">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh History
          </button>
        </div>
        {status && (
          <div className={`mt-3 rounded-lg border px-3 py-2 text-sm ${status.type === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-rose-200 bg-rose-50 text-rose-700'}`}>
            {status.text}
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="mb-4 text-lg font-semibold text-slate-900">Generation History</h3>
        {exports.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="px-2 py-2 text-left">Report</th>
                  <th className="px-2 py-2 text-left">Range</th>
                  <th className="px-2 py-2 text-left">Created</th>
                  <th className="px-2 py-2 text-right">Size</th>
                  <th className="px-2 py-2 text-left">Downloads</th>
                </tr>
              </thead>
              <tbody>
                {exports.filter((e) => e.name.endsWith('.xlsx')).map((f) => (
                  <tr key={f.name} className="border-b border-slate-100">
                    <td className="px-2 py-2">
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                        {f.report_type || 'snapshot'}
                      </span>
                    </td>
                    <td className="px-2 py-2 text-xs text-slate-600">
                      {f.range?.start_date ? `${f.range.start_date.slice(0, 10)} to ${f.range.end_date?.slice(0, 10)}` : '-'}
                    </td>
                    <td className="px-2 py-2">{f.updated_at ? new Date(f.updated_at).toLocaleString() : '-'}</td>
                    <td className="px-2 py-2 text-right">{Math.round((f.size_bytes || 0) / 1024)} KB</td>
                    <td className="px-2 py-2">
                      <div className="flex flex-wrap gap-2">
                        <button onClick={() => handleDownload(f.name)} disabled={downloading === f.name} className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700">
                          <Download size={12} /> XLSX
                        </button>
                        {f.manifest_url && (
                          <button onClick={() => handleDownload(nameFromUrl(f.manifest_url))} className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700">
                            Manifest
                          </button>
                        )}
                        {f.validation_url && (
                          <button onClick={() => handleDownload(nameFromUrl(f.validation_url))} className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700">
                            Validation
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-slate-500">{UI_COPY.empty.noCostData}</p>
        )}
      </div>
    </div>
  );
}

export default ExportReports;
