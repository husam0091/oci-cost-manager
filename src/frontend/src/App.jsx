import { useEffect, useMemo, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Database,
  DollarSign,
  PiggyBank,
  Settings as SettingsIcon,
  FileSpreadsheet,
  Menu,
  X,
  ShieldCheck,
  UserCog,
  Wrench,
  Sparkles,
  ScrollText,
} from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Resources from './pages/Resources';
import Costs from './pages/Costs';
import Budget from './pages/Budget';
import Settings from './pages/Settings';
import { parseBooleanFlag } from './utils/flags';
import ExportReports from './pages/ExportReports';
import Governance from './pages/Governance';
import Recommendations from './pages/Recommendations';
import Actions from './pages/Actions';
import Logs from './pages/Logs';
import GlobalStatusBar from './components/GlobalStatusBar';
import { getMe } from './services/api';

const PERSONA_ORDER = {
  Executive: ['/', '/budget', '/exports', '/costs', '/recommendations', '/governance', '/resources', '/actions', '/logs', '/settings'],
  FinOps: ['/costs', '/budget', '/exports', '/governance', '/logs', '/', '/recommendations', '/resources', '/actions', '/settings'],
  Engineer: ['/resources', '/recommendations', '/actions', '/costs', '/governance', '/budget', '/exports', '/', '/logs', '/settings'],
};

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/resources', icon: Database, label: 'Resources' },
  { path: '/costs', icon: DollarSign, label: 'Costs' },
  { path: '/budget', icon: PiggyBank, label: 'Budget' },
  { path: '/exports', icon: FileSpreadsheet, label: 'Export Reports' },
  { path: '/governance', icon: ShieldCheck, label: 'Governance' },
  { path: '/recommendations', icon: Sparkles, label: 'Recommendations' },
  { path: '/actions', icon: Wrench, label: 'Actions' },
  { path: '/logs', icon: ScrollText, label: 'Logs & Diagnostics' },
  { path: '/settings', icon: SettingsIcon, label: 'Settings & Profile' },
];

