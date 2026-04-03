import { useState, useEffect, useMemo } from 'react';
import { Database, Server, HardDrive, RefreshCw, Monitor, Folder, Archive, Shield, Package, Save, Search } from 'lucide-react';
import { getDataResources, getDataCompartmentTree, adminRunScan, getCostsByResource } from '../services/api';
import { UI_COPY } from '../constants/copy';

const typeConfig = {
  oracle_db: { icon: Database, color: 'bg-red-100 text-red-700', label: 'Oracle DB' },
  mysql: { icon: Database, color: 'bg-blue-100 text-blue-700', label: 'MySQL' },
  sql_server: { icon: Server, color: 'bg-purple-100 text-purple-700', label: 'SQL Server' },
  windows_server: { icon: Server, color: 'bg-violet-100 text-violet-700', label: 'Windows Server' },
  security_appliance: { icon: Shield, color: 'bg-amber-100 text-amber-700', label: 'Security Appliance' },
  autonomous_db: { icon: Database, color: 'bg-green-100 text-green-700', label: 'Autonomous DB' },
  compute: { icon: Monitor, color: 'bg-orange-100 text-orange-700', label: 'Compute VM' },
  nfs_file_system: { icon: Folder, color: 'bg-cyan-100 text-cyan-700', label: 'NFS File System' },
  bucket: { icon: Archive, color: 'bg-yellow-100 text-yellow-700', label: 'Object Storage' },
  block_volume: { icon: HardDrive, color: 'bg-slate-100 text-slate-700', label: 'Block Volume' },
  boot_volume: { icon: Package, color: 'bg-indigo-100 text-indigo-700', label: 'Boot Volume' },
  volume_backup: { icon: Save, color: 'bg-pink-100 text-pink-700', label: 'Volume Backup' },
  boot_volume_backup: { icon: Save, color: 'bg-fuchsia-100 text-fuchsia-700', label: 'Boot Volume Backup' },
};

const TYPE_FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'compute', label: 'VMs' },
  { key: 'sql_server', label: 'MS SQL' },
  { key: 'windows_server', label: 'Windows' },
  { key: 'security_appliance', label: 'F5/Palo/Forti' },
  { key: 'oracle_db', label: 'Oracle DB' },
  { key: 'mysql', label: 'MySQL' },
  { key: 'autonomous_db', label: 'Autonomous' },
  { key: 'nfs_file_system', label: 'NFS' },
  { key: 'block_volume', label: 'Block Vol' },
  { key: 'boot_volume', label: 'Boot Vol' },
  { key: 'volume_backup', label: 'Vol Backups' },
  { key: 'boot_volume_backup', label: 'Boot Backups' },
  { key: 'bucket', label: 'Buckets' },
];

const COST_TYPE_KEYS = ['sql_server', 'windows_server', 'security_appliance', 'nfs_file_system', 'volume_backup', 'block_volume'];

function detectTypeFromSkuText(text) {
  if (text.includes('sql server') || text.includes('microsoft sql')) return 'sql_server';
  if (text.includes('windows os')) return 'windows_server';
  if (text.includes('fortigate') || text.includes('palo alto') || text.includes('f5')) return 'security_appliance';
  if (text.includes('file storage')) return 'nfs_file_system';
  if (text.includes('backup')) return 'volume_backup';
  if (text.includes('block volume')) return 'block_volume';
  return null;
}

function resourceNameFromCostRow(row) {
  const id = row?.resource_id || '';
  if (!id) return 'Cost Resource';
  const short = id.length > 18 ? `...${id.slice(-18)}` : id;
  return `Resource ${short}`;
}

