import axios from 'axios';

const API_BASE = '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000, // 30s timeout to absorb cold-cache and proxy delays
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // For HTTP-only cookies (auth)
});

const emitGlobalApiError = (error) => {
  const payload = {
    message: error?.response?.data?.error?.reason
      || error?.response?.data?.detail?.error?.reason
      || error?.response?.data?.detail
      || error?.message
      || 'API request failed',
    code: error?.response?.data?.error?.code
      || error?.response?.data?.detail?.error?.code
      || 'API_ERROR',
    correlation_id:
      error?.response?.headers?.['x-correlation-id']
      || error?.response?.data?.error?.correlation_id
      || error?.response?.data?.detail?.error?.correlation_id,
  };
  window.dispatchEvent(new CustomEvent('app:api-error', { detail: payload }));
};

const CORR_KEY = 'x_correlation_id';
const telemetryWindow = [];
const TELEMETRY_MAX_BURST = 5;
const TELEMETRY_INTERVAL_MS = 1000;

const ensureCorrelationId = () => {
  let cid = localStorage.getItem(CORR_KEY);
  if (!cid) {
    if (window.crypto && window.crypto.randomUUID) {
      cid = window.crypto.randomUUID();
    } else {
      cid = `cid-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    }
    localStorage.setItem(CORR_KEY, cid);
  }
  return cid;
};

const redactDetails = (details = {}) => {
  const blocked = new Set(['password', 'token', 'secret', 'authorization', 'private_key', 'oci_key_content', 'key_content']);
  const walk = (value) => {
    if (Array.isArray(value)) return value.map(walk);
    if (value && typeof value === 'object') {
      return Object.fromEntries(
        Object.entries(value).map(([k, v]) => [k, blocked.has(String(k).toLowerCase()) ? '***REDACTED***' : walk(v)]),
      );
    }
    return value;
  };
  return walk(details);
};

export const sendFrontendLog = ({ level = 'info', message, route, details = {} }) => {
  const now = Date.now();
  while (telemetryWindow.length > 0 && (now - telemetryWindow[0]) > TELEMETRY_INTERVAL_MS) {
    telemetryWindow.shift();
  }
  if (telemetryWindow.length >= TELEMETRY_MAX_BURST) return;
  telemetryWindow.push(now);

  const payload = {
    level,
    message: String(message || '').slice(0, 2000),
    route: route || window.location.pathname,
    correlation_id: ensureCorrelationId(),
    details: redactDetails(details),
  };

  fetch('/api/v1/logs/frontend', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Correlation-Id': ensureCorrelationId(),
    },
    body: JSON.stringify(payload),
    credentials: 'include',
    keepalive: true,
  }).catch(() => {});
};

api.interceptors.request.use((config) => {
  const cid = ensureCorrelationId();
  config.headers = config.headers || {};
  config.headers['X-Correlation-Id'] = cid;
  return config;
});

api.interceptors.response.use(
  (response) => {
    const cid = response?.headers?.['x-correlation-id'];
    if (cid) localStorage.setItem(CORR_KEY, cid);
    return response;
  },
  async (error) => {
    const config = error?.config || {};
    const method = String(config?.method || 'get').toLowerCase();
    const isTimeoutOrNetwork = error?.code === 'ECONNABORTED' || !error?.response;
    const canRetry = method === 'get' && isTimeoutOrNetwork && !config.__retryOnce;

    if (canRetry) {
      config.__retryOnce = true;
      await new Promise((resolve) => setTimeout(resolve, 350));
      return api.request(config);
    }

    const url = config?.url || '';
    const status = error?.response?.status;
    const suppressAuthTransitionError = status === 401 && url.includes('/admin/logout');

    if (!url.includes('/logs/frontend') && !suppressAuthTransitionError) {
      sendFrontendLog({
        level: 'error',
        message: 'api_request_failed',
        route: window.location.pathname,
        details: {
          url,
          method,
          status,
          data: error?.response?.data,
          code: error?.code,
        },
      });
    }

    if (!suppressAuthTransitionError) {
      emitGlobalApiError(error);
    }

    return Promise.reject(error);
  },
);

// ============ DB-backed endpoints (fast, cached) ============
// These read from the local database populated by the background scanner

// Data: Resources from DB
export const getDataResources = (params = {}) => api.get('/data/resources', { params });

// Data: Compartments tree from DB
export const getDataCompartmentTree = () => api.get('/data/compartments/tree');

// Data: Costs from DB
export const getDataCosts = (params = {}) => api.get('/data/costs', { params });

// Data: Trends from DB
export const getDataTrends = (months = 6) => api.get('/data/trends', { params: { months } });

// ============ Admin endpoints ============
export const adminLogin = (username, password) => api.post('/admin/login', { username, password });
export const adminGetSettings = () => api.get('/admin/settings');
export const adminUpdateSettings = (data) => api.put('/admin/settings', data);
export const adminTestOciConnection = (data) => api.post('/admin/settings/test-oci', data);
export const adminExportSnapshot = (data) => api.post('/admin/exports/snapshot', data);
export const adminGenerateExport = (data) => api.post('/admin/exports/generate', data);
export const adminListExports = () => api.get('/admin/exports/list');
export const adminDownloadExport = (name) => api.get(`/admin/exports/download/${encodeURIComponent(name)}`, { responseType: 'blob' });
export const adminRunScan = () => api.post('/admin/scan/run');
export const adminGetScanRuns = () => api.get('/admin/scan/runs');
export const adminGetImportantCompartments = () => api.get('/admin/settings/important-compartments');
export const adminSetImportantCompartments = (data) => api.post('/admin/settings/important-compartments', data);
export const adminLogout = () => api.post('/admin/logout');
export const adminGetFeatureFlags = () => api.get('/admin/settings/feature-flags');
export const adminUpdateFeatureFlags = (data) => api.post('/admin/settings/feature-flags', data);
export const saveOciSettings = (data) => api.post('/settings/oci', data);
export const uploadOciKey = (file) => {
  const form = new FormData();
  form.append('key_file', file);
  return api.post('/settings/oci/key', form, { headers: { 'Content-Type': 'multipart/form-data' } });
};
export const testOciSettings = () => api.post('/settings/oci/test');
export const getMe = () => api.get('/me');
export const getOpsMetrics = () => api.get('/ops/metrics');
export const getDiagnostics = () => api.get('/diagnostics');
export const refreshDiagnostics = (params = {}) => api.post('/jobs/diagnostics_refresh', { params });
export const getJobsSummary = () => api.get('/jobs/summary');
export const getLogs = (params = {}) => api.get('/logs', { params });
export const getLogsTimeline = (correlationId) => api.get(`/logs/${encodeURIComponent(correlationId)}`);
export const exportLogs = (data = {}) => api.post('/logs/export', data);

// ============ Legacy live OCI endpoints (slower) ============
// These call OCI APIs directly - kept for backwards compatibility

// Compartments
export const getCompartments = () => api.get('/compartments');
export const getCompartmentTree = () => api.get('/compartments/tree');

// Resources
export const getResources = (params = {}, config = {}) => api.get('/resources', { params, timeout: config.timeout || 35000 });
export const getResourcesSummary = () => api.get('/resources/summary');

// Costs
export const getCosts = (params = {}) => api.get('/costs', { params });
export const getCostsByResource = (params = {}, config = {}) =>
  api.get('/costs/by-resource', { params, timeout: config.timeout || 60000 });
export const getDatabaseCosts = (params = {}) => api.get('/costs/databases', { params });
export const getCostTrends = (months = 6, refresh = false) => api.get('/costs/trends', { params: { months, refresh } });
export const getTopResources = (limit = 10) => api.get('/costs/top-resources', { params: { limit } });
const mapRangeFromParams = (params = {}) => {
  if (params.range) return params.range;
  return 'prev_month';
};
const toIsoDate = (value) => (typeof value === 'string' ? value : new Date(value).toISOString().slice(0, 10));
const resolveDateRange = (params = {}) => {
  if (params.start_date && params.end_date) {
    return {
      start_date: toIsoDate(params.start_date),
      end_date: toIsoDate(params.end_date),
    };
  }
  const now = new Date();
  const range = mapRangeFromParams(params);
  if (range === 'ytd') {
    return {
      start_date: `${now.getFullYear()}-01-01`,
      end_date: toIsoDate(now),
    };
  }
  if (range === 'prev_year' || range === 'yearly') {
    const y = now.getFullYear() - 1;
    return {
      start_date: `${y}-01-01`,
      end_date: `${y}-12-31`,
    };
  }
  const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const end = new Date(now.getFullYear(), now.getMonth(), 0);
  return {
    start_date: toIsoDate(start),
    end_date: toIsoDate(end),
  };
};
export const getCostSummary = (params = {}) => {
  const { start_date, end_date } = resolveDateRange(params);
  return api.get('/dashboard/summary', { params: { start_date, end_date, compare: 'previous' } }).then((res) => {
    const d = res?.data?.data || {};
    return {
      ...res,
      data: {
        ...res.data,
        data: {
          total: d?.totals?.current || 0,
          delta_abs: d?.totals?.delta_abs || 0,
          delta_pct: d?.totals?.delta_pct || 0,
          top_driver: { entity: d?.top_driver?.group || 'No data', share: d?.top_driver?.share_pct || 0 },
          biggest_mover: {
            entity: d?.biggest_mover?.entity_name || 'No data',
            delta_abs: d?.biggest_mover?.delta_abs || 0,
            delta_pct: d?.biggest_mover?.delta_pct || 0,
          },
          unallocated: { count: 0, pct: d?.mapping_health?.unallocated_pct || 0 },
          last_computed_at: d?.generated_at || null,
          stale: false,
        },
      },
    };
  });
};
export const getCostBreakdown = (params = {}) => {
  const { start_date, end_date } = resolveDateRange(params);
  const group_by = params.group_by || 'service';
  const compare = params.compare || 'previous';
  const limit = params.limit || 20;
  const min_share_pct = params.min_share_pct ?? 0;
  return api.get('/costs/breakdown', { params: { group_by, start_date, end_date, compare, limit, min_share_pct } }).then((res) => ({
    ...res,
    data: {
      ...res.data,
      data: {
        items: res?.data?.data?.items || [],
        mapping_health: res?.data?.data?.mapping_health || { unowned_cost: 0, low_confidence_cost: 0 },
      },
    },
  }));
};
export const getCostMovers = (params = {}) => {
  const { start_date, end_date } = resolveDateRange(params);
  const group_by = params.group_by || 'service';
  const compare = params.compare || 'previous';
  const limit = params.limit || 20;
  const direction = params.direction || 'up';
  return api.get('/costs/movers', { params: { group_by, start_date, end_date, compare, limit, direction } }).then((res) => ({
    ...res,
    data: {
      ...res.data,
      data: { items: res?.data?.data?.items || [] },
    },
  }));
};
export const getInsights = (params = {}) => api.get('/costs/insights', { params });
export const getDashboardSummary = (params = {}) => api.get('/dashboard/summary', { params });
export const getTagCoverage = (params = {}) => api.get('/governance/tag-coverage', { params });
export const adminGetAllocationRules = () => api.get('/admin/allocation-rules');
export const adminCreateAllocationRule = (data) => api.post('/admin/allocation-rules', data);
export const adminUpdateAllocationRule = (id, data) => api.put(`/admin/allocation-rules/${id}`, data);
export const adminDeleteAllocationRule = (id) => api.delete(`/admin/allocation-rules/${id}`);
const _toIsoDate = (value) => (typeof value === 'string' ? value : new Date(value).toISOString().slice(0, 10));

export const dashboardSummary = ({ start_date, end_date }) =>
  api.get('/dashboard/summary', {
    params: {
      start_date: _toIsoDate(start_date),
      end_date: _toIsoDate(end_date),
    },
  });
export const costsBreakdown = ({
  group_by = 'service',
  start_date,
  end_date,
  compare = 'previous',
  limit = 8,
  min_share_pct = 0.5,
}) => {
  return api.get('/costs/breakdown', {
    params: {
      group_by,
      start_date: _toIsoDate(start_date),
      end_date: _toIsoDate(end_date),
      compare,
      limit,
      min_share_pct,
    },
  });
};
export const costsMovers = ({
  group_by = 'service',
  start_date,
  end_date,
  compare = 'previous',
  limit = 10,
  direction = 'up',
}) => {
  return api.get('/costs/movers', {
    params: {
      group_by,
      start_date: _toIsoDate(start_date),
      end_date: _toIsoDate(end_date),
      compare,
      limit,
      direction,
    },
  });
};

// Explicit V2 bindings used by Dashboard to avoid legacy wrapper ambiguity.
export const dashboardSummaryV2 = ({ start_date, end_date }) =>
  api.get('/dashboard/summary', {
    params: {
      start_date: _toIsoDate(start_date),
      end_date: _toIsoDate(end_date),
    },
  });

export const costsBreakdownV2 = ({
  group_by = 'service',
  start_date,
  end_date,
  compare = 'previous',
  limit = 8,
  min_share_pct = 0.5,
}) =>
  api.get('/costs/breakdown', {
    params: {
      group_by,
      start_date: _toIsoDate(start_date),
      end_date: _toIsoDate(end_date),
      compare,
      limit,
      min_share_pct,
    },
  });

export const costsMoversV2 = ({
  group_by = 'service',
  start_date,
  end_date,
  compare = 'previous',
  limit = 10,
  direction = 'up',
}) =>
  api.get('/costs/movers', {
    params: {
      group_by,
      start_date: _toIsoDate(start_date),
      end_date: _toIsoDate(end_date),
      compare,
      limit,
      direction,
    },
  });
export const recommendationsSummary = ({ start_date, end_date }) => {
  const params = {
    start_date: typeof start_date === 'string' ? start_date : new Date(start_date).toISOString().slice(0, 10),
    end_date: typeof end_date === 'string' ? end_date : new Date(end_date).toISOString().slice(0, 10),
  };
  return api.get('/recommendations/summary', { params });
};
export const recommendationsList = ({
  start_date,
  end_date,
  category,
  confidence,
  compartment_id,
  team,
  app,
  env,
}) => {
  const params = {
    start_date: typeof start_date === 'string' ? start_date : new Date(start_date).toISOString().slice(0, 10),
    end_date: typeof end_date === 'string' ? end_date : new Date(end_date).toISOString().slice(0, 10),
    category,
    confidence,
    compartment_id,
    team,
    app,
    env,
  };
  return api.get('/recommendations/list', { params });
};
export const recommendationById = ({ recommendation_id, start_date, end_date }) => {
  const params = {
    start_date: typeof start_date === 'string' ? start_date : new Date(start_date).toISOString().slice(0, 10),
    end_date: typeof end_date === 'string' ? end_date : new Date(end_date).toISOString().slice(0, 10),
  };
  return api.get(`/recommendations/resource/${encodeURIComponent(recommendation_id)}`, { params });
};

// Cache
export const getCacheStatus = () => api.get('/cache');
export const clearCache = () => api.delete('/cache');

// Budgets
export const validateBudget = (data) => api.post('/budgets/validate', data);
export const checkBudget = (budget, period = 'monthly') => 
  api.get('/budgets/check', { params: { budget, period } });
export const getBudgetForecast = (budget, period = 'monthly') =>
  api.get('/budgets/forecast', { params: { budget, period } });
export const listBudgets = (config = {}) => api.get('/budgets', { timeout: config.timeout || 30000 });
export const createBudget = (data) => api.post('/budgets', data);
export const updateBudget = (budgetId, data) => api.put(`/budgets/${encodeURIComponent(budgetId)}`, data);
export const deleteBudget = (budgetId) => api.delete(`/budgets/${encodeURIComponent(budgetId)}`);
export const budgetStatus = (config = {}) => api.get('/budgets/status', { timeout: config.timeout || 45000 });
export const budgetHistory = (budget_id) => api.get('/budgets/history', { params: { budget_id } });

// Actions (Phase 5)
export const createAction = (data) => api.post('/actions', data);
export const listActions = (params = {}) => api.get('/actions', { params });
export const getAction = (actionId) => api.get(`/actions/${encodeURIComponent(actionId)}`);
export const approveAction = (actionId, data = {}) => api.post(`/actions/${encodeURIComponent(actionId)}/approve`, data);
export const rejectAction = (actionId, data = {}) => api.post(`/actions/${encodeURIComponent(actionId)}/reject`, data);
export const runAction = (actionId, data = {}) => api.post(`/actions/${encodeURIComponent(actionId)}/run`, data);
export const rollbackAction = (actionId, data = {}) => api.post(`/actions/${encodeURIComponent(actionId)}/rollback`, data);

// Prices
export const getPrices = (params = {}) => api.get('/prices', { params });
export const getDatabasePrices = (region) => api.get('/prices/databases', { params: { region } });
export const refreshPrices = () => api.post('/prices/refresh');

// Health
export const checkHealth = () => api.get('/health');
export const checkHealthLive = () => api.get('/health/live');
export const checkHealthReady = () => api.get('/health/ready');
export const checkOCIHealth = () => api.get('/health/oci');

// Daily cost breakdown (OCI Cost Analysis view)
export const getDailyCosts = (params = {}) => api.get('/costs/daily', { params });

// Universal Credits subscriptions
export const getSubscriptions = () => api.get('/subscriptions');

export default api;

export const adminGetPortalSslSettings = () => api.get('/settings/portal-ssl');
export const adminUploadPortalSsl = (formData, config = {}) => api.post('/settings/portal-ssl/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: config.timeout || 90000 });

export const adminListUsers = () => api.get('/admin/users');
export const adminCreateUser = (data) => api.post('/admin/users', data);
export const adminUpdateUser = (userId, data) => api.put(`/admin/users/${encodeURIComponent(userId)}`, data);
