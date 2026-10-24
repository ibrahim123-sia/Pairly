import { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { getProfileApi, updateProfileApi } from '../../api/storeApi';
import { changePasswordApi } from '../../api/authApi';
import toast from 'react-hot-toast';
import { getAIStatus, setStoreAI } from '../../api/aiApi';

export const Settings = () => {
  const { refreshMe } = useAuth();
  const [profile, setProfile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [pwd, setPwd] = useState({ current_password: '', new_password: '', confirm: '' });
  const [changingPwd, setChangingPwd] = useState(false);
  const [ai, setAi] = useState(null);
  const [savingAi, setSavingAi] = useState(false);

  useEffect(() => {
    getProfileApi().then((r) => setProfile(r.data));
    getAIStatus().then(setAi).catch(() => {});
  }, []);

  const update = (k) => (e) => setProfile({ ...profile, [k]: e.target.value });

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await updateProfileApi({
        name: profile.name,
        description: profile.description,
        contact_email: profile.contact_email,
        theme_mode: profile.theme_mode,
        brand_primary_color: profile.brand_primary_color,
      });
      setProfile(res.data);
      await refreshMe();
      toast.success('Profile saved');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const toggleAi = async () => {
    setSavingAi(true);
    try {
      const next = await setStoreAI(!ai.store_enabled);
      setAi(next);
      toast.success(next.store_enabled ? 'AI features turned on' : 'AI features turned off');
    } catch {
      toast.error('Could not update AI setting');
    } finally {
      setSavingAi(false);
    }
  };

  const changePwd = async (e) => {
    e.preventDefault();
    if (pwd.new_password.length < 8) return toast.error('Password must be 8+ characters');
    if (pwd.new_password !== pwd.confirm) return toast.error('Passwords do not match');
    setChangingPwd(true);
    try {
      await changePasswordApi(pwd.current_password, pwd.new_password);
      toast.success('Password updated');
      setPwd({ current_password: '', new_password: '', confirm: '' });
    } catch (err) {
      toast.error(err.response?.data?.error || 'Password change failed');
    } finally {
      setChangingPwd(false);
    }
  };

  if (!profile) return <p className="text-gray-500">Loading...</p>;

  return (
    <div className="space-y-8 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Store Settings</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">Manage your store profile, theme, and password.</p>
      </div>

      <form onSubmit={save} className="space-y-4 bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700">
        <h2 className="font-semibold text-gray-900 dark:text-white">Profile</h2>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Store name</label>
          <input value={profile.name || ''} onChange={update('name')} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
          <textarea value={profile.description || ''} onChange={update('description')} rows={2} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Contact email</label>
          <input type="email" value={profile.contact_email || ''} onChange={update('contact_email')} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Theme</label>
            <select value={profile.theme_mode || 'light'} onChange={update('theme_mode')} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Brand color</label>
            <input type="color" value={profile.brand_primary_color || '#2563eb'} onChange={update('brand_primary_color')} className="w-full h-10 border border-gray-300 dark:border-gray-600 rounded-lg" />
          </div>
        </div>
        <div className="flex justify-end">
          <button type="submit" disabled={saving} className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg disabled:opacity-60">
            {saving ? 'Saving...' : 'Save profile'}
          </button>
        </div>
      </form>

      {ai && (
        <div className="space-y-3 bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="font-semibold text-gray-900 dark:text-white">AI features</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                AI Insights on the dashboard and the Ask Pairly assistant. Only aggregated results (rules, bundles,
                segment totals) are sent to the AI provider, never customer rows, names or emails.
              </p>
            </div>
            <button type="button" role="switch" aria-checked={ai.store_enabled} aria-label="AI features"
              onClick={toggleAi} disabled={savingAi || !ai.admin_store_enabled}
              className={`relative shrink-0 inline-flex h-6 w-11 items-center rounded-full transition-colors disabled:opacity-50 ${ai.store_enabled ? 'bg-primary-600' : 'bg-gray-300 dark:bg-gray-600'}`}>
              <span className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${ai.store_enabled ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </button>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {ai.available
              ? `On · ${ai.used_today} of ${ai.daily_limit} AI requests used today${ai.model ? ` · model ${ai.model}` : ''}`
              : ai.message || 'AI is not available.'}
          </p>
        </div>
      )}

      <form onSubmit={changePwd} className="space-y-4 bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700">
        <h2 className="font-semibold text-gray-900 dark:text-white">Change password</h2>
        <input type="password" placeholder="Current password" value={pwd.current_password} onChange={(e) => setPwd({ ...pwd, current_password: e.target.value })} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white" />
        <input type="password" placeholder="New password" value={pwd.new_password} onChange={(e) => setPwd({ ...pwd, new_password: e.target.value })} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white" />
        <input type="password" placeholder="Confirm new password" value={pwd.confirm} onChange={(e) => setPwd({ ...pwd, confirm: e.target.value })} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white" />
        <div className="flex justify-end">
          <button type="submit" disabled={changingPwd} className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg disabled:opacity-60">
            {changingPwd ? 'Updating...' : 'Update password'}
          </button>
        </div>
      </form>
    </div>
  );
};