function ResourceCard({ resource, monthlyCost: monthlyCostProp }) {
  const config = typeConfig[resource.type] || { icon: HardDrive, color: 'bg-gray-100', label: resource.type };
  const Icon = config.icon;
  const displayName = resource.name && resource.name.trim().startsWith('ocid1.')
    ? `Resource ...${resource.name.trim().slice(-16)}`
    : (resource.name?.trim() || 'Unnamed resource');

  const d = resource.details || {};
  const monthlyCost = monthlyCostProp ?? d.monthly_cost ?? d.total_cost_estimate ?? null;
  const storageGb = d.size_in_gbs ?? d.data_storage_size_in_gbs ?? null;
  const ocpus = d.cpu_core_count ?? d.ocpus ?? null;
  const isHealthy = ['AVAILABLE', 'RUNNING', 'ACTIVE'].includes(resource.status);

  return (
    <div className="rounded-xl border border-slate-200/80 bg-white/90 p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <div className={`shrink-0 p-2 rounded-lg ${config.color}`}>
            <Icon size={20} />
          </div>
          <div className="min-w-0">
            <h3 className="truncate font-semibold text-slate-800 max-w-[180px]" title={resource.name}>
              {displayName}
            </h3>
            <p className="text-xs text-slate-500">{config.label}</p>
          </div>
        </div>
        <span className={`shrink-0 ml-2 px-2 py-1 rounded-full text-xs font-medium ${isHealthy ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
          {resource.status}
        </span>
      </div>

      {/* Monthly cost — prominent row */}
      {monthlyCost != null && (
        <div className="mt-3 flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
          <span className="text-xs font-medium text-slate-500">Est. Monthly Cost</span>
          <span className="text-sm font-bold text-slate-800">${monthlyCost.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
        </div>
      )}

      {/* Key specs grid */}
      <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
        {/* Private IP */}
        {d.private_ip && (
          <div className="col-span-2 flex items-center gap-1">
            <span className="text-slate-400">IP</span>
            <span className="font-mono font-medium text-slate-700">{d.private_ip}</span>
          </div>
        )}

        {/* OCPUs + Memory */}
        {ocpus != null && (
          <div className="flex gap-1">
            <span className="text-slate-400">OCPUs</span>
            <span className="font-medium text-slate-700">{ocpus}</span>
          </div>
        )}
        {d.memory_in_gbs != null && (
          <div className="flex gap-1">
            <span className="text-slate-400">RAM</span>
            <span className="font-medium text-slate-700">{d.memory_in_gbs} GB</span>
          </div>
        )}

        {/* Storage size */}
        {storageGb != null && (
          <div className="flex gap-1">
            <span className="text-slate-400">Storage</span>
            <span className="font-medium text-slate-700">{storageGb} GB</span>
          </div>
        )}
        {d.size_display && storageGb == null && (
          <div className="flex gap-1">
            <span className="text-slate-400">Size</span>
            <span className="font-medium text-slate-700">{d.size_display}</span>
          </div>
        )}

        {/* VPUs (block/boot volumes) */}
        {d.vpus_per_gb != null && (
          <div className="flex gap-1">
            <span className="text-slate-400">VPUs/GB</span>
            <span className="font-medium text-slate-700">{d.vpus_per_gb}</span>
          </div>
        )}

        {/* Shape */}
        {resource.shape && (
          <div className="col-span-2 flex gap-1">
            <span className="text-slate-400">Shape</span>
            <span className="font-medium text-slate-700 truncate">{resource.shape}</span>
          </div>
        )}

        {/* DB edition + version */}
        {d.edition && (
          <div className="col-span-2 flex gap-1">
            <span className="text-slate-400">Edition</span>
            <span className="font-medium text-slate-700">{d.edition.replace(/_/g, ' ')}</span>
          </div>
        )}
        {d.version && (
          <div className="flex gap-1">
            <span className="text-slate-400">Version</span>
            <span className="font-medium text-slate-700">{d.version}</span>
          </div>
        )}
        {d.node_count != null && (
          <div className="flex gap-1">
            <span className="text-slate-400">Nodes</span>
            <span className="font-medium text-slate-700">{d.node_count}</span>
          </div>
        )}

        {/* Buckets */}
        {d.approximate_count != null && (
          <div className="flex gap-1">
            <span className="text-slate-400">Objects</span>
            <span className="font-medium text-slate-700">{d.approximate_count.toLocaleString()}</span>
          </div>
        )}
        {d.storage_tier && (
          <div className="flex gap-1">
            <span className="text-slate-400">Tier</span>
            <span className="font-medium text-slate-700">{d.storage_tier}</span>
          </div>
        )}

        {/* Attachment state (volumes) */}
        {d.attachment_state && (
          <div className="flex gap-1">
            <span className="text-slate-400">Disk</span>
            <span className={`font-medium ${d.attachment_state === 'UNATTACHED' ? 'text-rose-600' : 'text-emerald-700'}`}>
              {d.attachment_state}
            </span>
          </div>
        )}

        {/* Availability domain */}
        {d.availability_domain && (
          <div className="col-span-2 flex gap-1">
            <span className="text-slate-400">AD</span>
            <span className="font-medium text-slate-700 truncate">{d.availability_domain.split(':').pop()}</span>
          </div>
        )}

        {/* Image (VMs) */}
        {d.image_name && ['sql_server', 'windows_server', 'security_appliance', 'compute'].includes(resource.type) && (
          <div className="col-span-2 flex gap-1">
            <span className="shrink-0 text-slate-400">Image</span>
            <span className="font-medium text-slate-700 truncate" title={d.image_name}>{d.image_name}</span>
          </div>
        )}

        {/* NFS exports */}
        {Array.isArray(d.exports) && d.exports.length > 0 && (
          <div className="col-span-2 flex gap-1">
            <span className="text-slate-400">Exports</span>
            <span className="font-medium text-slate-700 truncate">{d.exports.map((e) => e.path).filter(Boolean).slice(0, 2).join(', ')}</span>
          </div>
        )}
      </div>

      {/* Allocation footer */}
      {(() => {
        const alloc = (v) => (v && v !== 'Unallocated' ? v : null);
        const env = alloc(resource.env);
        const team = alloc(resource.team);
        const app = alloc(resource.app);
        const conf = resource.allocation_confidence;
        if (!env && !team && !app) return null;
        return (
          <div className="mt-3 flex flex-wrap gap-1 border-t border-slate-100 pt-2">
            {env && <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-500">env: {env}</span>}
            {team && <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-500">team: {team}</span>}
            {app && <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-500">app: {app}</span>}
            {conf && conf !== 'low' && (
              <span className={`rounded px-1.5 py-0.5 text-[11px] ${conf === 'high' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
                {conf} confidence
              </span>
            )}
          </div>
        );
      })()}
    </div>
  );
}

