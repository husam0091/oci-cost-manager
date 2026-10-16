import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowDownRight, ArrowRight, ArrowUpRight, CalendarDays, ChevronRight, RefreshCw, ReceiptText, ShieldCheck } from 'lucide-react';
import { getBilledSpend } from '../services/api';
import { getDateRangeForPreset } from '../utils/dateRanges';
const money = (value, currency) => {
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
      maximumFractionDigits: 2
    }).format(value);
  } catch {
    return `${Number(value).toLocaleString()} ${currency}`;
  }
};
const palette = ['#108891', '#6b83bd', '#a395bd', '#d4a05e', '#719e8e'];
export default function Overview({
  activeRegion = 'all'
}) {
  const [period, setPeriod] = useState('prev_month');
  const [currency, setCurrency] = useState('USD');
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let cancelled = false;
    const range = getDateRangeForPreset(period);
    setLoading(true);
    setReport(null);
    setError('');
    getBilledSpend({
      start_date: range.start,
      end_date: range.end,
      region: activeRegion,
      limit: 1,
      refresh: refresh > 0
    }).then(response => {
      if (!cancelled) setReport(response.data);
    }).catch(err => {
      if (!cancelled) setError(err.response?.data?.error?.reason || 'Billed spend is unavailable. Check the OCI connection in Diagnostics.');
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [period, activeRegion, refresh]);
  const currencies = report?.data?.totals || [];
  const current = currencies.find(t => t.currency === currency) || currencies[0];
  const code = current?.currency || currency;
  const services = (report?.data?.by_service || []).filter(s => s.currency === code);
  const resources = (report?.data?.resources || []).filter(r => r.currency === code);
  const range = getDateRangeForPreset(period);
  const metrics = [{
    label: 'Net reported spend',
    value: current ? money(current.net, code) : '—',
    note: 'Charges after credits and adjustments',
    icon: ReceiptText,
    featured: true
  }, {
    label: 'Usage charges',
    value: current ? money(current.charges, code) : '—',
    note: 'Positive amounts reported by OCI',
    icon: ArrowUpRight
  }, {
    label: 'Credits & adjustments',
    value: current ? money(current.credits, code) : '—',
    note: 'Negative amounts, kept visible',
    icon: ArrowDownRight
  }, {
    label: 'Resources billed',
    value: report ? resources.filter(r => r.resource_id).length.toLocaleString() : '—',
    note: 'In this period, region and currency',
    icon: ShieldCheck
  }];
  const maximum = Math.max(...services.map(s => Math.abs(s.cost)), 1);
  return <div className="overview-page">
    <div className="overview-heading"><div><p className="overline">ORACLE CLOUD INFRASTRUCTURE</p><h1>Your cloud, in perspective.</h1><p>Understand your spend. Find opportunities. Stay in control.</p></div><button className="finops-button" disabled={loading} onClick={() => setRefresh(v => v + 1)}><RefreshCw size={15} className={loading ? 'animate-spin' : ''} />Refresh from OCI</button></div>
    <div className="overview-filters"><label><CalendarDays size={15} /><span>Period</span><select aria-label="Overview reporting period" value={period} onChange={e => setPeriod(e.target.value)}><option value="prev_month">Previous full month</option><option value="ytd">Year to date</option><option value="prev_year">Previous full year</option></select></label><span className="filter-date">{range.start} — {range.end} · UTC</span>{currencies.length > 1 && <label>Currency<select aria-label="Overview currency" value={code} onChange={e => setCurrency(e.target.value)}>{currencies.map(t => <option key={t.currency}>{t.currency}</option>)}</select></label>}<span className="snapshot-label">{loading ? 'Reading OCI billing…' : report ? `${report.meta.cached ? 'Cached OCI response' : 'OCI response'} · ${new Date(report.data.generated_at).toLocaleTimeString()}` : 'Connection needs attention'}</span></div>
    {error && <div role="alert" className="overview-error"><strong>We couldn’t load your billed spend.</strong><p>{error}</p><Link to="/logs">Open Diagnostics <ArrowRight size={14} /></Link></div>}
    <div className="overview-metrics" aria-busy={loading}>{metrics.map(({
        label,
        value,
        note,
        icon: Icon,
        featured
      }) => <section key={label} className={`metric-tile ${featured ? 'is-featured' : ''}`}><div className="metric-label">{label}<Icon size={17} /></div><strong>{value}</strong><p>{note}</p></section>)}</div>
    <div className="overview-charts"><section className="finops-panel"><div className="panel-heading"><div><h2>Where your money goes</h2><p>Net charges by service · {code}</p></div><Link to="/costs">Explore spend <ChevronRight size={14} /></Link></div>{services.length ? <div className="service-bars">{services.slice(0, 7).map((s, i) => <div key={s.service}><div className="service-bar-label"><span><i style={{
                  background: palette[i % palette.length]
                }} />{s.service}</span><strong>{money(s.cost, code)}</strong></div><div className="service-bar-track"><div style={{
                width: `${Math.abs(s.cost) / maximum * 100}%`,
                background: s.cost < 0 ? '#608a72' : palette[i % palette.length]
              }} /></div></div>)}</div> : <div className="finops-empty">{loading ? 'Loading service charges…' : 'No service charges returned for this selection.'}</div>}<p className="panel-footnote">All billing groups are included before pagination. Credits remain in the net amount.</p></section>
    <section className="finops-panel bill-guide"><span className="guide-icon"><ReceiptText size={25} /></span><p className="overline">KNOW YOUR BILL</p><h2>One resource.<br />Every billed item.</h2><p>See how compute, storage and software contribute to the cost of a workload.</p><ul><li><span>01</span>Choose a service or resource</li><li><span>02</span>Inspect each SKU and usage unit</li><li><span>03</span>Check the licensing evidence</li></ul><Link className="finops-button is-primary" to="/costs">Open spend explorer <ArrowRight size={15} /></Link></section></div>
    <div className="overview-opportunity"><div className="opportunity-icon"><ShieldCheck size={23} /></div><div><h2>Turn insight into a lower cloud bill.</h2><p>Review optimization recommendations with workload context before creating an action.</p></div><Link className="finops-button" to="/recommendations">Review opportunities <ArrowRight size={15} /></Link></div>
    <section className="finops-panel"><div className="panel-heading"><div><h2>Your highest-cost resources</h2><p>Net reported spend · {code} · includes charges without a resource identifier</p></div><Link to="/resources">View inventory <ChevronRight size={14} /></Link></div><div className="overview-table-wrap"><table className="overview-table"><thead><tr><th>Resource</th><th>Region / compartment</th><th>Billing items</th><th className="number">Net charge</th><th>Details</th></tr></thead><tbody>{resources.slice(0, 8).map((r, i) => <tr key={r.resource_id || `unattributed-${i}`}><td><strong>{r.resource_name}</strong><small>{r.resource_id ? 'OCI resource' : 'Not attributed by OCI'}</small></td><td>{r.region || 'Not supplied'}<small>{r.compartment_id || 'Compartment not supplied'}</small></td><td><span className="billing-count">{r.billing_groups} groups</span></td><td className="number">{money(r.cost, code)}</td><td><Link to="/costs" state={{
                  resourceId: r.resource_id,
                  resourceName: r.resource_name,
                  startDate: range.start,
                  endDate: range.end
                }}>Inspect <ArrowRight size={13} /></Link></td></tr>)}</tbody></table></div>{!resources.length && <div className="finops-empty">{loading ? 'Loading resource charges…' : 'No billed resources were returned. Missing charges do not confirm that a workload is free.'}</div>}</section>
    <div className="overview-notes"><span>Source: OCI Usage API · {report?.data?.scope_limited ? 'Assigned scope only' : 'Selected tenancy scope'} · Not a final invoice</span><Link to="/analytics">Open detailed analytics <ArrowRight size={12} /></Link></div>
  </div>;
}
