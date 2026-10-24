import { useState, useEffect } from 'react';
import api from '../api/axiosClient';
import {
  ShoppingCart,
  Package,
  Users,
  DollarSign,
  TrendingUp,
  BarChart3,
  Database,
  AlertCircle,
} from 'lucide-react';
import { StatCard } from '../components/StatCard';
import { DataTable } from '../components/DataTable';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { AIInsightsCard } from '../components/AIInsightsCard';

// Same thresholds as the rules table below, so the insights describe what the page shows.
const INSIGHT_PARAMS = { min_support: 0.01, min_confidence: 0.3, min_lift: 1.0 };

export const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [topProducts, setTopProducts] = useState([]);
  const [recentRules, setRecentRules] = useState([]);
  const [healthStatus, setHealthStatus] = useState('');

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // Fetch summary - no filters for dashboard
      const summaryRes = await api.get('/analytics/summary');
      if (summaryRes.data.success) {
        setSummary(summaryRes.data.data);
        
        // Determine health status
        const dataHealth = summaryRes.data.data?.data_quality?.data_completeness || 0;
        if (dataHealth >= 90) setHealthStatus('Excellent');
        else if (dataHealth >= 80) setHealthStatus('Good');
        else if (dataHealth >= 70) setHealthStatus('Fair');
        else setHealthStatus('Poor');
      }

      // Fetch top products with default sorting
      const productsRes = await api.get('/analytics/top_products', {
        params: { 
          limit: 5,
          sort_by: 'revenue'
        }
      });
      if (productsRes.data.success) {
        setTopProducts(productsRes.data.products || []);
      }

      // Fetch recent rules with easy settings
      const rulesRes = await api.get('/analytics/association_rules', {
        params: { 
          limit: 5, 
          simple: true,
          min_support: 0.01,
          min_confidence: 0.3
        }
      });
      if (rulesRes.data.success) {
        setRecentRules(rulesRes.data.data || []);
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const statCards = [
    {
      title: 'Total Transactions',
      value: summary?.total_transactions?.toLocaleString() || '0',
      icon: ShoppingCart,
      color: 'blue'
    },
    {
      title: 'Total Products',
      value: summary?.total_products?.toLocaleString() || '0',
      icon: Package,
      color: 'purple'
    },
       {
      title: 'Total Customers',
      value: summary?.total_customers?.toLocaleString() || '0',
      icon: Users,
      color: 'green'
    },
   
    {
      title: 'Total Revenue',
      value: `$${summary?.total_revenue?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}`,
      icon: DollarSign,
      color: 'yellow'
    },
  ];

  const productColumns = [
    { 
      key: 'description', 
      title: 'Product', 
      sortable: true,
      render: (value) => (
        <div className="max-w-xs truncate" title={value}>
          {value || 'Unknown Product'}
        </div>
      )
    },
    { 
      key: 'total_revenue', 
      title: 'Revenue', 
      sortable: true, 
      render: (value) => `$${typeof value === 'number' ? value.toFixed(2) : '0.00'}` 
    },
    { 
      key: 'transactions', 
      title: 'Transactions', 
      sortable: true,
      render: (value) => value?.toLocaleString() || '0'
    },
    { 
      key: 'revenue_share', 
      title: 'Share', 
      sortable: true,
      render: (value) => `${value?.toFixed(1) || '0.0'}%`
    },
  ];

  const rulesColumns = [
    { 
      key: 'rule', 
      title: 'Association Rule', 
      sortable: false,
      render: (value) => (
        <div className="max-w-xs truncate" title={value}>
          {value || 'No rule'}
        </div>
      )
    },
    { 
      key: 'confidence', 
      title: 'Confidence', 
      sortable: true, 
      render: (value) => `${(typeof value === 'number' ? value * 100 : 0).toFixed(1)}%` 
    },
    { 
      key: 'lift', 
      title: 'Lift', 
      sortable: true, 
      render: (value) => (
        <span className={`font-bold ${value > 1.5 ? 'text-green-600' : value > 1 ? 'text-yellow-600' : 'text-red-600'}`}>
          {typeof value === 'number' ? value.toFixed(2) : '0.00'}
          {value > 1 && <TrendingUp className="inline-block ml-1 h-4 w-4" />}
        </span>
      ) 
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Dashboard Overview
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Which products sell together, and what to do about it
        </p>
      </div>

      {/* Data Health Alert */}
      {summary?.data_quality?.data_completeness < 80 && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <div className="flex items-center">
            <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 mr-3" />
            <div>
              <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-300">
                Data Quality Alert
              </h3>
              <p className="text-sm text-yellow-700 dark:text-yellow-400 mt-1">
                Data completeness is {summary.data_quality?.data_completeness}%. 
                Consider improving data quality for better analysis results.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => (
          <StatCard 
            key={index} 
            loading={loading} 
            title={stat.title}
            value={stat.value}
            icon={stat.icon}
            color={stat.color}
          />
        ))}
      </div>

      <AIInsightsCard params={INSIGHT_PARAMS} />

      {/* Additional Metrics */}
      {summary && !loading && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="card">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Avg Transaction Value
                </p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">
                  ${summary.avg_transaction_value?.toFixed(2) || '0.00'}
                </p>
              </div>
              <DollarSign className="h-6 w-6 text-green-600" />
            </div>
          </div>
          <div className="card">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Multi-item Transactions
                </p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">
                  {summary.data_quality?.multi_item_transactions?.toLocaleString() || '0'}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  ({summary.multi_item_percentage?.toFixed(1) || '0'}%)
                </p>
              </div>
              <ShoppingCart className="h-6 w-6 text-blue-600" />
            </div>
          </div>
          <div className="card">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Data Health
                </p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">
                  {healthStatus}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {summary.data_quality?.data_completeness || '0'}% complete
                </p>
              </div>
              <Database className="h-6 w-6 text-purple-600" />
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Products */}
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Top Products by Revenue
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Best performing products
              </p>
            </div>
            <TrendingUp className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          </div>
          {loading ? (
            <LoadingSpinner />
          ) : topProducts.length > 0 ? (
            <DataTable
              columns={productColumns}
              data={topProducts}
              itemsPerPage={5}
              className="border-none shadow-none"
            />
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500 dark:text-gray-400">No product data available</p>
            </div>
          )}
        </div>

        {/* Recent Association Rules */}
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Recent Association Rules
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Top product associations with confidence ≥ 30%
              </p>
            </div>
            <BarChart3 className="h-5 w-5 text-purple-600 dark:text-purple-400" />
          </div>
          {loading ? (
            <LoadingSpinner />
          ) : recentRules.length > 0 ? (
            <DataTable
              columns={rulesColumns}
              data={recentRules}
              itemsPerPage={5}
              className="border-none shadow-none"
            />
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500 dark:text-gray-400">No association rules found</p>
              <button 
                onClick={fetchDashboardData}
                className="mt-3 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Refresh Data
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Quick Links */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Quick Analysis
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <a 
            href="/association-rules" 
            className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors"
          >
            <h4 className="font-medium text-blue-800 dark:text-blue-300">Association Rules</h4>
            <p className="text-sm text-blue-700 dark:text-blue-400 mt-1">
              Discover product relationships
            </p>
          </a>
          <a 
            href="/product-bundles" 
            className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/30 transition-colors"
          >
            <h4 className="font-medium text-green-800 dark:text-green-300">Product Bundles</h4>
            <p className="text-sm text-green-700 dark:text-green-400 mt-1">
              Find co-purchase patterns
            </p>
          </a>
          <a 
            href="/seasonal-analysis" 
            className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg hover:bg-purple-100 dark:hover:bg-purple-900/30 transition-colors"
          >
            <h4 className="font-medium text-purple-800 dark:text-purple-300">Seasonal Analysis</h4>
            <p className="text-sm text-purple-700 dark:text-purple-400 mt-1">
              Analyze time-based patterns
            </p>
          </a>
        </div>
      </div>
    </div>
  );
};