function Resources() {
  const [loading, setLoading] = useState(true);
  const [resources, setResources] = useState([]);
  const [filter, setFilter] = useState('all');
  const [refreshing, setRefreshing] = useState(false);
  const [compartments, setCompartments] = useState([]);
  const [compartmentId, setCompartmentId] = useState('');
  const [counts, setCounts] = useState({ all: 0 });
  const [period, setPeriod] = useState('monthly');
  const [envFilter, setEnvFilter] = useState('');
  const [teamFilter, setTeamFilter] = useState('');
  const [appFilter, setAppFilter] = useState('');
  const [unownedOnly, setUnownedOnly] = useState(false);
  const [filterCost, setFilterCost] = useState(0);
  const [refreshTick, setRefreshTick] = useState(0);
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [costMap, setCostMap] = useState({});

  useEffect(() => {
    const t = setTimeout(() => setSearchQuery(searchInput), 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const filteredResources = resources;

  const fetchResources = async () => {
    try {
      setLoading(true);
      const params = {
        ...(filter !== 'all' ? { type: filter } : {}),
        ...(compartmentId ? { compartment_id: compartmentId } : {}),
        ...(searchQuery.trim() ? { search: searchQuery.trim() } : {}),
        limit: searchQuery.trim() ? 5000 : 1000,
      };
      const [res, costRes] = await Promise.all([
        getDataResources(params),
        getCostsByResource(_buildPeriodParams(period)).catch(() => null),
      ]);
      const map = {};
      for (const row of (costRes?.data?.data || [])) {
        if (row.resource_id && row.total_cost) map[row.resource_id] = row.total_cost;
      }
      setCostMap(map);
      let data = res.data.data || [];
      if (COST_TYPE_KEYS.includes(filter) && data.length === 0) {
        try {
          const byRes = await getCostsByResource(_buildPeriodParams(period));
          const fallbackRows = (byRes.data?.data || []).filter((r) => {
            const text = (r.skus || []).map((s) => (s.sku_name || '').toLowerCase()).join(' ');
            return detectTypeFromSkuText(text) === filter;
          });
          data = fallbackRows.slice(0, 300).map((r) => ({
            id: r.resource_id,
            name: resourceNameFromCostRow(r),
            type: filter,
            compartment_id: r.compartment_id || 'unknown',
            status: 'COST_DETECTED',
            shape: null,
            details: {
              image_name: 'Detected from OCI cost usage',
              image_family: filter,
              image_vendor: filter === 'security_appliance' ? 'security_vendor' : filter.includes('windows') || filter.includes('sql') ? 'microsoft' : null,
              total_cost_estimate: r.total_cost,
            },
          }));
        } catch {
          // keep empty fallback
        }
      }
      setResources(data);
    } catch (e) {
      console.error('Failed to fetch resources:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    // Load compartment tree from DB once
    (async () => {
      try {
        const tree = await getDataCompartmentTree();
        // Flatten tree to simple list of {id, name}
        const out = [];
        const walk = (node, prefix = '') => {
          out.push({ id: node.id, name: prefix ? `${prefix}/${node.name}` : node.name });
          (node.children || []).forEach(child => walk(child, prefix ? `${prefix}/${node.name}` : node.name));
        };
        if (tree?.data?.data) walk(tree.data.data);
        setCompartments(out);
      } catch {}
    })();
  }, []);

  useEffect(() => {
    fetchResources();
  }, [filter, compartmentId, period, refreshTick, searchQuery]);

  useEffect(() => {
    const loadCounts = async () => {
      try {
        const costRes = await getCostsByResource(_buildPeriodParams(period));
        const derived = {};
        for (const t of COST_TYPE_KEYS) derived[t] = new Set();
        (costRes.data?.data || []).forEach((r) => {
          const text = (r.skus || []).map((s) => (s.sku_name || '').toLowerCase()).join(' ');
          const t = detectTypeFromSkuText(text);
          if (t && derived[t]) derived[t].add(r.resource_id);
        });

        const entries = await Promise.all(
          TYPE_FILTERS.map(async (t) => {
            const params = {
              ...(t.key !== 'all' ? { type: t.key } : {}),
              ...(compartmentId ? { compartment_id: compartmentId } : {}),
              limit: 1,
            };
            const res = await getDataResources(params);
            let total = res.data?.meta?.total ?? 0;
            if (COST_TYPE_KEYS.includes(t.key) && total === 0) {
              total = derived[t.key]?.size || 0;
            }
            return [t.key, total];
          }),
        );
        setCounts(Object.fromEntries(entries));
      } catch {
        setCounts({ all: resources.length });
      }
    };
    loadCounts();
  }, [compartmentId, period, resources.length, refreshTick]);

  const _buildPeriodParams = (p) => {
    const now = new Date();
    const end = now.toISOString().slice(0, 10);
    const start = new Date(now);
    if (p === 'daily') {
      start.setDate(now.getDate() - 1);
    } else if (p === 'yearly') {
      start.setMonth(0, 1);
    } else if (p === 'past_year') {
      start.setDate(now.getDate() - 365);
    } else {
      start.setDate(1);
    }
    return { start_date: start.toISOString().slice(0, 10), end_date: end };
  };

  useEffect(() => {
    const loadFilterCost = async () => {
      try {
        const costRes = await getCostsByResource(_buildPeriodParams(period));
        const rows = costRes.data?.data || [];
        let total = 0;
        for (const r of rows) {
          const text = (r.skus || []).map((s) => (s.sku_name || '').toLowerCase()).join(' ');
          const type = filter;
          const match =
            type === 'all' ||
            (type === 'sql_server' && (text.includes('sql server') || text.includes('microsoft sql'))) ||
            (type === 'windows_server' && text.includes('windows os')) ||
            (type === 'security_appliance' && (text.includes('fortigate') || text.includes('palo alto') || text.includes('f5'))) ||
            (type === 'volume_backup' && text.includes('backup')) ||
            (type === 'nfs_file_system' && text.includes('file storage')) ||
            (type === 'block_volume' && text.includes('block volume'));
          if (match) total += r.total_cost || 0;
        }
        setFilterCost(total);
      } catch {
        setFilterCost(0);
      }
    };
    loadFilterCost();
  }, [filter, period]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await adminRunScan();
    } catch {
      // Keep best-effort behavior if scan fails.
    }
    await fetchResources();
    setRefreshTick((v) => v + 1);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-start justify-between gap-3 md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Resources</h1>
          <p className="text-sm text-slate-500">OCI inventory across compartments and service types</p>
          <p className="mt-1 text-sm font-medium text-cyan-700">Current filter cost: ${Math.round(filterCost).toLocaleString()}</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm"
          >
            <option value="daily">Daily</option>
            <option value="monthly">Monthly</option>
            <option value="yearly">Yearly</option>
            <option value="past_year">Past 12 Months</option>
          </select>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2.5 text-white transition hover:bg-sky-700 disabled:opacity-50"
          >
            <RefreshCw size={18} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="space-y-3 rounded-2xl border border-slate-200/80 bg-white/80 p-4 shadow-sm backdrop-blur">
        {/* Search box */}
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search by name or IP address…"
            className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-4 text-sm shadow-sm focus:border-sky-400 focus:outline-none focus:ring-1 focus:ring-sky-400"
          />
          {searchInput && (
            <button onClick={() => { setSearchInput(''); setSearchQuery(''); }} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs">✕</button>
          )}
        </div>
        {/* Resource type filters */}
        <div className="flex flex-wrap gap-2">
          {TYPE_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                filter === f.key
                  ? 'bg-sky-600 text-white'
                  : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
              }`}
            >
              {f.label} ({counts[f.key] ?? 0})
            </button>
          ))}
        </div>
        {/* Compartment filter */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-600">Compartment:</label>
          <select
            value={compartmentId}
            onChange={e => setCompartmentId(e.target.value)}
            className="min-w-[220px] rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm"
          >
            <option value="">All compartments</option>
            {compartments.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Resource Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      ) : filteredResources.length > 0 ? (
        <>
          {searchQuery && (
            <p className="text-sm text-slate-500">
              <span className="font-medium text-slate-700">{filteredResources.length}</span> results for <span className="font-medium text-slate-700">"{searchQuery}"</span>
            </p>
          )}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {filteredResources.map((resource) => (
              <ResourceCard key={resource.id} resource={resource} monthlyCost={costMap[resource.id] ?? null} />
            ))}
          </div>
        </>
      ) : searchQuery ? (
        <div className="rounded-2xl border border-slate-200/80 bg-white/90 p-12 text-center shadow-sm">
          <Search size={48} className="mx-auto mb-4 text-slate-300" />
          <p className="text-slate-500">No resources match "<span className="font-medium">{searchQuery}</span>"</p>
          <button onClick={() => { setSearchInput(''); setSearchQuery(''); }} className="mt-3 text-sm text-sky-600 hover:underline">Clear search</button>
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-200/80 bg-white/90 p-12 text-center shadow-sm">
          <Database size={48} className="mx-auto mb-4 text-slate-300" />
          <p className="text-slate-500">{UI_COPY.empty.noCostData}</p>
          <p className="mt-1 text-sm text-slate-400">{UI_COPY.detection.lowConfidence}</p>
        </div>
      )}
    </div>
  );
}

export default Resources;
