import { useEffect, useMemo, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Database, DollarSign, PiggyBank, Settings as SettingsIcon, FileSpreadsheet, Menu, X, ShieldCheck, ChevronRight, Layers3, Wrench, Sparkles, ScrollText, Sun, Moon } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Overview from './pages/Overview';
import { BUILD_INFO } from './buildInfo';
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
import { getMe, adminGetRegions } from './services/api';
const PERSONA_ORDER = {
  Executive: ['/', '/budget', '/exports', '/costs', '/recommendations', '/governance', '/resources', '/actions', '/logs', '/settings'],
  FinOps: ['/costs', '/budget', '/exports', '/governance', '/logs', '/', '/recommendations', '/resources', '/actions', '/settings'],
  Engineer: ['/resources', '/recommendations', '/actions', '/costs', '/governance', '/budget', '/exports', '/', '/logs', '/settings']
};
const navItems = [{
  path: '/',
  icon: LayoutDashboard,
  label: 'Overview'
}, {
  path: '/resources',
  icon: Database,
  label: 'Resources'
}, {
  path: '/costs',
  icon: DollarSign,
  label: 'Spend explorer'
}, {
  path: '/budget',
  icon: PiggyBank,
  label: 'Budgets'
}, {
  path: '/exports',
  icon: FileSpreadsheet,
  label: 'Reports'
}, {
  path: '/governance',
  icon: ShieldCheck,
  label: 'Governance'
}, {
  path: '/recommendations',
  icon: Sparkles,
  label: 'Recommendations'
}, {
  path: '/actions',
  icon: Wrench,
  label: 'Actions'
}, {
  path: '/logs',
  icon: ScrollText,
  label: 'Diagnostics'
}, {
  path: '/settings',
  icon: SettingsIcon,
  label: 'Settings'
}];
function Sidebar({
  mobileOpen,
  onClose,
  profileName,
  persona
}) {
  const location = useLocation();
  const sortedItems = [...navItems].sort((a, b) => PERSONA_ORDER[persona].indexOf(a.path) - PERSONA_ORDER[persona].indexOf(b.path));
  return <>
      <div className={`fixed inset-0 z-30 bg-slate-950/45 backdrop-blur-sm transition-opacity lg:hidden ${mobileOpen ? 'opacity-100' : 'pointer-events-none opacity-0'}`} onClick={onClose} />
      <aside className={`workspace-sidebar ${mobileOpen ? 'is-open' : ''}`}>
        <Link className="workspace-brand" to="/" onClick={onClose}>
          <span className="workspace-logo"><Layers3 size={23} /></span>
          <span>OCI Cost Manager<small>FINOPS WORKSPACE</small></span>
        </Link>
        <button className="sidebar-close lg:hidden" onClick={onClose} aria-label="Close navigation"><X size={18} /></button>
        <p className="workspace-nav-label">WORKSPACE</p>
        <nav aria-label="Main navigation" className="workspace-navigation">
          {sortedItems.map(item => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;
          return <Link key={item.path} to={item.path} onClick={onClose} aria-current={isActive ? 'page' : undefined} className={isActive ? 'is-active' : ''}>
              <Icon size={18} /><span>{item.label}</span>{isActive && <ChevronRight size={14} className="nav-chevron" />}
            </Link>;
        })}
        </nav>
        <div className="sidebar-guidance"><ShieldCheck size={17} /><div>Clarity before action<small>Review billed usage and licensing before changing a workload.</small></div></div>
        <div className="workspace-session">
          <span className="workspace-avatar">{(profileName || 'U').slice(0, 2).toUpperCase()}</span>
          <Link to="/settings" onClick={onClose}><strong>{profileName || 'User'}</strong><small>Profile & preferences</small></Link>
        </div>
        <span className="sidebar-release">Interface {BUILD_INFO.uiVersion}</span>
      </aside>
    </>;
}
function AppLayout() {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [authChecking, setAuthChecking] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [profileName, setProfileName] = useState('admin');
  const [role, setRole] = useState('admin');
  const [persona, setPersona] = useState(() => {
    const saved = localStorage.getItem('ui_persona');
    return PERSONA_ORDER[saved] ? saved : 'Executive';
  });
  const [appVersion, setAppVersion] = useState('1.0.0');
  const [demoMode, setDemoMode] = useState(false);
  const [toasts, setToasts] = useState([]);
  const [activeRegion, setActiveRegion] = useState(localStorage.getItem('ui_active_region') || 'all');
  const [availableRegions, setAvailableRegions] = useState([]);
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('ui_dark_mode') === 'true');
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
          try {
            const regRes = await adminGetRegions();
            if (regRes.data?.success) {
              const {
                primary_region,
                enabled_regions
              } = regRes.data.data;
              const all = [...new Set([primary_region, ...(enabled_regions || [])].filter(Boolean))];
              setAvailableRegions(all);
            }
          } catch {/* regions endpoint requires admin — ignore for non-admin */}
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
    const root = document.documentElement;
    if (darkMode) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('ui_dark_mode', String(darkMode));
  }, [darkMode]);
  useEffect(() => {
    const onApiError = evt => {
      const detail = evt?.detail || {};
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      setToasts(prev => [...prev, {
        id,
        ...detail
      }].slice(-4));
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id));
      }, 7000);
    };
    window.addEventListener('app:api-error', onApiError);
    return () => window.removeEventListener('app:api-error', onApiError);
  }, []);
  const pageTitle = useMemo(() => {
    const match = navItems.find(item => item.path === location.pathname);
    return match ? match.label : location.pathname === '/analytics' ? 'Detailed analytics' : 'OCI Cost Manager';
  }, [location.pathname]);
  if (authChecking) {
    return <div className="flex min-h-screen items-center justify-center bg-app-gradient">
        <div className="h-12 w-12 animate-spin rounded-full border-b-2 border-sky-600" />
      </div>;
  }
  if (!authenticated) {
    return <div className="finops-app workspace-login">
      <section className="login-introduction">
        <div className="workspace-brand"><span className="workspace-logo"><Layers3 size={23} /></span><span>OCI Cost Manager<small>FINOPS WORKSPACE</small></span></div>
        <div><p className="overline">CLOUD COST INTELLIGENCE</p><h1>A clearer view<br />of your cloud.</h1><p>Understand every charge. Connect spend to workloads. Make informed decisions.</p></div>
        <span className="login-release">Interface {BUILD_INFO.uiVersion} · Build {BUILD_INFO.revision.slice(0, 8)}</span>
      </section>
      <section className="login-form-area"><Settings onAuthChange={(value, username) => {
          setAuthenticated(value);
          if (username) setProfileName(username);
        }} forceLogin /><p className="login-footnote">Use your existing workspace account. Access follows your assigned role and scope.</p></section>
    </div>;
  }
  return <div className="finops-app text-slate-900 dark:text-slate-100">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <div className="workspace-layout">
        <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} profileName={profileName} persona={persona} />
        <main className="workspace-main" id="main-content">
          <div className="fixed right-4 top-4 z-50 space-y-2">
            {toasts.map(t => <div key={t.id} className="max-w-sm rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800 shadow dark:border-rose-700 dark:bg-rose-950 dark:text-rose-200">
                <div className="font-medium">{t.code || 'API_ERROR'}</div>
                <div>{t.message || 'Request failed'}</div>
                {t.correlation_id ? <div className="mt-1 text-xs text-rose-700 dark:text-rose-400">Correlation: {t.correlation_id}</div> : null}
              </div>)}
          </div>
          <header className="workspace-header">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <button type="button" className="rounded-md border border-slate-300 bg-white p-2 text-slate-700 hover:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
                  <Menu size={18} />
                </button>
                <div>
                  <div className="workspace-breadcrumb"><span>Workspace</span><ChevronRight size={13} /><strong>{pageTitle}</strong></div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {availableRegions.length > 0 && <select aria-label="Active OCI region" value={activeRegion} onChange={e => {
                setActiveRegion(e.target.value);
                localStorage.setItem('ui_active_region', e.target.value);
              }} className="rounded-lg border border-sky-200 bg-sky-50 px-2 py-1.5 text-xs font-medium text-sky-700 dark:border-sky-700 dark:bg-sky-950 dark:text-sky-300">
                    <option value="all">All Regions</option>
                    {availableRegions.map(r => <option key={r} value={r}>{r}</option>)}
                  </select>}
                <select aria-label="Workspace view" value={persona} onChange={e => {
                setPersona(e.target.value);
                localStorage.setItem('ui_persona', e.target.value);
              }} className="hidden rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 sm:block">
                  <option>Executive</option>
                  <option>FinOps</option>
                  <option>Engineer</option>
                </select>
                <span className="workspace-role hidden sm:inline-flex">{role}</span>
                {demoMode ? <div className="hidden rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-300 sm:block">
                    Demo mode: read-only
                  </div> : null}
                {/* Dark / Light mode toggle */}
                <button type="button" onClick={() => setDarkMode(v => !v)} title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'} className="rounded-lg border border-slate-200 bg-white p-2 text-slate-600 transition hover:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700" aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}>
                  {darkMode ? <Sun size={15} /> : <Moon size={15} />}
                </button>
              </div>
            </div>
          </header>

          <section className="workspace-content">
            <GlobalStatusBar />
            <Routes>
              <Route path="/" element={<Overview activeRegion={activeRegion} />} />
              <Route path="/analytics" element={<Dashboard persona={persona} activeRegion={activeRegion} />} />
              <Route path="/resources" element={<Resources activeRegion={activeRegion} />} />
              <Route path="/costs" element={<Costs activeRegion={activeRegion} />} />
              <Route path="/budget" element={<Budget activeRegion={activeRegion} />} />
              <Route path="/exports" element={<ExportReports activeRegion={activeRegion} />} />
              <Route path="/governance" element={<Governance activeRegion={activeRegion} />} />
              <Route path="/recommendations" element={<Recommendations activeRegion={activeRegion} />} />
              <Route path="/actions" element={<Actions activeRegion={activeRegion} />} />
              <Route path="/logs" element={<Logs role={role} activeRegion={activeRegion} />} />
              <Route path="/settings" element={<Settings onAuthChange={(value, username) => {
              setAuthenticated(value);
              if (username) setProfileName(username);
            }} onRegionsChange={regions => setAvailableRegions(regions)} />} />
            </Routes>
          </section>
          <footer className="workspace-footer">
            <span>OCI Cost Manager <span className="release-badge">Interface {BUILD_INFO.uiVersion}</span></span>
            <span title={`Built ${BUILD_INFO.builtAt}`}>Build {BUILD_INFO.revision.slice(0, 8)} · API v{appVersion}</span>
          </footer>
        </main>
      </div>
    </div>;
}
function App() {
  return <Router>
      <AppLayout />
    </Router>;
}
export default App;