function Sidebar({ mobileOpen, onClose, profileName, persona }) {
  const location = useLocation();
  const sortedItems = [...navItems].sort(
    (a, b) => PERSONA_ORDER[persona].indexOf(a.path) - PERSONA_ORDER[persona].indexOf(b.path),
  );

  return (
    <>
      <div
        className={`fixed inset-0 z-30 bg-slate-950/45 backdrop-blur-sm transition-opacity lg:hidden ${
          mobileOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
        onClick={onClose}
      />
      <aside
        className={`sidebar-surface fixed left-0 top-0 z-40 h-full w-[300px] transform border-r border-white/20 p-5 text-slate-100 shadow-2xl shadow-slate-950/30 backdrop-blur-xl transition-transform duration-200 ease-out lg:static lg:z-10 lg:h-auto lg:min-h-full lg:w-80 lg:translate-x-0 lg:self-stretch ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="mb-8 flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">OCI Cost Manager</h1>
            <p className="mt-1 text-sm text-slate-400">Cost intelligence console</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-2 text-slate-300 hover:bg-slate-800 lg:hidden"
            aria-label="Close navigation"
          >
            <X size={18} />
          </button>
        </div>

        <div className="mb-5 rounded-xl border border-cyan-300/25 bg-cyan-300/15 px-3 py-2 text-xs text-cyan-100">
          Live cost control with integration diagnostics
        </div>

        <nav className="space-y-1">
          {sortedItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
                  isActive
                    ? 'bg-cyan-300 text-slate-950 shadow-[0_8px_22px_rgba(34,211,238,0.35)]'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                <Icon size={18} />
                <span className="font-medium">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="mt-8 rounded-xl border border-white/10 bg-slate-950/35 p-3">
          <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wide text-slate-400">
            <ShieldCheck size={14} />
            Session
          </div>
          <div className="flex items-center justify-between rounded-lg bg-slate-800/70 px-3 py-2 text-sm">
            <span className="text-slate-300">Profile</span>
            <span className="font-medium text-slate-100">{profileName || 'admin'}</span>
          </div>
          <Link
            to="/settings"
            onClick={onClose}
            className="mt-2 flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-cyan-300 transition hover:bg-slate-800 hover:text-cyan-200"
          >
            <UserCog size={16} />
            Setup Profile
          </Link>
        </div>
      </aside>
    </>
  );
}

function AppLayout() {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [authChecking, setAuthChecking] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [profileName, setProfileName] = useState('admin');
  const [role, setRole] = useState('admin');
  const [persona, setPersona] = useState(localStorage.getItem('ui_persona') || 'Executive');
  const [appVersion, setAppVersion] = useState('1.0.0');
  const [demoMode, setDemoMode] = useState(false);
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    let mounted = true;
    const checkAuth = async () => {
      try {
        const me = await getMe();
        if (!mounted) return;
        if (me.data?.success) {
          setAuthenticated(true);
          setProfileName(me.data?.data?.username || 'user');
          setRole(me.data?.data?.role || 'viewer');
          setAppVersion(me.data?.data?.app_version || '1.0.0');
          setDemoMode(parseBooleanFlag(me.data?.data?.feature_flags?.enable_demo_mode));
        } else {
          setAuthenticated(false);
        }
      } catch {
        if (mounted) setAuthenticated(false);
      } finally {
        if (mounted) setAuthChecking(false);
      }
    };
    checkAuth();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const onApiError = (evt) => {
      const detail = evt?.detail || {};
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      setToasts((prev) => [...prev, { id, ...detail }].slice(-4));
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 7000);
    };
    window.addEventListener('app:api-error', onApiError);
    return () => window.removeEventListener('app:api-error', onApiError);
  }, []);

  const pageTitle = useMemo(() => {
    const match = navItems.find((item) => item.path === location.pathname);
    return match ? match.label : 'OCI Cost Manager';
  }, [location.pathname]);

  if (authChecking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-app-gradient">
        <div className="h-12 w-12 animate-spin rounded-full border-b-2 border-sky-600" />
      </div>
    );
  }

  if (!authenticated) {
    return (
      <div className="min-h-screen bg-app-gradient p-4 lg:p-8">
        <Settings onAuthChange={(value, username) => {
          setAuthenticated(value);
          if (username) setProfileName(username);
        }} forceLogin />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-app-gradient text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-[1800px]">
        <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} profileName={profileName} persona={persona} />
        <main className="w-full flex-1">
          <div className="fixed right-4 top-4 z-50 space-y-2">
            {toasts.map((t) => (
              <div key={t.id} className="max-w-sm rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800 shadow">
                <div className="font-medium">{t.code || 'API_ERROR'}</div>
                <div>{t.message || 'Request failed'}</div>
                {t.correlation_id ? <div className="mt-1 text-xs text-rose-700">Correlation: {t.correlation_id}</div> : null}
              </div>
            ))}
          </div>
          <header className="sticky top-0 z-20 border-b border-slate-200/70 bg-white/85 px-4 py-3 backdrop-blur lg:px-8">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  className="rounded-md border border-slate-300 bg-white p-2 text-slate-700 hover:bg-slate-100 lg:hidden"
                  onClick={() => setMobileOpen(true)}
                  aria-label="Open navigation"
                >
                  <Menu size={18} />
                </button>
                <div>
                  <p className="text-xs font-medium uppercase tracking-[0.14em] text-slate-500">Workspace</p>
                  <h2 className="text-lg font-semibold tracking-tight text-slate-900">{pageTitle}</h2>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <select
                  value={persona}
                  onChange={(e) => {
                    setPersona(e.target.value);
                    localStorage.setItem('ui_persona', e.target.value);
                  }}
                  className="hidden rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-700 sm:block"
                >
                  <option>Executive</option>
                  <option>FinOps</option>
                  <option>Engineer</option>
                </select>
                <div className="hidden rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-1.5 text-xs font-medium text-cyan-700 sm:block">
                  Role: {role}
                </div>
                {demoMode ? (
                  <div className="hidden rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 sm:block">
                    Demo mode: read-only
                  </div>
                ) : null}
              </div>
            </div>
          </header>

          <section className="p-4 lg:p-8">
            <GlobalStatusBar />
            <Routes>
              <Route path="/" element={<Dashboard persona={persona} />} />
              <Route path="/resources" element={<Resources />} />
              <Route path="/costs" element={<Costs />} />
              <Route path="/budget" element={<Budget />} />
              <Route path="/exports" element={<ExportReports />} />
              <Route path="/governance" element={<Governance />} />
              <Route path="/recommendations" element={<Recommendations />} />
              <Route path="/actions" element={<Actions />} />
              <Route path="/logs" element={<Logs role={role} />} />
              <Route
                path="/settings"
                element={
                  <Settings
                    onAuthChange={(value, username) => {
                      setAuthenticated(value);
                      if (username) setProfileName(username);
                    }}
                  />
                }
              />
            </Routes>
          </section>
          <footer className="border-t border-slate-200/70 bg-white/70 px-4 py-2 text-right text-xs text-slate-600 lg:px-8">
            OCI Cost Manager v{appVersion}
          </footer>
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppLayout />
    </Router>
  );
}

export default App;
