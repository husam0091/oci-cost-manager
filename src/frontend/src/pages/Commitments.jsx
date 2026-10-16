import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ResponsiveContainer, LineChart, Line, BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip, Legend, Cell } from 'recharts';
import { getCommitmentContracts, getCommitmentOverview, getCommitmentBreakdown, syncCommitments, createCommitment, getCommitmentSyncJob } from '../services/api';
import './Commitments.css';

const money = (value, currency) => value == null ? 'Unavailable' : new Intl.NumberFormat(undefined, { style: 'currency', currency, maximumFractionDigits: 2 }).format(value);
const errorText = e => e.response?.data?.detail?.reason || e.response?.data?.error?.reason || e.response?.data?.detail || e.message;
export default function Commitments({ activeRegion = 'all', role = 'viewer' }) {
  const [contracts, setContracts] = useState([]);
  const [selected, setSelected] = useState('');
  const [currency, setCurrency] = useState('');
  const [mode, setMode] = useState('subscription');
  const [report, setReport] = useState(null);
  const [diagnostics, setDiagnostics] = useState(null);
  const [service, setService] = useState([]);
  const [shares, setShares] = useState([]);
  const [group, setGroup] = useState('compartment');
  const [refresh, setRefresh] = useState(0);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [syncJob, setSyncJob] = useState(null);
  const canEdit = role === 'admin' || role === 'finops';
  const [loading, setLoading] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const [form, setForm] = useState({ name: '', currency: 'USD', total_value: '', start_date: '', end_date: '', term_months: 12, oci_subscription_id: '' });
  const navigate = useNavigate();
  useEffect(() => {
    let cancelled = false;
    getCommitmentContracts().then(({ data }) => {
      if (cancelled) return;
      setContracts(data.data); setDiagnostics(data.meta.diagnostics);
      const today = new Date().toISOString().slice(0, 10);
      const preferred = data.data.find(c => c.start_date <= today && c.end_date_exclusive > today && !['cancelled', 'canceled', 'terminated', 'expired'].includes(c.status.toLowerCase())) || data.data[0];
      setSelected(previous => data.data.some(c => c.id === previous) ? previous : preferred?.id || '');
      setCurrency(previous => data.data.some(c => c.currency === previous) ? previous : preferred?.currency || '');
    }).catch(e => { if (!cancelled) setError(String(errorText(e))); });
    return () => { cancelled = true; };
  }, [refresh]);
  useEffect(() => {
    let cancelled = false;
    if (!selected) { setReport(null); return; }
    setLoading(true); setError(''); setReport(null); setService([]); setShares([]);
    getCommitmentOverview({ contract_id: selected, mode, region: activeRegion }).then(({ data }) => {
      if (!cancelled) { setReport(data.data); setDiagnostics(data.data.diagnostics); }
    }).catch(e => { if (!cancelled) setError(String(errorText(e))); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [selected, mode, activeRegion, refresh]);
  useEffect(() => {
    if (!syncJob) return;
    let cancelled = false;
    let timer;
    const poll = async () => {
      try {
        const { data } = await getCommitmentSyncJob(syncJob);
        if (cancelled) return;
        const status = data.data.status;
        if (status === 'succeeded' || status === 'failed') {
          setNotice(status === 'succeeded' ? 'Sync finished. Review source diagnostics for any partial results.' : 'Sync failed. Review the source diagnostics and worker logs.');
          setSyncJob(null); setRefresh(n => n + 1); return;
        }
        setNotice(`Subscription sync ${status} · ${data.data.progress ?? 0}% · ${syncJob}`);
      } catch (e) { if (!cancelled) setError(String(errorText(e))); }
      if (!cancelled) timer = setTimeout(poll, 4000);
    };
    poll();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [syncJob]);
  const active = report?.active_period;
  useEffect(() => {
    let cancelled = false;
    if (!active?.id) return;
    Promise.all([
      getCommitmentBreakdown({ period: active.id, group_by: 'service', region: activeRegion }),
      getCommitmentBreakdown({ period: active.id, group_by: group, region: activeRegion })
    ]).then(([services, groups]) => {
      if (!cancelled) { setService(services.data.meta.complete ? services.data.data : []); setShares(groups.data.meta.complete ? groups.data.data : []); }
    }).catch(e => { if (!cancelled) setError(String(errorText(e))); });
    return () => { cancelled = true; };
  }, [active?.id, group, activeRegion, refresh]);
  const currencies = useMemo(() => [...new Set(contracts.map(c => c.currency))], [contracts]);
  const contract = report?.contract;
  const code = contract?.currency || currency || 'USD';
  const periods = (report?.periods || []).slice(-12);
  const policies = [...new Set(Object.values(diagnostics?.policies || {}).flat())];
  const queue = async () => {
    try { const { data } = await syncCommitments(); setSyncJob(data.data.job_id); setNotice(`Sync queued · ${data.data.job_id}. The inventory scan is unaffected.`); }
    catch (e) { setError(String(errorText(e))); }
  };
  const save = async e => {
    e.preventDefault();
    try { const { data } = await createCommitment({ ...form, term_months: Number(form.term_months) }); setSelected(data.data.id); setCurrency(data.data.currency); setRefresh(n => n + 1); setShowManual(false); setNotice('Manual contract saved. Run Sync subscriptions to load actual OCI spend.'); }
    catch (err) { setError(String(errorText(err))); }
  };
  const explore = datum => {
    const item = datum?.payload || datum;
    if (!active || item?.name === 'Other' || item?.name === 'Unattributed') return;
    const end = new Date(`${active.end_date_exclusive}T00:00:00Z`); end.setUTCDate(end.getUTCDate() - 1);
    navigate('/costs', { state: { service: item.name, startDate: active.start_date, endDate: end.toISOString().slice(0, 10) } });
  };
  const metrics = [
    ['Committed · whole term', money(contract?.total_value, code)], ['Consumed · term to date', money(report?.consumed_to_date, code)],
    ['Remaining commitment', money(report?.remaining, code)], ['Utilisation', report?.utilisation_pct == null ? 'Unavailable' : `${report.utilisation_pct.toFixed(1)}%`],
    ['Daily burn · term average', money(report?.daily_burn, code)], ['Forecast · linear estimate', money(report?.forecast_term_end, code)],
    ['Days left', report?.days_remaining ?? '—'], ['Active period · UTC', active ? `${active.start_date} → ${active.end_date_exclusive} (end exclusive)` : 'No synced active period']
  ];
  return <div className="commitments-page">
    <header className="commitments-header"><div><p className="overline">CONTRACT INTELLIGENCE · INTERFACE 2.3</p><h1>Commitment vs Spend</h1><p>Understand your Universal Credits, actual consumption and the pace ahead.</p></div><div className="commitments-actions"><button className="finops-button" onClick={() => setRefresh(n => n + 1)}>Refresh view</button><button className="finops-button is-primary" disabled={!canEdit || Boolean(syncJob)} title={!canEdit ? 'Administrator or FinOps role required' : 'Refresh OCI subscription sources'} onClick={queue}>{syncJob ? 'Sync in progress…' : 'Sync subscriptions'}</button></div></header>
    {error && <p role="alert" className="commitments-alert">{error}</p>}{notice && <p role="status" className="commitments-notice">{notice}</p>}
    <section className="finops-panel commitments-controls"><label>Contract<select value={selected} onChange={e => setSelected(e.target.value)}><option value="">Select a contract</option>{contracts.filter(c => !currency || c.currency === currency).map(c => <option key={c.id} value={c.id}>{c.name} · {c.source}</option>)}</select></label><label>Period basis<select value={mode} onChange={e => setMode(e.target.value)}><option value="subscription">Subscription anniversary month</option><option value="calendar">Calendar month</option></select></label><div><small>Region</small><p>{activeRegion || 'all'} · contract allowance remains tenancy-wide</p></div><button className="finops-button" disabled={!canEdit} title={!canEdit ? 'Administrator or FinOps role required' : 'Enter confirmed contract terms'} onClick={() => setShowManual(!showManual)}>Add manual contract</button></section>
    <div className="commitments-currencies" role="group" aria-label="Currency">{currencies.map(c => <button key={c} aria-pressed={currency === c} onClick={() => { setCurrency(c); setSelected(contracts.find(row => row.currency === c)?.id || ''); }}>{c}</button>)}</div>
    {showManual && <form className="finops-panel commitments-form" onSubmit={save}><h2>Manual contract · clearly marked as manual</h2><p>Enter confirmed contract terms. End date is exclusive; for a term ending 14 March enter 15 March.</p>{[['name', 'Contract name', 'text'], ['total_value', 'Total committed value', 'number'], ['currency', 'Currency (ISO code)', 'text'], ['start_date', 'Start date', 'date'], ['end_date', 'End date (exclusive)', 'date'], ['term_months', 'Term months', 'number'], ['oci_subscription_id', 'OCI subscription ID (optional)', 'text']].map(([key, label, type]) => <label key={key}>{label}<input required={key !== 'oci_subscription_id'} type={type} step={key === 'total_value' ? '0.01' : undefined} value={form[key]} onChange={e => setForm({ ...form, [key]: e.target.value })} /></label>)}<button className="finops-button is-primary" type="submit">Save manual contract</button></form>}
    {loading && <p role="status">Loading persisted commitment data…</p>}
    {!loading && !contract && <section className="finops-panel commitments-empty"><h2>No contract available yet</h2><p>Sync OCI subscriptions, review source permissions below, or add your confirmed contract manually. Missing commitment values are never replaced with zero.</p></section>}
    {contract && <>
      <p className="commitments-freshness">{contract.source === 'manual' ? 'MANUAL CONTRACT' : contract.source} · Spend computed {report.computed_at || 'not yet synced'} · Currency {code}</p>
      {report.alerts.map(message => <p key={message} className="commitments-alert" role="status">{message}</p>)}
      <div className="commitments-metrics">{metrics.map(([label, value]) => <section className="finops-panel" key={label}><small>{label}</small><strong>{value}</strong></section>)}</div>
      <p>{report.projected_overage > 0 ? `Projected overage: ${money(report.projected_overage, code)} (estimate)` : report.projected_underuse != null ? `Projected underuse: ${money(report.projected_underuse, code)} (estimate)` : 'Forecast unavailable until spend is complete.'}</p>
      <div className="commitments-charts">
        <section className="finops-panel"><h2>Term trajectory</h2><p>Committed ramp, OCI actuals and linear forecast · {code}</p><div className="commitments-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={report.cumulative}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="date" /><YAxis /><Tooltip /><Legend /><Line dataKey="committed" stroke="#8092ba" dot={false} /><Line dataKey="actual" stroke="#108891" dot={false} /><Line dataKey="forecast" stroke="#d39a34" strokeDasharray="6 4" dot={false} /></LineChart></ResponsiveContainer></div></section>
        <section className="finops-panel"><h2>Monthly allowance vs actual</h2><p>Last 12 periods · negative credits stay in net spend</p><div className="commitments-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={periods}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="start_date" /><YAxis /><Tooltip /><Legend /><Bar dataKey="allowance" fill="#aab7d2" /><Bar dataKey="actual">{periods.map(row => <Cell key={row.id} fill={row.actual > row.allowance && row.allowance != null ? '#c94c51' : '#108891'} />)}</Bar></BarChart></ResponsiveContainer></div></section>
        <section className="finops-panel"><h2>Active month by service</h2><p>Click a service to inspect its billing items · {code}</p>{service.length ? <div className="commitments-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={service} layout="vertical" margin={{ left: 50 }}><XAxis type="number" /><YAxis type="category" dataKey="name" width={110} /><Tooltip /><Bar dataKey="actual" fill="#108891" onClick={explore} cursor="pointer" /></BarChart></ResponsiveContainer></div> : <p>Sync complete active-period spend to see service costs.</p>}</section>
        <section className="finops-panel"><h2>Share of monthly allowance</h2><label>Group by <select value={group} onChange={e => setGroup(e.target.value)}><option value="compartment">Compartment</option><option value="team">Team allocation</option></select></label><p>Actual consumption ÷ whole monthly allowance; this is not a team budget.</p><div className="commitments-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={shares} layout="vertical" margin={{ left: 50 }}><XAxis type="number" unit="%" /><YAxis type="category" dataKey="name" width={110} /><Tooltip /><Bar dataKey="allowance_share_pct" fill="#8092ba" /></BarChart></ResponsiveContainer></div></section>
      </div>
      <section className="finops-panel"><div className="commitments-actions"><h2>Periods</h2><a className="finops-button" href={`/api/v1/subscriptions/export?contract_id=${encodeURIComponent(contract.id)}&mode=${mode}&format=csv&region=${encodeURIComponent(activeRegion)}`}>Export CSV</a><a className="finops-button" href={`/api/v1/subscriptions/export?contract_id=${encodeURIComponent(contract.id)}&mode=${mode}&format=xlsx&region=${encodeURIComponent(activeRegion)}`}>Export XLSX</a></div><div className="overview-table-wrap"><table className="overview-table"><thead><tr><th>Period (end exclusive)</th><th>Allowance · prorated</th><th>Charges</th><th>Credits</th><th>Actual net</th><th>Forecast · estimate</th></tr></thead><tbody>{periods.map(row => <tr key={row.id}><td>{row.start_date} → {row.end_date_exclusive}</td>{['allowance', 'charges', 'credits', 'actual', 'forecast'].map(key => <td key={key}>{money(row[key], code)}</td>)}</tr>)}</tbody></table></div></section>
      <p className="commitments-note">{report.meta.comparison} {report.meta.payg_note} {report.meta.credit_expiry} Forecasts and prorated allowances are estimates. <Link to="/costs">Inspect real billed spend</Link>.</p>
    </>}
    <section className="finops-panel"><h2>Contracts</h2><div className="overview-table-wrap"><table className="overview-table"><thead><tr><th>Contract</th><th>Source</th><th>Status</th><th>Start / end exclusive</th><th>Value</th></tr></thead><tbody>{contracts.map(c => <tr key={c.id}><td>{c.name}</td><td>{c.source}</td><td>{c.status}</td><td>{c.start_date} → {c.end_date_exclusive}</td><td>{money(c.total_value, c.currency)}</td></tr>)}</tbody></table></div></section>
    <section className="finops-panel commitments-diagnostics"><h2>Subscription source diagnostics</h2><p>Sync status: {diagnostics?.status || 'not synced'}. An empty response does not prove permission is missing.</p>{Object.entries(diagnostics?.sources || {}).map(([name, status]) => <details key={name}><summary>{name} · {status.status}{status.count != null ? ` · ${status.count} returned` : ''}</summary>{status.error && <pre>{status.error}</pre>}{status.policy_note && <p>{status.policy_note}</p>}{status.totals && <p>{Object.entries(status.totals).map(([c, amount]) => `${c}: ${money(Number(amount), c)}`).join(' · ')}</p>}{status.policies?.map(policy => <code key={policy}>{policy}</code>)}</details>)}<details><summary>IAM checklist · tenancy-level read permissions</summary><p>{diagnostics?.iam_note}</p>{policies.map(policy => <code key={policy}>{policy}</code>)}</details><p>Diagnostics preserve OCI failures per source. No production permissions are changed by this page.</p></section>
  </div>;
}
