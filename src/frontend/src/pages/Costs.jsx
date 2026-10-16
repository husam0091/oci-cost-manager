import { useEffect, useState } from 'react';
import { getBilledSpend } from '../services/api';
import { getDateRangeForPreset } from '../utils/dateRanges';
const card = 'rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800';
const control = 'rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800';
const money = (n, c) => { try { return new Intl.NumberFormat(undefined, { style: 'currency', currency: c }).format(n); } catch { return `${Number(n).toFixed(2)} ${c}`; } };
export default function Costs({ activeRegion = 'all' }) {
  const [range, setRange] = useState(() => getDateRangeForPreset('prev_month'));
  const [preset, setPreset] = useState('prev_month');
  const [service, setService] = useState('');
  const [resource, setResource] = useState(null);
  const [offset, setOffset] = useState(0);
  const [version, setVersion] = useState(0);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const invalid = !range.start || !range.end || range.start > range.end;
  useEffect(() => { setOffset(0); setResource(null); setService(''); }, [activeRegion]);
  useEffect(() => {
    let cancelled = false; setReport(null); setError('');
    if (invalid) { setLoading(false); return undefined; }
    setLoading(true);
    getBilledSpend({ start_date: range.start, end_date: range.end, region: activeRegion, service: service || undefined,
      resource_id: resource?.id, offset, limit: 100, refresh: version > 0 && offset === 0,
    }).then(r => { if (!cancelled) setReport(r.data); }).catch(e => { if (!cancelled) setError(e.response?.data?.error?.reason || 'Could not read OCI charges. Check sign-in and Diagnostics.'); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [range.start, range.end, service, resource?.id, activeRegion, offset, version, invalid]);
  const data = report?.data, meta = report?.meta, rows = data?.items || [];
  function exportPage() {
    const csv = [['OCI-reported charges; CURRENT PAGE ONLY; not a final invoice'], ['Start UTC', range.start, 'End inclusive UTC', range.end],
      ['Service', 'Resource', 'OCID', 'SKU', 'Part number', 'Currency', 'Cost', 'Quantity', 'Unit', 'Effective rate', 'License evidence'],
      ...rows.map(r => [r.service, r.resource_name, r.resource_id, r.sku_name, r.sku_part_number, r.currency, r.cost, r.quantity, r.unit, r.effective_unit_cost, r.licensing.model])]
      .map(row => row.map(v => { let t = String(v ?? ''); if (/^[=+@\t\r]/.test(t) || (/^-/.test(t) && !/^-\d+(\.\d+)?$/.test(t))) t = `'${t}`; return `"${t.replaceAll('"', '""')}"`; }).join(',')).join('\r\n');
    const u = URL.createObjectURL(new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })); const a = document.createElement('a'); a.href = u; a.download = `oci-spend-${range.start}-page-${offset / 100 + 1}.csv`; a.click(); setTimeout(() => URL.revokeObjectURL(u), 1000);
  }
  return <div className="space-y-5">
    <div className="flex flex-wrap justify-between gap-4"><div><h1 className="text-2xl font-bold">Understand your cloud bill</h1><p className="mt-1 text-sm text-slate-500">Actual OCI-reported charges. Open a resource to inspect each billed SKU.</p></div><button className={control} disabled={loading || invalid} onClick={() => { setOffset(0); setVersion(v => v + 1); }}>Refresh from OCI</button></div>
    <div className={`${card} flex flex-wrap items-end gap-4`}>
      <label className="text-sm">Period<select aria-label="Period" className={`${control} mt-1 block`} value={preset} onChange={e => { setPreset(e.target.value); setOffset(0); setResource(null); if (e.target.value !== 'custom') setRange(getDateRangeForPreset(e.target.value)); }}><option value="prev_month">Previous full month</option><option value="ytd">Year to date</option><option value="prev_year">Previous full year</option><option value="custom">Custom dates</option></select></label>
      {['start', 'end'].map(k => <label className="text-sm" key={k}>{k === 'start' ? 'Start (UTC)' : 'End, inclusive (UTC)'}<input aria-label={`${k} date`} className={`${control} mt-1 block`} type="date" value={range[k]} onChange={e => { setPreset('custom'); setRange({ ...range, [k]: e.target.value }); setOffset(0); }} /></label>)}
      <label className="text-sm">Service<select aria-label="Service" className={`${control} mt-1 block`} value={service} onChange={e => { setService(e.target.value); setResource(null); setOffset(0); }}><option value="">All services</option>{[...new Set([service, ...(data?.services || [])].filter(Boolean))].map(s => <option key={s}>{s}</option>)}</select></label><span className="pb-2 text-xs text-slate-500">Region: {activeRegion === 'all' ? 'All regions' : activeRegion}</span>
    </div>
    {invalid && <p role="alert" className="text-rose-700">Choose valid dates with the end on or after the start.</p>}
    {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-800">{error} <button className="underline" onClick={() => setVersion(v => v + 1)}>Retry</button></div>}
    {loading && <div role="status" className={card}>Reading OCI billing… No estimated bill is substituted.</div>}
    {report && <>
      <div className="grid gap-4 md:grid-cols-3">{data.totals.map(t => <section className={card} key={t.currency}><p className="text-xs uppercase text-slate-500">Net reported spend · {t.currency}</p><p className="my-3 text-3xl font-semibold">{money(t.net, t.currency)}</p><p className="text-xs text-slate-500">Charges {money(t.charges, t.currency)} · Credits {money(t.credits, t.currency)}</p></section>)}</div>
      <div className="flex flex-wrap justify-between gap-2 text-xs text-slate-500"><span>{meta.cached ? 'Cached OCI response' : 'Fetched from OCI'} · {new Date(data.generated_at).toLocaleString()} · 10-minute cache</span><span>{data.scope_limited ? 'Assigned scope only; unattributed resources excluded' : 'Includes unattributed charges'}</span></div>
      {resource && <div className="flex flex-wrap gap-4 rounded-xl bg-cyan-50 p-4 text-sm text-cyan-900"><button className="underline" onClick={() => { setResource(null); setOffset(0); }}>← All resources</button><strong>{resource.name}</strong></div>}
      <section className={card}><div className="mb-4 flex flex-wrap justify-between gap-3"><div><h2 className="font-semibold">{resource ? 'Resource billing details' : 'What you are paying for'}</h2><p className="text-xs text-slate-500">{meta.total} billing groups · totals cover all pages</p></div><button className={control} disabled={!rows.length} onClick={exportPage}>Download this page (CSV)</button></div>
        <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-xs text-slate-500"><tr><th className="p-3">Service / resource</th><th className="p-3">Billed SKU</th><th className="p-3">Licensing evidence</th>{resource && <th className="p-3">Usage / effective billed rate</th>}<th className="p-3 text-right">Charge</th></tr></thead><tbody>{rows.map((r, i) => <tr className="border-b border-slate-100 dark:border-slate-700" key={`${r.resource_id}-${r.sku_name}-${r.unit}-${r.currency}-${i}`}>
          <td className="max-w-xs p-3"><small className="block text-slate-500">{r.service}</small>{!resource && r.resource_id ? <button className="break-all text-left font-medium text-cyan-700 hover:underline" onClick={() => { setResource({ id: r.resource_id, name: r.resource_name }); setService(r.service === 'Not supplied by OCI' ? '' : r.service); setOffset(0); }}>{r.resource_name} →</button> : <span className="break-all">{r.resource_name}</span>}<small className="mt-1 block text-slate-500">{r.region || 'Region not supplied'} · {r.compartment_id || 'Compartment not supplied'}</small></td>
          <td className="max-w-sm p-3">{r.sku_name}<small className="mt-1 block text-slate-500">{r.sku_part_number || 'Open resource for part number'}</small></td><td className="max-w-xs p-3"><b>{r.licensing.model}</b><small className="mt-1 block text-slate-500">{r.licensing.explanation}</small></td>
          {resource && <td className="p-3">{r.quantity == null ? 'Usage not supplied' : `${r.quantity.toLocaleString()} ${r.unit || ''}`}<small className="mt-1 block text-slate-500">{r.effective_unit_cost == null ? 'Rate unavailable' : `${r.effective_unit_cost.toPrecision(6)} ${r.currency} / ${r.unit}`}</small></td>}
          <td className={`whitespace-nowrap p-3 text-right font-semibold ${r.cost < 0 ? 'text-emerald-700' : ''}`}>{money(r.cost, r.currency)}<small className="mt-1 block font-normal text-slate-500">{r.charge_type}</small></td></tr>)}</tbody></table></div>
        {!rows.length && <p className="py-8 text-center text-slate-500">OCI returned no billing items. Missing charges do not confirm free resources or BYOL eligibility.</p>}
        <div className="mt-4 flex items-center justify-between text-xs text-slate-500"><span>{rows.length ? `${offset + 1}–${offset + rows.length}` : '0'} of {meta.total}</span><div className="flex gap-2"><button className={control} disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 100))}>Previous</button><button className={control} disabled={!meta.has_more} onClick={() => setOffset(offset + 100)}>Next</button></div></div>
      </section>
    </>}
    <details className={card}><summary className="cursor-pointer font-semibold">Understand PAYG, software licenses and your invoice</summary><div className="mt-4 space-y-3 text-sm text-slate-600 dark:text-slate-400">
      <p><b>Pay as you go (PAYG)</b> is a commercial billing plan based on usage. This view uses OCI-reported charges; subscription discounts and agreements can affect the bill. It does not assume your tenancy uses PAYG.</p>
      <p><b>Windows / SQL Server:</b> compute, Windows OS and SQL Server or Marketplace software can be separate charges. A software-related SKU is labeled as a metered software charge; confirm PAYG terms in your agreement.</p>
      <p><b>License Included:</b> explicitly named SKUs already include software licensing in that charge. Do not add a second license estimate.</p>
      <p><b>BYOL:</b> use of existing licenses still incurs OCI infrastructure charges. Separate license/support costs are outside this view. Eligibility must be checked against the applicable agreement.</p>
      <p>Dates are UTC billing boundaries. Recent usage can be delayed. Taxes, fees and invoice adjustments may differ. Currencies are kept separate and negative amounts remain credits/adjustments. Effective unit cost is a blended billed rate, not a public price or quote.</p>
      <div className="flex flex-wrap gap-4"><a className="text-cyan-700 underline" href="https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/costanalysisoverview.htm" target="_blank" rel="noreferrer">Oracle Cost Analysis</a><a className="text-cyan-700 underline" href="https://docs.oracle.com/en-us/iaas/Content/Compute/References/microsoftlicensing.htm" target="_blank" rel="noreferrer">Microsoft licensing on OCI</a><a className="text-cyan-700 underline" href="https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/costusagereportsoverview.htm" target="_blank" rel="noreferrer">Invoice reconciliation</a></div>
    </div></details>
  </div>;
}
