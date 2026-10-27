import { useState, useEffect } from 'react';
import api from '../../api/axiosClient';
import { DataTable } from '../../components/DataTable';
import { LoadingSpinner } from '../../components/LoadingSpinner';
import { Database, BarChart, PieChart, LineChart, CheckCircle, AlertCircle, TrendingUp, RefreshCw, Users } from 'lucide-react';

export const DataSummary = () => {
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [topProducts, setTopProducts] = useState([]);
  const [healthStatus, setHealthStatus] = useState('');

  useEffect(() => {
    fetchDataSummary();
    fetchTopProducts();
  }, []);

  const fetchDataSummary = async () => {
    setLoading(true);
    try {
      const response = await api.get('/analytics/summary');
      if (response.data.success) {
        setSummary(response.data.data);
        
        // Determine health status
        const dataHealth = response.data.data?.data_quality?.data_completeness || 0;
        if (dataHealth >= 90) setHealthStatus('Excellent');
        else if (dataHealth >= 80) setHealthStatus('Good');
        else if (dataHealth >= 70) setHealthStatus('Fair');
        else setHealthStatus('Poor');
      }
    } catch (error) {
      console.error('Error fetching data summary:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTopProducts = async () => {
    try {
      const response = await api.get('/analytics/top_products', {
        params: { limit: 5, sort_by: 'revenue' }
      });
      if (response.data.success) {
        setTopProducts(response.data.products || []);
      }
    } catch (error) {
      console.error('Error fetching top products:', error);
    }
  };

  if (loading) {
    return <LoadingSpinner text="Loading data summary..." />;
  }

  if (!summary) {
    return (
      <div className="text-center py-12">
        <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
          No data available
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Unable to load data summary. Check backend connection.
        </p>
        <button 
          onClick={fetchDataSummary}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <RefreshCw className="inline-block h-4 w-4 mr-2" />
          Retry
        </button>
      </div>
    );
  }

  const dataQualityItems = [
    { 
      label: 'Total Records', 
      value: summary.data_quality?.total_records?.toLocaleString() || '0',
      icon: Database 
    },
    { 
      label: 'Data Completeness', 
      value: `${summary.data_quality?.data_completeness || '0'}%`,
      icon: CheckCircle 
    },
    { 
      label: 'Data Health', 
      value: healthStatus,
      icon: TrendingUp 
    },
    { 
      label: 'Multi-item Transactions', 
      value: summary.data_quality?.multi_item_transactions?.toLocaleString() || '0',
      icon: BarChart 
    },
    { 
      label: 'Multi-item Percentage', 
      value: `${summary.multi_item_percentage || '0'}%`,
      icon: PieChart 
    },
  ];

  const businessMetrics = [
    { 
      label: 'Avg Transaction Value', 
      value: `$${summary.avg_transaction_value?.toFixed(2) || '0.00'}`,
      icon: LineChart 
    },
    { 
      label: 'Total Countries', 
      value: summary.total_countries || '0',
      icon: Database 
    },
    { 
      label: 'Revenue per Transaction', 
      value: `$${summary.data_quality?.revenue_per_transaction?.toFixed(2) || '0.00'}`,
      icon: TrendingUp 
    },
    { 
      label: 'Unique Products per Transaction', 
      value: summary.avg_basket_size?.toFixed(1) || '0.0',
      icon: BarChart 
    },
  ];

  const dataIssues = [
    { 
      label: 'Missing Customers', 
      value: summary.data_quality?.missing_customers?.toLocaleString() || '0',
      severity: summary.data_quality?.missing_customers > 0 ? 'warning' : 'good' 
    },
    { 
      label: 'Missing Descriptions', 
      value: summary.data_quality?.missing_descriptions?.toLocaleString() || '0',
      severity: summary.data_quality?.missing_descriptions > 0 ? 'warning' : 'good' 
    },
    { 
      label: 'Missing Prices', 
      value: summary.data_quality?.missing_prices?.toLocaleString() || '0',
      severity: summary.data_quality?.missing_prices > 0 ? 'warning' : 'good' 
    },
    { 
      label: 'Missing Quantities', 
      value: summary.data_quality?.missing_quantities?.toLocaleString() || '0',
      severity: summary.data_quality?.missing_quantities > 0 ? 'warning' : 'good' 
    },
  ];

  const dateRangeItems = [
    { label: 'Data Range', value: summary.date_range?.days ? `${summary.date_range.days} days` : 'N/A' },
    { label: 'From', value: summary.date_range?.start || 'N/A' },
    { label: 'To', value: summary.date_range?.end || 'N/A' },
    { label: 'Association Readiness', value: summary.multi_item_percentage > 20 ? 'Ready' : 'Limited' },
  ];

  const topProductsColumns = [
    { key: 'description', title: 'Product', sortable: true, render: (value) => (
      <div className="max-w-xs truncate" title={value}>{value || 'Unknown'}</div>
    )},
    { key: 'total_revenue', title: 'Revenue', sortable: true, render: (value) => `$${typeof value === 'number' ? value.toFixed(2) : '0.00'}` },
    { key: 'transactions', title: 'Transactions', sortable: true, render: (value) => value?.toLocaleString() || '0' },
    { key: 'revenue_share', title: 'Share', sortable: true, render: (value) => `${value?.toFixed(1) || '0.0'}%` },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Data Summary
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Comprehensive overview of your dataset and business metrics
        </p>
      </div>

      {/* Data Health Warning */}
      {summary.data_quality?.data_completeness < 80 && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <div className="flex">
            <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 mt-0.5" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-300">
                Data Quality Alert
              </h3>
              <div className="mt-2 text-sm text-yellow-700 dark:text-yellow-400">
                <p>
                  Data completeness is {summary.data_quality?.data_completeness}%. Issues detected:
                </p>
                <ul className="list-disc pl-5 mt-1">
                  {summary.data_quality?.missing_customers > 0 && <li>{summary.data_quality.missing_customers} missing customer IDs</li>}
                  {summary.data_quality?.missing_descriptions > 0 && <li>{summary.data_quality.missing_descriptions} missing product descriptions</li>}
                  {summary.data_quality?.missing_prices > 0 && <li>{summary.data_quality.missing_prices} missing prices</li>}
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Association Rules Warning */}
      {summary.multi_item_percentage < 30 && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="flex">
            <AlertCircle className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800 dark:text-blue-300">
                Association Rules Readiness
              </h3>
              <div className="mt-2 text-sm text-blue-700 dark:text-blue-400">
                <p>
                  Only {summary.multi_item_percentage}% of transactions have multiple items.
                  Association rules work best when many customers buy multiple products together.
                </p>
                <p className="mt-1">
                  <strong>Transactions with multiple items:</strong> {summary.data_quality?.multi_item_transactions?.toLocaleString() || '0'} / {summary.total_transactions?.toLocaleString() || '0'}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center">
            <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20">
              <Database className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Total Transactions
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {summary.total_transactions?.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-3 rounded-lg bg-green-50 dark:bg-green-900/20">
              <BarChart className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Total Revenue
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                ${summary.total_revenue?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-3 rounded-lg bg-purple-50 dark:bg-purple-900/20">
              <PieChart className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Total Products
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {summary.total_products?.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        {/* Total Customers Card - Added */}
        <div className="card">
          <div className="flex items-center">
            <div className="p-3 rounded-lg bg-orange-50 dark:bg-orange-900/20">
              <Users className="h-6 w-6 text-orange-600 dark:text-orange-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Total Customers
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {summary.total_customers?.toLocaleString() || '0'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Data Quality */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Data Quality Metrics
          </h3>
          <div className="space-y-4">
            {dataQualityItems.map((item, index) => (
              <div key={index} className="flex justify-between items-center py-3 border-b border-gray-100 dark:border-gray-700 last:border-0">
                <div className="flex items-center">
                  <div className="p-2 rounded-lg bg-gray-50 dark:bg-gray-800 mr-3">
                    <item.icon className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                  </div>
                  <span className="text-gray-700 dark:text-gray-300">{item.label}</span>
                </div>
                <span className="font-medium text-gray-900 dark:text-white">{item.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Business Metrics */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Business Metrics
          </h3>
          <div className="space-y-4">
            {businessMetrics.map((item, index) => (
              <div key={index} className="flex justify-between items-center py-3 border-b border-gray-100 dark:border-gray-700 last:border-0">
                <div className="flex items-center">
                  <div className="p-2 rounded-lg bg-gray-50 dark:bg-gray-800 mr-3">
                    <item.icon className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                  </div>
                  <span className="text-gray-700 dark:text-gray-300">{item.label}</span>
                </div>
                <span className="font-medium text-gray-900 dark:text-white">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Top Products */}
      {topProducts.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Top 5 Products by Revenue
          </h3>
          <DataTable
            columns={topProductsColumns}
            data={topProducts}
            itemsPerPage={5}
            className="border-none shadow-none"
          />
        </div>
      )}

      {/* Data Issues & Date Range */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Data Issues */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Data Issues
          </h3>
          <div className="space-y-3">
            {dataIssues.map((item, index) => (
              <div key={index} className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">{item.label}</span>
                <span className={`font-medium ${item.severity === 'warning' ? 'text-yellow-600' : 'text-green-600'}`}>
                  {item.value}
                  {item.severity === 'warning' && (
                    <AlertCircle className="inline-block ml-1 h-4 w-4" />
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Date Range */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Date Range & Analysis
          </h3>
          <div className="space-y-3">
            {dateRangeItems.map((item, index) => (
              <div key={index} className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">{item.label}</span>
                <span className={`font-medium ${
                  item.value === 'Ready' ? 'text-green-600' : 
                  item.value === 'Limited' ? 'text-yellow-600' : 
                  'text-gray-900 dark:text-white'
                }`}>
                  {item.value}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Data Health Score */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Data Health Score
          </h3>
          <div className="text-center py-6">
            <div className="inline-flex items-center justify-center">
              <div className="relative">
                <svg className="w-32 h-32">
                  <circle
                    className="text-gray-200 dark:text-gray-700"
                    strokeWidth="10"
                    stroke="currentColor"
                    fill="transparent"
                    r="56"
                    cx="64"
                    cy="64"
                  />
                  <circle
                    className={`${
                      summary.data_quality?.data_completeness >= 90 ? 'text-green-500' : 
                      summary.data_quality?.data_completeness >= 80 ? 'text-yellow-500' : 
                      summary.data_quality?.data_completeness >= 70 ? 'text-orange-500' : 'text-red-500'
                    }`}
                    strokeWidth="10"
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="transparent"
                    r="56"
                    cx="64"
                    cy="64"
                    strokeDasharray={`${(summary.data_quality?.data_completeness || 0) * 3.52} 352`}
                    strokeDashoffset="0"
                    transform="rotate(-90 64 64)"
                  />
                </svg>
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                  <span className="text-3xl font-bold text-gray-900 dark:text-white">
                    {summary.data_quality?.data_completeness || 0}%
                  </span>
                </div>
              </div>
            </div>
            <p className="text-gray-600 dark:text-gray-400 mt-4">
              {summary.data_quality?.data_completeness >= 90 ? 'Excellent data quality' : 
               summary.data_quality?.data_completeness >= 80 ? 'Good data quality' : 
               summary.data_quality?.data_completeness >= 70 ? 'Fair data quality' : 
               'Needs improvement'}
            </p>
          </div>
        </div>
      </div>

      {/* Refresh Button */}
      <div className="flex justify-end">
        <button 
          onClick={() => {
            fetchDataSummary();
            fetchTopProducts();
          }}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh Data Summary
        </button>
      </div>
    </div>
  );
};