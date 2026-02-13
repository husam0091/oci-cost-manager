import { useState, useEffect } from 'react';
import { Database, Server, HardDrive, RefreshCw, Monitor, Folder, Archive, Shield, Package, Save } from 'lucide-react';
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

function ResourceCard({ resource }) {
  const config = typeConfig[resource.type] || { icon: HardDrive, color: 'bg-gray-100', label: resource.type };
  const Icon = config.icon;
  const displayName = resource.name && resource.name.startsWith('ocid1.')
    ? `Resource ...${resource.name.slice(-16)}`
    : (resource.name || 'Unnamed resource');
  
  return (
    <div className="rounded-xl border border-slate-200/80 bg-white/90 p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${config.color}`}>
            <Icon size={20} />
          </div>
          <div>
            <h3 className="max-w-[190px] truncate font-semibold text-slate-800" title={resource.name}>
              {displayName}
            </h3>
            <p className="text-sm text-slate-500">{config.label}</p>
          </div>
        </div>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
          resource.status === 'AVAILABLE' || resource.status === 'RUNNING' || resource.status === 'ACTIVE'
            ? 'bg-green-100 text-green-700'
            : 'bg-yellow-100 text-yellow-700'
        }`}>
          {resource.status}
        </span>
      </div>
      
      <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
        <div className="col-span-2 flex flex-wrap gap-2">
          <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">env: {resource.env || 'Unallocated'}</span>
          <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">team: {resource.team || 'Unallocated'}</span>
          <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">app: {resource.app || 'Unallocated'}</span>
          <span className={`rounded-full px-2 py-1 text-xs ${resource.allocation_confidence === 'high' ? 'bg-emerald-50 text-emerald-700' : resource.allocation_confidence === 'medium' ? 'bg-amber-50 text-amber-800' : 'bg-rose-50 text-rose-700'}`}>
            {resource.allocation_confidence || 'low'}
          </span>
        </div>
        {/* Shape - for DBs and VMs */}
        {resource.shape && (
          <div className="col-span-2">
            <span className="text-gray-500">Shape:</span>
            <span className="ml-1 text-gray-700 text-xs">{resource.shape}</span>
          </div>
        )}
        
        {/* OCPUs - for VMs and DBs */}
        {(resource.details?.cpu_core_count || resource.details?.ocpus) && (
          <div>
            <span className="text-gray-500">OCPUs:</span>
            <span className="ml-1 text-gray-700">{resource.details.cpu_core_count || resource.details.ocpus}</span>
          </div>
        )}
        
        {/* Memory - for VMs */}
        {resource.details?.memory_in_gbs && (
          <div>
            <span className="text-gray-500">Memory:</span>
            <span className="ml-1 text-gray-700">{resource.details.memory_in_gbs} GB</span>
          </div>
        )}
        
        {/* Private IP - for VMs */}
        {resource.details?.private_ip && (
          <div className="col-span-2">
            <span className="text-gray-500">Private IP:</span>
            <span className="ml-1 text-gray-700 font-mono text-xs">{resource.details.private_ip}</span>
          </div>
        )}
        
        {/* Edition - for Oracle DBs */}
        {resource.details?.edition && (
          <div className="col-span-2">
            <span className="text-gray-500">Edition:</span>
            <span className="ml-1 text-gray-700 text-xs">{resource.details.edition.replace(/_/g, ' ')}</span>
          </div>
        )}
        
        {/* Storage - for DBs */}
        {resource.details?.data_storage_size_in_gbs && (
          <div>
            <span className="text-gray-500">Storage:</span>
            <span className="ml-1 text-gray-700">{resource.details.data_storage_size_in_gbs} GB</span>
          </div>
        )}
        
        {/* Size display - for File Storage and Buckets */}
        {resource.details?.size_display && (
          <div>
            <span className="text-gray-500">Size:</span>
            <span className="ml-1 text-gray-700">{resource.details.size_display}</span>
          </div>
        )}
        
        {/* Object count - for Buckets */}
        {resource.details?.approximate_count != null && (
          <div>
            <span className="text-gray-500">Objects:</span>
            <span className="ml-1 text-gray-700">{resource.details.approximate_count.toLocaleString()}</span>
          </div>
        )}
        
        {/* Storage tier - for Buckets */}
        {resource.details?.storage_tier && (
          <div>
            <span className="text-gray-500">Tier:</span>
            <span className="ml-1 text-gray-700">{resource.details.storage_tier}</span>
          </div>
        )}
        
        {/* Image name - for VM workloads */}
        {resource.details?.image_name && ['sql_server', 'windows_server', 'security_appliance', 'compute'].includes(resource.type) && (
          <div className="col-span-2">
            <span className="text-gray-500">Image:</span>
            <span className="ml-1 text-gray-700 text-xs truncate block" title={resource.details.image_name}>
              {resource.details.image_name}
            </span>
          </div>
        )}

        {resource.details?.image_vendor && (
          <div>
            <span className="text-gray-500">Vendor:</span>
            <span className="ml-1 text-gray-700">{resource.details.image_vendor}</span>
          </div>
        )}

        {resource.details?.total_cost_estimate != null && (
          <div className="col-span-2">
            <span className="text-gray-500">Estimated Cost:</span>
            <span className="ml-1 text-gray-700">${Math.round(resource.details.total_cost_estimate).toLocaleString()}</span>
          </div>
        )}

        {resource.details?.attachment_state && (
          <div>
            <span className="text-gray-500">Attachment:</span>
            <span className={`ml-1 font-medium ${resource.details.attachment_state === 'UNATTACHED' ? 'text-rose-600' : 'text-emerald-700'}`}>
              {resource.details.attachment_state}
            </span>
          </div>
        )}

        {resource.details?.protocol && (
          <div>
            <span className="text-gray-500">Protocol:</span>
            <span className="ml-1 text-gray-700">{resource.details.protocol}</span>
          </div>
        )}

        {Array.isArray(resource.details?.exports) && resource.details.exports.length > 0 && (
          <div className="col-span-2">
            <span className="text-gray-500">NFS Exports:</span>
            <span className="ml-1 text-gray-700 text-xs">
              {resource.details.exports.map((e) => e.path).filter(Boolean).slice(0, 3).join(', ')}
            </span>
          </div>
        )}
      </div>
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

  const fetchResources = async () => {
    try {
      setLoading(true);
      const params = {
        ...(filter !== 'all' ? { type: filter } : {}),
        ...(compartmentId ? { compartment_id: compartmentId } : {}),
        ...(envFilter ? { env: envFilter } : {}),
        ...(teamFilter ? { team: teamFilter } : {}),
        ...(appFilter ? { app: appFilter } : {}),
        ...(unownedOnly ? { unowned_only: true } : {}),
        limit: 1000,
      };
      const res = await getDataResources(params);
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
  }, [filter, compartmentId, period, refreshTick, envFilter, teamFilter, appFilter, unownedOnly]);

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
        <div className="grid grid-cols-1 gap-2 md:grid-cols-4">
          <input value={envFilter} onChange={(e) => setEnvFilter(e.target.value)} placeholder="Env filter" className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm" />
          <input value={teamFilter} onChange={(e) => setTeamFilter(e.target.value)} placeholder="Team filter" className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm" />
          <input value={appFilter} onChange={(e) => setAppFilter(e.target.value)} placeholder="App filter" className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm" />
          <label className="flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm">
            <input type="checkbox" checked={unownedOnly} onChange={(e) => setUnownedOnly(e.target.checked)} />
            Show only unowned
          </label>
        </div>
      </div>

      {/* Resource Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      ) : resources.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {resources.map((resource) => (
            <ResourceCard key={resource.id} resource={resource} />
          ))}
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
