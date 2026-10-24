import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listStoresApi, disableStoreApi, enableStoreApi, resetManagerPasswordApi } from '../../api/adminApi';
import { CheckCircle2, XCircle, KeyRound } from 'lucide-react';
import toast from 'react-hot-toast';

export const Stores = () => {
  const [stores, setStores] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const res = await listStoresApi({ per_page: 100 });
      setStores(res.data.items);
    } catch {
      toast.error('Could not load stores');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const toggle = async (s) => {
    try {
      if (s.is_active) {
        const reason = prompt('Reason for disabling this store? (optional)') || '';
        await disableStoreApi(s.id, reason);
        toast.success('Store disabled');
      } else {
        await enableStoreApi(s.id);
        toast.success('Store enabled');
      }
      load();
    } catch (e) {
      toast.error(e.response?.data?.error || 'Action failed');
    }
  };

  const resetPwd = async (s) => {
    if (!confirm(`Reset password for the manager of ${s.name}?`)) return;
    try {
      const res = await resetManagerPasswordApi(s.id);
      if (res.data.temp_password) {
        prompt('Email could not be sent. Copy temporary password:', res.data.temp_password);
      } else {
        toast.success('New password emailed to manager');
      }
    } catch (e) {
      toast.error(e.response?.data?.error || 'Reset failed');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Stores</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Create and manage retail stores</p>
        </div>
        <Link to="/admin/stores/new" className="bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium px-4 py-2 rounded-lg">
          + New Store
        </Link>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {loading ? (
          <p className="p-6 text-gray-500">Loading...</p>
        ) : stores.length === 0 ? (
          <div className="p-12 text-center text-gray-500">
            No stores yet. <Link to="/admin/stores/new" className="text-primary-600 hover:underline">Create the first one</Link>.
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900 text-xs uppercase text-gray-500 dark:text-gray-400">
              <tr>
                <th className="px-4 py-3 text-left">Store</th>
                <th className="px-4 py-3 text-left">Manager</th>
                <th className="px-4 py-3 text-left">Datasets</th>
                <th className="px-4 py-3 text-left">Last upload</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700 text-sm">
              {stores.map((s) => (
                <tr key={s.id}>
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900 dark:text-white">{s.name}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">/{s.slug}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-700 dark:text-gray-300">
                    {s.manager_name ? <div>{s.manager_name}</div> : null}
                    <div className="text-xs text-gray-500 dark:text-gray-400">{s.manager_email}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-700 dark:text-gray-300">{s.dataset_count ?? 0}</td>
                  <td className="px-4 py-3 text-gray-700 dark:text-gray-300">
                    {s.last_upload_at ? new Date(s.last_upload_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-4 py-3">
                    {s.is_active ? (
                      <span className="inline-flex items-center text-green-600 text-xs"><CheckCircle2 className="h-4 w-4 mr-1" /> Active</span>
                    ) : (
                      <span className="inline-flex items-center text-red-600 text-xs"><XCircle className="h-4 w-4 mr-1" /> Disabled</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <button onClick={() => resetPwd(s)} className="text-gray-500 hover:text-primary-600" title="Reset manager password">
                      <KeyRound className="h-4 w-4 inline" />
                    </button>
                    <button onClick={() => toggle(s)} className={`text-xs font-medium px-3 py-1 rounded-md ${s.is_active ? 'bg-red-50 text-red-600 hover:bg-red-100' : 'bg-green-50 text-green-600 hover:bg-green-100'}`}>
                      {s.is_active ? 'Disable' : 'Enable'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
