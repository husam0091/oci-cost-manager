import { useState, useEffect } from 'react';
import {
  LogIn,
  LogOut,
  RefreshCw,
  AlertTriangle,
  ShieldCheck,
  ServerCog,
} from 'lucide-react';
import {
  adminLogin,
  adminLogout,
  adminGetSettings,
  adminUpdateSettings,
  adminRunScan,
  adminGetScanRuns,
  adminTestOciConnection,
  adminGetImportantCompartments,
  adminGetFeatureFlags,
  adminSetImportantCompartments,
  adminUpdateFeatureFlags,
  getDataCompartmentTree,
} from '../services/api';

function Settings({ onAuthChange, forceLogin = false }) {
  const [activeTab, setActiveTab] = useState('integration');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const [settings, setSettings] = useState(null);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [scanInterval, setScanInterval] = useState(8);
  const [saveMessage, setSaveMessage] = useState(null);

  const [ociAuthMode, setOciAuthMode] = useState('profile');
  const [ociConfigProfile, setOciConfigProfile] = useState('DEFAULT');
  const [ociConfigFile, setOciConfigFile] = useState('/root/.oci/config');
  const [ociUser, setOciUser] = useState('');
  const [ociFingerprint, setOciFingerprint] = useState('');
  const [ociTenancy, setOciTenancy] = useState('');
  const [ociRegion, setOciRegion] = useState('');
  const [ociKeyFile, setOciKeyFile] = useState('/root/.oci/oci_api_key.pem');
  const [ociKeyContent, setOciKeyContent] = useState('');
  const [ociPassPhrase, setOciPassPhrase] = useState('');

  const [scanRuns, setScanRuns] = useState([]);
  const [scanRunning, setScanRunning] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [testingConnection, setTestingConnection] = useState(false);
  const [ociTestStatus, setOciTestStatus] = useState(null);
  const [importantCompartments, setImportantCompartments] = useState([]);
  const [importantIncludeChildren, setImportantIncludeChildren] = useState(true);
  const [availableCompartments, setAvailableCompartments] = useState([]);
  const [importantSaveStatus, setImportantSaveStatus] = useState(null);
  const [notificationsEmailEnabled, setNotificationsEmailEnabled] = useState(false);
  const [notificationsSmtpHost, setNotificationsSmtpHost] = useState('');
  const [notificationsSmtpPort, setNotificationsSmtpPort] = useState(587);
  const [notificationsSmtpUsername, setNotificationsSmtpUsername] = useState('');
  const [notificationsSmtpPassword, setNotificationsSmtpPassword] = useState('');
  const [notificationsEmailFrom, setNotificationsEmailFrom] = useState('');
  const [notificationsEmailTo, setNotificationsEmailTo] = useState('');
  const [notificationsWebhookEnabled, setNotificationsWebhookEnabled] = useState(false);
  const [notificationsWebhookUrl, setNotificationsWebhookUrl] = useState('');
  const [notificationsWebhookDryRun, setNotificationsWebhookDryRun] = useState(true);
  const [role, setRole] = useState('admin');
  const [allowedTeams, setAllowedTeams] = useState('');
  const [allowedApps, setAllowedApps] = useState('');
  const [allowedEnvs, setAllowedEnvs] = useState('');
  const [allowedCompartments, setAllowedCompartments] = useState('');
  const [featureFlags, setFeatureFlags] = useState({
    enable_oci_executors: false,
    enable_destructive_actions: false,
    enable_budget_auto_eval: true,
    enable_demo_mode: false,
  });

  useEffect(() => {
    checkLoginStatus();
  }, []);

  const checkLoginStatus = async () => {
    try {
      const res = await adminGetSettings();
      if (res.data.success) {
        const data = res.data.data;
        setIsLoggedIn(true);
        setSettings(data);
        setNewUsername(data.username || '');
        setScanInterval(data.scan_interval_hours || 8);
        setOciAuthMode(data.oci_auth_mode || 'profile');
        setOciConfigProfile(data.oci_config_profile || 'DEFAULT');
        setOciConfigFile(data.oci_config_file || '/root/.oci/config');
        setOciUser(data.oci_user || '');
        setOciFingerprint(data.oci_fingerprint || '');
        setOciTenancy(data.oci_tenancy || '');
        setOciRegion(data.oci_region || '');
        setOciKeyFile(data.oci_key_file || '/root/.oci/oci_api_key.pem');
        setOciKeyContent(data.oci_key_content || '');
        setOciPassPhrase(data.oci_pass_phrase || '');
        setNotificationsEmailEnabled(Boolean(data.notifications_email_enabled));
        setNotificationsSmtpHost(data.notifications_smtp_host || '');
        setNotificationsSmtpPort(Number(data.notifications_smtp_port || 587));
        setNotificationsSmtpUsername(data.notifications_smtp_username || '');
        setNotificationsSmtpPassword(data.notifications_smtp_password || '');
        setNotificationsEmailFrom(data.notifications_email_from || '');
        setNotificationsEmailTo((data.notifications_email_to || []).join(','));
        setNotificationsWebhookEnabled(Boolean(data.notifications_webhook_enabled));
        setNotificationsWebhookUrl(data.notifications_webhook_url || '');
        setNotificationsWebhookDryRun(Boolean(data.notifications_webhook_dry_run));
        setRole(data.user_role || 'admin');
        setAllowedTeams((data.allowed_teams || []).join(','));
        setAllowedApps((data.allowed_apps || []).join(','));
        setAllowedEnvs((data.allowed_envs || []).join(','));
        setAllowedCompartments((data.allowed_compartment_ids || []).join(','));
        try {
          const ff = await adminGetFeatureFlags();
          setFeatureFlags(ff.data?.data || featureFlags);
        } catch {
          // ignore
        }
        if (onAuthChange) onAuthChange(true, data.username || 'admin');
        loadScanRuns();
        loadImportantCompartments();
      }
    } catch {
      setIsLoggedIn(false);
      if (onAuthChange) onAuthChange(false);
    }
  };

  const loadImportantCompartments = async () => {
    try {
      const [savedRes, treeRes] = await Promise.all([
        adminGetImportantCompartments(),
        getDataCompartmentTree(),
      ]);
      const data = savedRes.data?.data || {};
      setImportantCompartments(data.important_compartments || []);
      setImportantIncludeChildren(Boolean(data.include_children));

      const flatten = (node, acc = []) => {
        if (!node) return acc;
        acc.push({ id: node.id, name: node.name, parent_id: node.parent_id });
        (node.children || []).forEach((child) => flatten(child, acc));
        return acc;
      };
      setAvailableCompartments(flatten(treeRes.data?.data || null, []));
    } catch {
      setAvailableCompartments([]);
    }
  };

  const toggleImportantCompartment = (cid) => {
    setImportantCompartments((prev) => (
      prev.includes(cid) ? prev.filter((x) => x !== cid) : [...prev, cid]
    ));
  };

  const saveImportantCompartments = async () => {
    setImportantSaveStatus(null);
    try {
      await adminSetImportantCompartments({
        important_compartments: importantCompartments,
        include_children: importantIncludeChildren,
      });
      setImportantSaveStatus({ type: 'success', text: 'Important compartments saved.' });
    } catch (err) {
      setImportantSaveStatus({ type: 'error', text: err.response?.data?.detail || 'Failed to save important compartments' });
    }
  };

  const loadScanRuns = async () => {
    try {
      const res = await adminGetScanRuns();
      setScanRuns(res.data.data || []);
    } catch {
      setScanRuns([]);
    }
  };

  const buildIntegrationPayload = () => ({
    oci_auth_mode: ociAuthMode,
    oci_config_profile: ociConfigProfile,
    oci_config_file: ociConfigFile,
    oci_user: ociUser,
    oci_fingerprint: ociFingerprint,
    oci_tenancy: ociTenancy,
    oci_region: ociRegion,
    oci_key_file: ociKeyFile,
    oci_key_content: ociKeyContent,
    oci_pass_phrase: ociPassPhrase,
    notifications_email_enabled: notificationsEmailEnabled,
    notifications_smtp_host: notificationsSmtpHost,
    notifications_smtp_port: notificationsSmtpPort,
    notifications_smtp_username: notificationsSmtpUsername,
    notifications_smtp_password: notificationsSmtpPassword,
    notifications_email_from: notificationsEmailFrom,
    notifications_email_to: notificationsEmailTo.split(',').map((x) => x.trim()).filter(Boolean),
      notifications_webhook_enabled: notificationsWebhookEnabled,
      notifications_webhook_url: notificationsWebhookUrl,
      notifications_webhook_dry_run: notificationsWebhookDryRun,
      user_role: role,
      allowed_teams: allowedTeams.split(',').map((x) => x.trim()).filter(Boolean),
      allowed_apps: allowedApps.split(',').map((x) => x.trim()).filter(Boolean),
      allowed_envs: allowedEnvs.split(',').map((x) => x.trim()).filter(Boolean),
      allowed_compartment_ids: allowedCompartments.split(',').map((x) => x.trim()).filter(Boolean),
      enable_oci_executors: featureFlags.enable_oci_executors,
      enable_destructive_actions: featureFlags.enable_destructive_actions,
      enable_budget_auto_eval: featureFlags.enable_budget_auto_eval,
      enable_demo_mode: featureFlags.enable_demo_mode,
    });

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError(null);
    try {
      await adminLogin(username, password);
      setPassword('');
      if (onAuthChange) onAuthChange(true, username);
      checkLoginStatus();
    } catch (err) {
      setLoginError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = async () => {
    await adminLogout();
    setIsLoggedIn(false);
    if (onAuthChange) onAuthChange(false);
  };

  const handleSaveSettings = async () => {
    setSettingsLoading(true);
    setSaveMessage(null);
    try {
      const payload = buildIntegrationPayload();
      if (newUsername && newUsername !== settings?.username) payload.username = newUsername;
      if (newPassword) payload.password = newPassword;
      if (scanInterval !== settings?.scan_interval_hours) payload.scan_interval_hours = scanInterval;
      await adminUpdateSettings(payload);
      await adminUpdateFeatureFlags(featureFlags);
      setSaveMessage({ type: 'success', text: 'Settings saved.' });
      setNewPassword('');
      checkLoginStatus();
    } catch (err) {
      setSaveMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to save settings' });
    } finally {
      setSettingsLoading(false);
    }
  };

  const handleTestConnection = async () => {
    setTestingConnection(true);
    setOciTestStatus(null);
    try {
      const res = await adminTestOciConnection(buildIntegrationPayload());
      const data = res.data?.data || {};
      setOciTestStatus({ type: 'success', text: `Connected to ${data.tenancy_name || 'tenancy'} in ${data.region || 'region'}` });
    } catch (err) {
      setOciTestStatus({ type: 'error', text: err.response?.data?.detail || 'OCI connection test failed' });
    } finally {
      setTestingConnection(false);
    }
  };

  const handleRunScan = async () => {
    if (ociTestStatus?.type !== 'success') return;
    setScanRunning(true);
    setScanResult(null);
    try {
      const res = await adminRunScan();
      const status = res?.data?.data?.status;
      const runId = res?.data?.data?.run_id;
      if (status === 'already_running') {
        setScanResult({ type: 'success', text: runId ? `Scan already running (Run #${runId})` : 'Scan already running' });
      } else {
        setScanResult({ type: 'success', text: 'Scan started in background. Refresh history to track progress.' });
      }
      loadScanRuns();
    } catch (err) {
      setScanResult({ type: 'error', text: err.response?.data?.detail || 'Scan failed' });
    } finally {
      setScanRunning(false);
    }
  };

  if (!isLoggedIn) {
    return (
      <div className="mx-auto mt-8 max-w-md">
        <div className="rounded-3xl border border-white/50 bg-white/85 p-8 shadow-xl">
          <div className="mb-6 flex items-center gap-3">
            <div className="rounded-xl bg-cyan-100 p-3"><LogIn className="text-cyan-700" size={24} /></div>
            <div><h1 className="text-xl font-bold text-slate-900">Admin Login</h1></div>
          </div>
          <form onSubmit={handleLogin} className="space-y-4">
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} className="w-full rounded-lg border border-slate-300 px-4 py-2" placeholder="Username" required />
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full rounded-lg border border-slate-300 px-4 py-2" placeholder="Password" required />
            {loginError && <div className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{loginError}</div>}
            <button type="submit" disabled={loginLoading} className="w-full rounded-lg bg-cyan-600 px-4 py-2 font-medium text-white">
              {loginLoading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  const tabClass = (id) => `rounded-lg px-3 py-2 text-sm font-medium ${activeTab === id ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:bg-white/60'}`;

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-white/60 bg-white/85 p-6 shadow-xl">
        <div className="flex flex-col items-start justify-between gap-3 md:flex-row md:items-center">
          <div><h1 className="text-2xl font-bold tracking-tight text-slate-900">Settings</h1></div>
          {!forceLogin && (
            <button onClick={handleLogout} className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-slate-700">
              <LogOut size={16} /> Logout
            </button>
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-white/60 bg-white/90 p-2 shadow-lg">
        <div className="grid grid-cols-2 gap-2 rounded-xl bg-slate-100 p-1">
          <button className={tabClass('integration')} onClick={() => setActiveTab('integration')}>Integration</button>
          <button className={tabClass('operations')} onClick={() => setActiveTab('operations')}>Operations</button>
        </div>
      </div>

      {activeTab === 'integration' && (
        <div className="grid grid-cols-1 gap-6 2xl:grid-cols-3">
          <div className="rounded-2xl border border-white/60 bg-white/90 p-5 shadow-lg 2xl:col-span-1">
            <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900"><ShieldCheck size={18} className="text-cyan-700" />Admin Access</h3>
            <div className="space-y-3">
              <input type="text" value={newUsername} onChange={(e) => setNewUsername(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Username" />
              <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="New password (optional)" />
              <select value={scanInterval} onChange={(e) => setScanInterval(parseInt(e.target.value, 10))} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">
                <option value={1}>Every 1 hour</option><option value={2}>Every 2 hours</option><option value={4}>Every 4 hours</option>
                <option value={6}>Every 6 hours</option><option value={8}>Every 8 hours</option><option value={12}>Every 12 hours</option><option value={24}>Every 24 hours</option>
              </select>
              <select value={role} onChange={(e) => setRole(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">
                <option value="admin">admin</option>
                <option value="finops">finops</option>
                <option value="engineer">engineer</option>
                <option value="viewer">viewer</option>
              </select>
              <input type="text" value={allowedTeams} onChange={(e) => setAllowedTeams(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Allowed teams (comma-separated)" />
              <input type="text" value={allowedApps} onChange={(e) => setAllowedApps(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Allowed apps (comma-separated)" />
              <input type="text" value={allowedEnvs} onChange={(e) => setAllowedEnvs(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Allowed envs (comma-separated)" />
              <input type="text" value={allowedCompartments} onChange={(e) => setAllowedCompartments(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Allowed compartment IDs (comma-separated)" />
            </div>
          </div>

          <div className="rounded-2xl border border-white/60 bg-white/90 p-5 shadow-lg 2xl:col-span-2">
            <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900"><ServerCog size={18} className="text-cyan-700" />OCI SDK Integration</h3>
            <p className="mb-3 text-xs text-slate-500">Secret sources: direct values, environment overrides, or vault:// references (recommended for production).</p>
            <div className="mb-4 grid grid-cols-2 gap-2 rounded-xl bg-slate-100 p-1">
              <button onClick={() => setOciAuthMode('profile')} className={`rounded-lg px-3 py-2 text-sm ${ociAuthMode === 'profile' ? 'bg-white shadow-sm' : ''}`}>Profile Config</button>
              <button onClick={() => setOciAuthMode('direct')} className={`rounded-lg px-3 py-2 text-sm ${ociAuthMode === 'direct' ? 'bg-white shadow-sm' : ''}`}>Direct Credentials</button>
            </div>
            {ociAuthMode === 'profile' ? (
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <input type="text" value={ociConfigProfile} onChange={(e) => setOciConfigProfile(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Profile Name" />
                <input type="text" value={ociConfigFile} onChange={(e) => setOciConfigFile(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="/root/.oci/config" />
              </div>
            ) : (
              <div className="space-y-3">
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <input type="text" value={ociUser} onChange={(e) => setOciUser(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="User OCID" />
                  <input type="text" value={ociFingerprint} onChange={(e) => setOciFingerprint(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Fingerprint" />
                  <input type="text" value={ociTenancy} onChange={(e) => setOciTenancy(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Tenancy OCID" />
                  <input type="text" value={ociRegion} onChange={(e) => setOciRegion(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Region" />
                  <input type="text" value={ociKeyFile} onChange={(e) => setOciKeyFile(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Key file path" />
                  <input type="password" value={ociPassPhrase} onChange={(e) => setOciPassPhrase(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Passphrase (optional)" />
                </div>
                <textarea rows={7} value={ociKeyContent} onChange={(e) => setOciKeyContent(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs" placeholder="Private key content (optional)" />
              </div>
            )}
            <div className="mt-4 flex flex-wrap gap-2">
              <button onClick={handleTestConnection} disabled={testingConnection} className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white">{testingConnection ? 'Testing...' : 'Test Connection'}</button>
              <button onClick={handleSaveSettings} disabled={settingsLoading} className="rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white">{settingsLoading ? 'Saving...' : 'Save Settings'}</button>
            </div>
            <div className="mt-6 rounded-xl border border-slate-200 p-4">
              <h4 className="mb-3 text-sm font-semibold text-slate-800">Notifications (opt-in)</h4>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                  <input type="checkbox" checked={notificationsEmailEnabled} onChange={(e) => setNotificationsEmailEnabled(e.target.checked)} />
                  Enable Email (SMTP)
                </label>
                <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                  <input type="checkbox" checked={notificationsWebhookEnabled} onChange={(e) => setNotificationsWebhookEnabled(e.target.checked)} />
                  Enable Webhook
                </label>
                <input type="text" value={notificationsSmtpHost} onChange={(e) => setNotificationsSmtpHost(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="SMTP host" />
                <input type="number" value={notificationsSmtpPort} onChange={(e) => setNotificationsSmtpPort(parseInt(e.target.value || '587', 10))} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="SMTP port" />
                <input type="text" value={notificationsSmtpUsername} onChange={(e) => setNotificationsSmtpUsername(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="SMTP username" />
                <input type="password" value={notificationsSmtpPassword} onChange={(e) => setNotificationsSmtpPassword(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="SMTP password" />
                <input type="text" value={notificationsEmailFrom} onChange={(e) => setNotificationsEmailFrom(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Email from" />
                <input type="text" value={notificationsEmailTo} onChange={(e) => setNotificationsEmailTo(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Email to (comma-separated)" />
                <input type="text" value={notificationsWebhookUrl} onChange={(e) => setNotificationsWebhookUrl(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm md:col-span-2" placeholder="Webhook URL (Slack/Teams compatible)" />
                <label className="inline-flex items-center gap-2 text-sm text-slate-700 md:col-span-2">
                  <input type="checkbox" checked={notificationsWebhookDryRun} onChange={(e) => setNotificationsWebhookDryRun(e.target.checked)} />
                  Webhook dry-run (no outbound POST)
                </label>
              </div>
            </div>
            <div className="mt-6 rounded-xl border border-slate-200 p-4">
              <h4 className="mb-3 text-sm font-semibold text-slate-800">Feature Flags</h4>
              <div className="grid grid-cols-1 gap-2">
                <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={featureFlags.enable_oci_executors}
                    onChange={(e) => setFeatureFlags((f) => ({ ...f, enable_oci_executors: e.target.checked }))}
                  />
                  enable_oci_executors
                </label>
                <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={featureFlags.enable_destructive_actions}
                    onChange={(e) => setFeatureFlags((f) => ({ ...f, enable_destructive_actions: e.target.checked }))}
                  />
                  enable_destructive_actions
                </label>
                <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={featureFlags.enable_budget_auto_eval}
                    onChange={(e) => setFeatureFlags((f) => ({ ...f, enable_budget_auto_eval: e.target.checked }))}
                  />
                  enable_budget_auto_eval
                </label>
                <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={featureFlags.enable_demo_mode}
                    onChange={(e) => setFeatureFlags((f) => ({ ...f, enable_demo_mode: e.target.checked }))}
                  />
                  enable_demo_mode
                </label>
              </div>
            </div>
            {ociTestStatus && <div className={`mt-3 rounded-lg border px-3 py-2 text-sm ${ociTestStatus.type === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-rose-200 bg-rose-50 text-rose-700'}`}>{ociTestStatus.text}</div>}
            {saveMessage && <div className={`mt-2 rounded-lg border px-3 py-2 text-sm ${saveMessage.type === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-rose-200 bg-rose-50 text-rose-700'}`}>{saveMessage.text}</div>}
          </div>
        </div>
      )}

      {activeTab === 'operations' && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-white/60 bg-white/90 p-6 shadow-lg">
            <h3 className="mb-4 text-lg font-semibold text-slate-900">Important Compartments</h3>
            <p className="mb-3 text-sm text-slate-500">Selected compartments appear on Dashboard as Core Business Spotlight.</p>
            <label className="mb-3 flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={importantIncludeChildren}
                onChange={(e) => setImportantIncludeChildren(e.target.checked)}
              />
              Include child compartments
            </label>
            <div className="max-h-56 space-y-1 overflow-auto rounded-lg border border-slate-200 p-2">
              {availableCompartments.map((c) => (
                <label key={c.id} className="flex items-center gap-2 rounded-md px-2 py-1 text-sm hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={importantCompartments.includes(c.id)}
                    onChange={() => toggleImportantCompartment(c.id)}
                  />
                  <span className="truncate">{c.name}</span>
                </label>
              ))}
            </div>
            <div className="mt-3">
              <button onClick={saveImportantCompartments} className="rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white">
                Save Important Compartments
              </button>
            </div>
            {importantSaveStatus && (
              <div className={`mt-3 rounded-lg border px-3 py-2 text-sm ${importantSaveStatus.type === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-rose-200 bg-rose-50 text-rose-700'}`}>
                {importantSaveStatus.text}
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-white/60 bg-white/90 p-6 shadow-lg">
            <div className="flex flex-wrap gap-2">
              <button onClick={handleRunScan} disabled={scanRunning || ociTestStatus?.type !== 'success'} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white">
                {scanRunning ? 'Scanning...' : 'Run Scan'}
              </button>
              <button onClick={loadScanRuns} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm text-slate-700">
                <RefreshCw size={14} /> Refresh History
              </button>
            </div>
            {scanResult && <div className={`mt-3 rounded-lg border px-3 py-2 text-sm ${scanResult.type === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-rose-200 bg-rose-50 text-rose-700'}`}>{scanResult.text}</div>}
          </div>

          <div className="rounded-2xl border border-white/60 bg-white/90 p-6 shadow-lg">
            <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900"><AlertTriangle size={18} className="text-cyan-700" />Scan History</h3>
            {scanRuns.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="border-b border-slate-200"><th className="px-3 py-2 text-left">Run ID</th><th className="px-3 py-2 text-left">Status</th><th className="px-3 py-2 text-left">Started</th><th className="px-3 py-2 text-left">Finished</th><th className="px-3 py-2 text-left">Error</th></tr></thead>
                  <tbody>
                    {scanRuns.map((run) => (
                      <tr key={run.id} className="border-b border-slate-100">
                        <td className="px-3 py-2">#{run.id}</td>
                        <td className="px-3 py-2">{run.status}</td>
                        <td className="px-3 py-2">{run.started_at ? new Date(run.started_at).toLocaleString() : '-'}</td>
                        <td className="px-3 py-2">{run.finished_at ? new Date(run.finished_at).toLocaleString() : '-'}</td>
                        <td className="max-w-xs truncate px-3 py-2 text-xs text-rose-600">{run.error_message || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <p className="text-slate-500">No scan runs yet.</p>}
          </div>
        </div>
      )}
    </div>
  );
}

export default Settings;
