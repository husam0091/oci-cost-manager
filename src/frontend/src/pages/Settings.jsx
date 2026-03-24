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
  adminGetImportantCompartments,
  adminGetFeatureFlags,
  adminSetImportantCompartments,
  adminUpdateFeatureFlags,
  adminListUsers,
  adminCreateUser,
  adminUpdateUser,
  getDataResources,
  getDataCompartmentTree,
  saveOciSettings,
  uploadOciKey,
  testOciSettings,
  getMe,
  adminGetPortalSslSettings,
  adminUploadPortalSsl,
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

  const [ociUser, setOciUser] = useState('');
  const [ociFingerprint, setOciFingerprint] = useState('');
  const [ociTenancy, setOciTenancy] = useState('');
  const [ociRegion, setOciRegion] = useState('');
  const [ociLastTestStatus, setOciLastTestStatus] = useState(null);
  const [ociLastTestedAt, setOciLastTestedAt] = useState(null);
  const [selectedKeyFile, setSelectedKeyFile] = useState(null);
  const [uploadingKey, setUploadingKey] = useState(false);
  const [showAdvancedPem, setShowAdvancedPem] = useState(false);
  const [portalSslInfo, setPortalSslInfo] = useState(null);
  const [portalSslStatus, setPortalSslStatus] = useState(null);
  const [portalCertFile, setPortalCertFile] = useState(null);
  const [portalKeyFile, setPortalKeyFile] = useState(null);
  const [portalIntermediateFile, setPortalIntermediateFile] = useState(null);
  const [portalRootFile, setPortalRootFile] = useState(null);
  const [portalPfxFile, setPortalPfxFile] = useState(null);
  const [portalPfxPassword, setPortalPfxPassword] = useState('');
  const [portalUploading, setPortalUploading] = useState(false);

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
  const [users, setUsers] = useState([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [userStatus, setUserStatus] = useState(null);
  const [permissionOptions, setPermissionOptions] = useState({ teams: [], apps: [], envs: [], compartments: [] });
  const [newUser, setNewUser] = useState({
    username: '',
    password: '',
    role: 'viewer',
    allowed_teams: [],
    allowed_apps: [],
    allowed_envs: [],
    allowed_compartment_ids: [],
    is_active: true,
  });

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
      const meRes = await getMe();
      const me = meRes.data?.data || {};
      setIsLoggedIn(Boolean(meRes.data?.success));
      if (onAuthChange) onAuthChange(Boolean(meRes.data?.success), me.username || 'user');

      // Admin-only settings (best effort)
      try {
        const res = await adminGetSettings();
        if (res.data.success) {
          const data = res.data.data;
          setSettings(data);
          setNewUsername(data.username || '');
          setScanInterval(data.scan_interval_hours || 8);
          setOciUser(data.oci_user || '');
          setOciFingerprint(data.oci_fingerprint || '');
          setOciTenancy(data.oci_tenancy || '');
          setOciRegion(data.oci_region || '');
          setOciLastTestStatus(data.oci_last_test_status || null);
          setOciLastTestedAt(data.oci_last_tested_at || null);
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
          try {
            const ff = await adminGetFeatureFlags();
            setFeatureFlags(ff.data?.data || featureFlags);
          } catch {
            // ignore
          }
          try {
            const ssl = await adminGetPortalSslSettings();
            setPortalSslInfo(ssl.data?.data || null);
          } catch {
            setPortalSslInfo(null);
          }
          loadScanRuns();
          loadImportantCompartments();
          loadUsers();
          loadPermissionOptions();
        }
      } catch {
        // Non-admin user: authenticated but admin settings not available
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

  const loadUsers = async () => {
    setUsersLoading(true);
    try {
      const res = await adminListUsers();
      setUsers(res.data?.data || []);
    } catch {
      setUsers([]);
    } finally {
      setUsersLoading(false);
    }
  };

  const loadPermissionOptions = async () => {
    try {
      const [resRows, treeRes] = await Promise.all([
        getDataResources({ limit: 1000 }),
        getDataCompartmentTree(),
      ]);
      const rows = resRows.data?.data || [];
      const teams = Array.from(new Set(rows.map((r) => r.team).filter(Boolean).filter((x) => x !== 'Unallocated'))).sort();
      const apps = Array.from(new Set(rows.map((r) => r.app).filter(Boolean).filter((x) => x !== 'Unallocated'))).sort();
      const envs = Array.from(new Set(rows.map((r) => r.env).filter(Boolean).filter((x) => x !== 'Unallocated'))).sort();
      const flatten = (node, acc = []) => {
        if (!node) return acc;
        acc.push({ id: node.id, name: node.name });
        (node.children || []).forEach((child) => flatten(child, acc));
        return acc;
      };
      const compartments = flatten(treeRes.data?.data || null, []);
      setPermissionOptions({ teams, apps, envs, compartments });
    } catch {
      setPermissionOptions({ teams: [], apps: [], envs: [], compartments: [] });
    }
  };

  const toggleUserScope = (field, value) => {
    setNewUser((u) => {
      const arr = new Set(u[field] || []);
      if (arr.has(value)) arr.delete(value); else arr.add(value);
      return { ...u, [field]: Array.from(arr) };
    });
  };

  const createUser = async () => {
    setUserStatus(null);
    if (!newUser.username || !newUser.password) {
      setUserStatus({ type: 'error', text: 'Username and password are required' });
      return;
    }
    try {
      await adminCreateUser(newUser);
      setUserStatus({ type: 'success', text: 'User created successfully' });
      setNewUser({ username: '', password: '', role: 'viewer', allowed_teams: [], allowed_apps: [], allowed_envs: [], allowed_compartment_ids: [], is_active: true });
      await loadUsers();
    } catch (err) {
      setUserStatus({ type: 'error', text: err.response?.data?.detail || 'Failed to create user' });
    }
  };

  const updateUser = async (id, patch) => {
    setUserStatus(null);
    try {
      await adminUpdateUser(id, patch);
      setUserStatus({ type: 'success', text: 'User updated' });
      await loadUsers();
    } catch (err) {
      setUserStatus({ type: 'error', text: err.response?.data?.detail || 'Failed to update user' });
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
    try {
      await adminLogout();
    } catch (err) {
      // If session already expired, still force local logout state.
      if (err?.response?.status && err.response.status !== 401) {
        throw err;
      }
    } finally {
      setIsLoggedIn(false);
      if (onAuthChange) onAuthChange(false);
    }
  };

  const handleSaveSettings = async () => {
    setSettingsLoading(true);
    setSaveMessage(null);
    try {
      const payload = buildIntegrationPayload();
      await saveOciSettings({
        user_ocid: ociUser,
        tenancy_ocid: ociTenancy,
        fingerprint: ociFingerprint,
        region: ociRegion,
      });
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
      const res = await testOciSettings();
      const data = res.data?.data || {};
      setOciTestStatus({ type: 'success', text: `Connected to ${data.tenancy_name || 'tenancy'} in ${data.region || 'region'}` });
      setOciLastTestStatus(data.status || 'healthy');
      setOciLastTestedAt(new Date().toISOString());
    } catch (err) {
      const d = err?.response?.data?.detail || err?.response?.data || {};
      const msg = d?.error?.reason || d?.reason || d?.message || (typeof d === 'string' ? d : 'OCI connection test failed');
      setOciTestStatus({ type: 'error', text: msg });
    } finally {
      setTestingConnection(false);
    }
  };

  const handleUploadKey = async () => {
    if (!selectedKeyFile) return;
    setUploadingKey(true);
    try {
      await uploadOciKey(selectedKeyFile);
      setSaveMessage({ type: 'success', text: 'OCI private key uploaded.' });
    } catch (err) {
      setSaveMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to upload key' });
    } finally {
      setUploadingKey(false);
    }
  };

  const handleUploadPortalSsl = async () => {
    setPortalSslStatus(null);
    setPortalUploading(true);
    try {
      const form = new FormData();
      if (portalPfxFile) {
        form.append('pfx_file', portalPfxFile);
        if (portalPfxPassword) form.append('pfx_password', portalPfxPassword);
      } else {
        if (!portalCertFile || !portalKeyFile) {
          setPortalSslStatus({ type: 'error', text: 'Provide cert + key files, or upload a .pfx file.' });
          setPortalUploading(false);
          return;
        }
        form.append('cert_file', portalCertFile);
        form.append('key_file', portalKeyFile);
        if (portalIntermediateFile) form.append('intermediate_file', portalIntermediateFile);
        if (portalRootFile) form.append('root_file', portalRootFile);
      }
      const res = await adminUploadPortalSsl(form);
      setPortalSslInfo(res.data?.data || null);
      setPortalSslStatus({ type: 'success', text: 'Certificate uploaded. Reload nginx to apply on port 443.' });
    } catch (err) {
      setPortalSslStatus({ type: 'error', text: err.response?.data?.detail || 'Failed to upload SSL certificate' });
    } finally {
      setPortalUploading(false);
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
            <input id="login-username" name="username" type="text" value={username} onChange={(e) => setUsername(e.target.value)} className="w-full rounded-lg border border-slate-300 px-4 py-2" placeholder="Username" required />
            <input id="login-password" name="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full rounded-lg border border-slate-300 px-4 py-2" placeholder="Password" required />
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
        <div className="grid grid-cols-3 gap-2 rounded-xl bg-slate-100 p-1">
          <button className={tabClass('integration')} onClick={() => setActiveTab('integration')}>Integration</button>
          <button className={tabClass('operations')} onClick={() => setActiveTab('operations')}>Operations</button>
          <button className={tabClass('users')} onClick={() => setActiveTab('users')}>Users</button>
        </div>
      </div>

      {activeTab === 'integration' && (
        <div className="grid grid-cols-1 gap-6 2xl:grid-cols-3">
          <div className="rounded-2xl border border-white/60 bg-white/90 p-5 shadow-lg 2xl:col-span-1">
            <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900"><ShieldCheck size={18} className="text-cyan-700" />Admin Access</h3>
            <div className="space-y-3">
              <input name="settings-username" type="text" value={newUsername} onChange={(e) => setNewUsername(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Username" />
              <input name="settings-new-password" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="New password (optional)" />
              <select value={scanInterval} onChange={(e) => setScanInterval(parseInt(e.target.value, 10))} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">
                <option value={1}>Every 1 hour</option><option value={2}>Every 2 hours</option><option value={4}>Every 4 hours</option>
                <option value={6}>Every 6 hours</option><option value={8}>Every 8 hours</option><option value={12}>Every 12 hours</option><option value={24}>Every 24 hours</option>
              </select>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
                User role and scope permissions are managed in the <span className="font-semibold">Users</span> tab with checkbox-based controls.
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-white/60 bg-white/90 p-5 shadow-lg 2xl:col-span-2">
            <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900"><ServerCog size={18} className="text-cyan-700" />OCI SDK Integration</h3>
            <p className="mb-3 text-xs text-slate-500">Private keys are never displayed or returned after upload.</p>
            <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-2">
              <input name="oci-user-ocid" type="text" value={ociUser} onChange={(e) => setOciUser(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="User OCID" />
              <input name="oci-fingerprint" type="text" value={ociFingerprint} onChange={(e) => setOciFingerprint(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Fingerprint" />
              <input name="oci-tenancy-ocid" type="text" value={ociTenancy} onChange={(e) => setOciTenancy(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Tenancy OCID" />
              <input name="oci-region" type="text" value={ociRegion} onChange={(e) => setOciRegion(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Region" />
            </div>
            <div className="mb-4 rounded-xl border border-slate-200 p-4">
              <h4 className="mb-2 text-sm font-semibold text-slate-800">Private Key Upload</h4>
              <input type="file" accept=".pem" onChange={(e) => setSelectedKeyFile(e.target.files?.[0] || null)} className="mb-2 block w-full text-sm text-slate-700" />
              <div className="flex flex-wrap gap-2">
                <button onClick={handleUploadKey} disabled={!selectedKeyFile || uploadingKey} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white">
                  {uploadingKey ? 'Uploading...' : 'Upload / Replace OCI Key'}
                </button>
                <button type="button" onClick={() => setShowAdvancedPem((v) => !v)} className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm text-slate-700">
                  {showAdvancedPem ? 'Hide Advanced' : 'Show Advanced'}
                </button>
              </div>
              {showAdvancedPem ? <p className="mt-2 text-xs text-slate-500">Paste PEM is disabled by default in production. Use file upload.</p> : null}
            </div>
            <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
              <div>Fingerprint: <span className="font-medium text-slate-900">{ociFingerprint || '-'}</span></div>
              <div>Region: <span className="font-medium text-slate-900">{ociRegion || '-'}</span></div>
              <div>Last Test Status: <span className="font-medium text-slate-900">{ociLastTestStatus || '-'}</span></div>
              <div>Last Tested: <span className="font-medium text-slate-900">{ociLastTestedAt ? new Date(ociLastTestedAt).toLocaleString() : '-'}</span></div>
            </div>
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
                <input name="smtp-host" type="text" value={notificationsSmtpHost} onChange={(e) => setNotificationsSmtpHost(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="SMTP host" />
                <input name="smtp-port" type="number" value={notificationsSmtpPort} onChange={(e) => setNotificationsSmtpPort(parseInt(e.target.value || '587', 10))} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="SMTP port" />
                <input name="smtp-username" type="text" value={notificationsSmtpUsername} onChange={(e) => setNotificationsSmtpUsername(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="SMTP username" />
                <input name="smtp-password" type="password" value={notificationsSmtpPassword} onChange={(e) => setNotificationsSmtpPassword(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="SMTP password" />
                <input name="email-from" type="text" value={notificationsEmailFrom} onChange={(e) => setNotificationsEmailFrom(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Email from" />
                <input name="email-to" type="text" value={notificationsEmailTo} onChange={(e) => setNotificationsEmailTo(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Email to (comma-separated)" />
                <input type="text" value={notificationsWebhookUrl} onChange={(e) => setNotificationsWebhookUrl(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm md:col-span-2" placeholder="Webhook URL (Slack/Teams compatible)" />
                <label className="inline-flex items-center gap-2 text-sm text-slate-700 md:col-span-2">
                  <input type="checkbox" checked={notificationsWebhookDryRun} onChange={(e) => setNotificationsWebhookDryRun(e.target.checked)} />
                  Webhook dry-run (no outbound POST)
                </label>
              </div>
            </div>

            <div className="mt-6 rounded-xl border border-slate-200 p-4">
              <h4 className="mb-3 text-sm font-semibold text-slate-800">Portal SSL (HTTPS / 443)</h4>
              <p className="mb-3 text-xs text-slate-500">Upload either a PKCS#12 file (.pfx/.p12) or PEM files (.crt/.pem + .key). Optional intermediate/root certs will be appended into full chain.</p>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <input type="file" accept=".pfx,.p12" onChange={(e) => setPortalPfxFile(e.target.files?.[0] || null)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                <input type="password" value={portalPfxPassword} onChange={(e) => setPortalPfxPassword(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="PFX password (optional)" />
                <input type="file" accept=".crt,.cer,.pem" onChange={(e) => setPortalCertFile(e.target.files?.[0] || null)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                <input type="file" accept=".key,.pem" onChange={(e) => setPortalKeyFile(e.target.files?.[0] || null)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                <input type="file" accept=".crt,.cer,.pem" onChange={(e) => setPortalIntermediateFile(e.target.files?.[0] || null)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                <input type="file" accept=".crt,.cer,.pem" onChange={(e) => setPortalRootFile(e.target.files?.[0] || null)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              </div>
              <div className="mt-3">
                <button onClick={handleUploadPortalSsl} disabled={portalUploading} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white">{portalUploading ? 'Uploading...' : 'Upload SSL Certificate'}</button>
              </div>
              {portalSslInfo ? (
                <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
                  <div><span className="font-semibold">Enabled:</span> {String(Boolean(portalSslInfo.enabled))}</div>
                  <div><span className="font-semibold">Mode:</span> {portalSslInfo.mode || '-'}</div>
                  <div><span className="font-semibold">Subject:</span> {portalSslInfo.subject || '-'}</div>
                  <div><span className="font-semibold">Issuer:</span> {portalSslInfo.issuer || '-'}</div>
                  <div><span className="font-semibold">Expires:</span> {portalSslInfo.expires_at ? new Date(portalSslInfo.expires_at).toLocaleString() : '-'}</div>
                  <div><span className="font-semibold">Reload:</span> {portalSslInfo.reload_hint || 'sudo nginx -t && sudo systemctl reload nginx'}</div>
                </div>
              ) : null}
              {portalSslStatus ? <div className={`mt-3 rounded-lg border px-3 py-2 text-sm ${portalSslStatus.type === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-rose-200 bg-rose-50 text-rose-700'}`}>{portalSslStatus.text}</div> : null}
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
            <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900">
              <ShieldCheck size={18} className="text-emerald-600" /> Cost Data Accuracy
            </h3>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-4 text-xs text-emerald-800 space-y-1">
                <p className="font-semibold text-sm">Data Source</p>
                <p>Costs are fetched live from the <strong>OCI Usage API</strong> (<code className="bg-emerald-100 px-1 rounded">RequestSummarizedUsages</code>) using <code className="bg-emerald-100 px-1 rounded">query_type=COST</code>. The <code className="bg-emerald-100 px-1 rounded">computed_amount</code> field is used — this is the same source as OCI Cost Analysis. No estimation or rounding is applied.</p>
              </div>
              <div className="rounded-xl border border-amber-100 bg-amber-50 p-4 text-xs text-amber-800 space-y-1">
                <p className="font-semibold text-sm">Billing Lag</p>
                <p>OCI billing data has a <strong>24–48 hour processing delay</strong>. The app shows costs as returned by OCI — today&apos;s actual charges are not yet available in the Usage API. Run a fresh scan to get the most recent data available from OCI.</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-700 space-y-1">
                <p className="font-semibold text-sm">Required IAM Policies</p>
                <p>The OCI key must have access to the entire tenancy to return complete cost data. Required policies:</p>
                <ul className="mt-1 list-disc list-inside space-y-0.5">
                  <li><code className="bg-slate-100 px-1 rounded">TENANCY_INSPECT</code></li>
                  <li><code className="bg-slate-100 px-1 rounded">USAGE_INSPECTOR</code></li>
                  <li>Or: <code className="bg-slate-100 px-1 rounded">manage usage-reports in tenancy</code></li>
                </ul>
                <p className="mt-1">If the key only has compartment-level access, costs will be partial and lower than OCI Cost Analysis.</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-700 space-y-1">
                <p className="font-semibold text-sm">How to Cross-Check</p>
                <p>In the OCI console:</p>
                <ol className="mt-1 list-decimal list-inside space-y-0.5">
                  <li>Go to <strong>Billing &amp; Cost Management</strong></li>
                  <li>Click <strong>Cost Analysis</strong></li>
                  <li>Set scope to <strong>All Compartments</strong></li>
                  <li>Set period to <strong>This Month</strong> or the same date range shown on the Dashboard</li>
                  <li>Compare the total — it should match within the billing lag window</li>
                </ol>
              </div>
            </div>
          </div>

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


      {activeTab === 'users' && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-white/60 bg-white/90 p-6 shadow-lg">
            <h3 className="mb-4 text-lg font-semibold text-slate-900">Create User</h3>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <input name="new-user-username" type="text" value={newUser.username} onChange={(e) => setNewUser((u) => ({ ...u, username: e.target.value }))} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Username" />
              <input name="new-user-password" type="password" value={newUser.password} onChange={(e) => setNewUser((u) => ({ ...u, password: e.target.value }))} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Password" />
              <select value={newUser.role} onChange={(e) => setNewUser((u) => ({ ...u, role: e.target.value }))} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
                <option value="admin">admin</option>
                <option value="finops">finops</option>
                <option value="engineer">engineer</option>
                <option value="viewer">viewer</option>
              </select>
            </div>
            <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="mb-2 text-sm font-medium text-slate-800">Allowed Teams</p>
                <div className="max-h-32 space-y-1 overflow-auto">
                  {permissionOptions.teams.map((x) => (
                    <label key={x} className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={newUser.allowed_teams.includes(x)} onChange={() => toggleUserScope('allowed_teams', x)} />{x}</label>
                  ))}
                </div>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="mb-2 text-sm font-medium text-slate-800">Allowed Apps</p>
                <div className="max-h-32 space-y-1 overflow-auto">
                  {permissionOptions.apps.map((x) => (
                    <label key={x} className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={newUser.allowed_apps.includes(x)} onChange={() => toggleUserScope('allowed_apps', x)} />{x}</label>
                  ))}
                </div>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="mb-2 text-sm font-medium text-slate-800">Allowed Environments</p>
                <div className="max-h-32 space-y-1 overflow-auto">
                  {permissionOptions.envs.map((x) => (
                    <label key={x} className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={newUser.allowed_envs.includes(x)} onChange={() => toggleUserScope('allowed_envs', x)} />{x}</label>
                  ))}
                </div>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="mb-2 text-sm font-medium text-slate-800">Allowed Compartments</p>
                <div className="max-h-32 space-y-1 overflow-auto">
                  {permissionOptions.compartments.map((c) => (
                    <label key={c.id} className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={newUser.allowed_compartment_ids.includes(c.id)} onChange={() => toggleUserScope('allowed_compartment_ids', c.id)} />{c.name}</label>
                  ))}
                </div>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-3">
              <label className="inline-flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={newUser.is_active} onChange={(e) => setNewUser((u) => ({ ...u, is_active: e.target.checked }))} />Active</label>
              <button onClick={createUser} className="rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white">Create User</button>
            </div>
          </div>

          <div className="rounded-2xl border border-white/60 bg-white/90 p-6 shadow-lg">
            <h3 className="mb-4 text-lg font-semibold text-slate-900">Users</h3>
            {usersLoading ? <p className="text-sm text-slate-500">Loading users...</p> : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="border-b border-slate-200"><th className="px-3 py-2 text-left">Username</th><th className="px-3 py-2 text-left">Role</th><th className="px-3 py-2 text-left">Active</th><th className="px-3 py-2 text-left">Scopes</th></tr></thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.id} className="border-b border-slate-100">
                        <td className="px-3 py-2 font-medium">{u.username}</td>
                        <td className="px-3 py-2">
                          <select value={u.role} onChange={(e) => updateUser(u.id, { role: e.target.value })} className="rounded border border-slate-300 px-2 py-1 text-xs">
                            <option value="admin">admin</option><option value="finops">finops</option><option value="engineer">engineer</option><option value="viewer">viewer</option>
                          </select>
                        </td>
                        <td className="px-3 py-2"><input type="checkbox" checked={Boolean(u.is_active)} onChange={(e) => updateUser(u.id, { is_active: e.target.checked })} /></td>
                        <td className="px-3 py-2 text-xs text-slate-600">teams:{(u.allowed_teams || []).length} apps:{(u.allowed_apps || []).length} envs:{(u.allowed_envs || []).length} comps:{(u.allowed_compartment_ids || []).length}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {userStatus ? <div className={`mt-3 rounded-lg border px-3 py-2 text-sm ${userStatus.type === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-rose-200 bg-rose-50 text-rose-700'}`}>{userStatus.text}</div> : null}
          </div>
        </div>
      )}

    </div>
  );
}

export default Settings;
