import { useState, useEffect } from 'react';
import api from '../api/axiosClient';
import { DataTable } from '../components/DataTable';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { Package, TrendingUp, DollarSign, Tag, RefreshCw, AlertCircle, ShoppingCart, Filter, Globe } from 'lucide-react';

export const ProductBundles = () => {
  const [loading, setLoading] = useState(false);
  const [bundles, setBundles] = useState([]);
  const [metadata, setMetadata] = useState(null);
  const [filters, setFilters] = useState({
    min_confidence: 0.3,
    min_transactions: 5,
    country: 'all',
    product: 'all',
  });

  const [availableFilters, setAvailableFilters] = useState({
    countries: [],
    products: []
  });

  useEffect(() => {
    fetchAvailableFilters();
  }, []);

  useEffect(() => {
    fetchBundles();
  }, [filters]);

  const fetchAvailableFilters = async () => {
    try {
      const response = await api.get('/analytics/filters');
      if (response.data.success) {
        setAvailableFilters({
          countries: response.data.filters.countries || [],
          products: response.data.filters.products || []
        });
      }
    } catch (error) {
      console.error('Error fetching filters:', error);
    }
  };

  const fetchBundles = async () => {
    setLoading(true);
    try {
      // Use the filtered bundles endpoint
      const response = await api.get('/analytics/product_bundles_filtered', {
        params: filters,
      });

      if (response.data.success) {
        setBundles(response.data.bundles || []);
        setMetadata(response.data.metadata || null);
      } else {
        console.error('API returned error:', response.data.error);
        setBundles([]);
        setMetadata(null);
      }
    } catch (error) {
      console.error('Error fetching bundles:', error);
      setBundles([]);
      setMetadata(null);
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = () => {
    fetchBundles();
  };

  const handleResetFilters = () => {
    setFilters({
      min_confidence: 0.3,
      min_transactions: 5,
      country: 'all',
      product: 'all',
    });
  };

  const columns = [
    {
      key: 'bundle_id',
      title: 'Bundle ID',
      sortable: true,
      render: (value) => (
        <span className="font-mono font-bold text-blue-600 dark:text-blue-400">{value}</span>
      ),
    },
    {
      key: 'bundle_name',
      title: 'Bundle Name',
      sortable: true,
      render: (value, row) => (
        <div>
          <div className="font-medium text-gray-900 dark:text-white">
            {value}
          </div>
          <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
            Main products: {row.main_products?.slice(0, 2).map(p => p.substring(0, 20)).join(' + ')}
          </div>
        </div>
      ),
    },
    {
      key: 'transaction_count',
      title: 'Transactions',
      sortable: true,
      render: (value) => (
        <div className="text-center">
          <div className="flex items-center justify-center">
            <ShoppingCart className="h-4 w-4 text-gray-400 mr-1" />
            <span className="font-bold text-gray-900 dark:text-white">{value || 0}</span>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">co-occurrences</div>
        </div>
      ),
    },
    {
      key: 'confidence',
      title: 'Confidence',
      sortable: true,
      render: (value) => (
        <div className="text-center">
          <span className="font-bold text-gray-900 dark:text-white">
            {value ? (value * 100).toFixed(1) + '%' : '0%'}
          </span>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 mt-1">
            <div
              className="bg-green-600 h-1.5 rounded-full"
              style={{ width: `${value ? Math.min(value * 100, 100) : 0}%` }}
            ></div>
          </div>
        </div>
      ),
    },
    // {
    //   key: 'estimated_revenue',
    //   title: 'Est. Revenue',
    //   sortable: true,
    //   render: (value) => (
    //     <div className="text-right">
    //       <div className="flex items-center justify-end">
    //         <DollarSign className="h-4 w-4 text-gray-400 mr-1" />
    //         <span className="font-bold text-gray-900 dark:text-white">
    //           ${typeof value === 'number' ? value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}
    //         </span>
    //       </div>
    //       <div className="text-xs text-gray-500 dark:text-gray-400">total revenue</div>
    //     </div>
    //   ),
    // },
    {
      key: 'lift',
      title: 'Lift',
      sortable: true,
      render: (value) => (
        <div
          className={`font-bold text-center ${
            value > 1.5
              ? 'text-green-600'
              : value > 1
              ? 'text-yellow-600'
              : 'text-red-600'
          }`}
        >
          {typeof value === 'number' ? value.toFixed(2) : '0.00'}
          {value > 1 && <TrendingUp className="inline-block ml-1 h-4 w-4" />}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Suggested Product Bundles
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Intelligent product bundles based on co-purchase patterns
        </p>
      </div>

      {/* Custom Filter Panel for Product Bundles */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center">
            <Filter className="h-5 w-5 text-blue-600 mr-2" />
            <h3 className="font-semibold text-gray-900 dark:text-white">Product Bundles Filters</h3>
          </div>
          <button
            onClick={handleResetFilters}
            className="flex items-center px-3 py-1.5 text-sm bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            <RefreshCw className="h-3 w-3 mr-1" />
            Reset
          </button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Confidence Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Min Confidence ({(filters.min_confidence * 100).toFixed(0)}%)
            </label>
            <input
              type="range"
              min="0.1"
              max="1.0"
              step="0.01"
              value={filters.min_confidence}
              onChange={(e) => setFilters({...filters, min_confidence: parseFloat(e.target.value)})}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>10%</span>
              <span>100%</span>
            </div>
          </div>

          {/* Transaction Count Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Min Transactions ({filters.min_transactions})
            </label>
            <input
              type="range"
              min="2"
              max="50"
              step="1"
              value={filters.min_transactions}
              onChange={(e) => setFilters({...filters, min_transactions: parseInt(e.target.value)})}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>2</span>
              <span>50</span>
            </div>
          </div>

          {/* Country Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              <div className="flex items-center">
                <Globe className="h-4 w-4 mr-1" />
                Country
              </div>
            </label>
            <select
              value={filters.country}
              onChange={(e) => setFilters({...filters, country: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
            >
              <option value="all">All Countries</option>
              {availableFilters.countries.map((country) => (
                <option key={country} value={country}>{country}</option>
              ))}
            </select>
          </div>

          {/* Product Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Base Product
            </label>
            <select
              value={filters.product}
              onChange={(e) => setFilters({...filters, product: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
            >
              <option value="all">All Products</option>
              {availableFilters.products.slice(0, 50).map((product) => (
                <option key={product} value={product}>{product.length > 30 ? product.substring(0, 30) + '...' : product}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

     


      {/* Bundles Table */}
      <div className="card">
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Recommended Product Bundles
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Suggested bundles based on co-purchase patterns with confidence ≥ {(filters.min_confidence * 100).toFixed(0)}%
            {metadata?.filtered_records && ` • From ${metadata.filtered_records.toLocaleString()} filtered records`}
          </p>
        </div>

        {loading ? (
          <LoadingSpinner text="Finding product bundles..." />
        ) : bundles.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-400 dark:text-gray-500 mb-4">
              <Package className="h-12 w-12 mx-auto" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No bundles found
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              This could be because:
            </p>
            <ul className="text-sm text-gray-600 dark:text-gray-400 text-left max-w-md mx-auto mb-6 space-y-2">
              <li className="flex items-start">
                <AlertCircle className="h-4 w-4 mr-2 mt-0.5 text-yellow-500" />
                <span>Confidence threshold is too high (try 20% instead of 30%)</span>
              </li>
              <li className="flex items-start">
                <AlertCircle className="h-4 w-4 mr-2 mt-0.5 text-yellow-500" />
                <span>Minimum transaction count is too high (try 2 instead of 5)</span>
              </li>
              <li className="flex items-start">
                <AlertCircle className="h-4 w-4 mr-2 mt-0.5 text-yellow-500" />
                <span>Filters are too restrictive (try removing filters)</span>
              </li>
              <li className="flex items-start">
                <AlertCircle className="h-4 w-4 mr-2 mt-0.5 text-yellow-500" />
                <span>Dataset has few co-purchased products</span>
              </li>
            </ul>
            <div className="flex justify-center space-x-4">
              <button 
                onClick={() => setFilters({...filters, min_confidence: 0.2, min_transactions: 2})}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                Try Lower Thresholds
              </button>
              <button 
                onClick={handleRetry}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <RefreshCw className="inline-block h-4 w-4 mr-1" />
                Retry
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="mb-4 text-sm text-gray-600 dark:text-gray-400">
              Found {bundles.length} product bundles from {metadata?.top_products_analyzed || 0} top products. 
              Lift &gt; 1 indicates products are purchased together more often than expected.
            </div>
            <DataTable
              columns={columns}
              data={bundles}
              itemsPerPage={10}
              onRowClick={(bundle) => console.log('Bundle selected:', bundle)}
            />
            {metadata && (
              <div className="mt-4 text-xs text-gray-500 dark:text-gray-400">
                Analyzed {metadata.top_products_analyzed} top products • 
                Minimum {metadata.min_transactions} transactions per bundle • 
                Filtered from {metadata.filtered_records} records • 
                {metadata.filters_applied?.country && ` Country: ${metadata.filters_applied.country}`}
                {metadata.filters_applied?.product && ` • Product: ${metadata.filters_applied.product}`}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};