import { useEffect, useState } from 'react';
import { adminStatsApi } from '../../api/adminApi';
import { Store, Users, Database, ShieldCheck } from 'lucide-react';
import { Link } from 'react-router-dom';
import { AdminAIPanel } from '../../components/AdminAIPanel';

const Stat = ({ icon: Icon, label, value, color = 'text-primary-600' }) => (
  <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 flex items-center space-x-4">
    <div className={`p-3 rounded-lg bg-primary-50 dark:bg-primary-900/20 ${color}`}>
      <Icon className="h-6 w-6" />
    </div>
    <div>
      <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
    </div>
  </div>
);

export const AdminDashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminStatsApi()
      .then((r) => setStats(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Platform Overview</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Global stats across all stores</p>
        </div>
        <Link to="/admin/stores/new" className="bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium px-4 py-2 rounded-lg">
          + New Store
        </Link>
      </div>
      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Stat icon={Store} label="Total Stores" value={stats?.total_stores ?? 0} />
          <Stat icon={ShieldCheck} label="Active Stores" value={stats?.active_stores ?? 0} />
          <Stat icon={Users} label="Store Managers" value={stats?.total_managers ?? 0} />
          <Stat icon={Database} label="Datasets" value={stats?.total_datasets ?? 0} />
        </div>
      )}
      <AdminAIPanel />
    </div>
  );
};
