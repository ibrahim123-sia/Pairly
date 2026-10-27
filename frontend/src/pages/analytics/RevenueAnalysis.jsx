import { useState, useEffect } from "react";
import api from '../../api/axiosClient';
import { DataTable } from "../../components/DataTable";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { DollarSign, TrendingUp, BarChart3, Target, Globe, Users, Filter } from "lucide-react";

export const RevenueAnalysis = () => {
  const [loading, setLoading] = useState(true);
  const [revenueData, setRevenueData] = useState([]);
  const [filters, setFilters] = useState({
    limit: 10,
    country: 'all',
    year: 'all',
  });

  const [availableFilters, setAvailableFilters] = useState({
    countries: [],
    years: []
  });

  useEffect(() => {
    fetchAvailableFilters();
  }, []);

  useEffect(() => {
    fetchRevenueAnalysis();
  }, [filters]);

  const fetchAvailableFilters = async () => {
    try {
      const response = await api.get("/analytics/filters");
      if (response.data.success) {
        setAvailableFilters({
          countries: response.data.filters.countries || [],
          years: response.data.filters.years || []
        });
      }
    } catch (error) {
      console.error("Error fetching filters:", error);
    }
  };

  const fetchRevenueAnalysis = async () => {
    setLoading(true);
    try {
      // Use the new revenue by country endpoint with filters
      const response = await api.get("/analytics/revenue_by_country", {
        params: filters,
      });

      if (response.data.success) {
        setRevenueData(response.data.revenue_analysis || []);
      } else {
        console.error('API error:', response.data.error);
        setRevenueData([]);
      }
    } catch (error) {
      console.error("Error fetching revenue analysis:", error);
      setRevenueData([]);
    } finally {
      setLoading(false);
    }
  };

  const handleResetFilters = () => {
    setFilters({
      limit: 10,
      country: 'all',
      year: 'all',
    });
  };

  const columns = [
    {
      key: "country",
      title: "Country",
      sortable: true,
      render: (value, row) => (
        <div className="flex items-center">
          <Globe className="h-4 w-4 text-gray-400 mr-2" />
          <div>
            <div className="font-medium text-gray-900 dark:text-white">
              {value || 'Unknown'}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              Market share: {row.market_share?.toFixed(1) || '0.0'}%
            </div>
          </div>
        </div>
      ),
    },
    {
      key: "total_revenue",
      title: "Total Revenue",
      sortable: true,
      render: (value) => (
        <div className="text-right">
          <div className="flex items-center justify-end">
            <DollarSign className="h-4 w-4 text-gray-400 mr-1" />
            <span className="font-bold text-gray-900 dark:text-white">
              {typeof value === "number"
                ? value.toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })
                : "0.00"}
            </span>
          </div>
        </div>
      ),
    },
    {
      key: "transaction_count",
      title: "Transactions",
      sortable: true,
      render: (value) => (
        <div className="text-center">
          <span className="font-bold text-gray-900 dark:text-white">
            {typeof value === "number" ? value.toLocaleString() : "0"}
          </span>
        </div>
      ),
    },
    {
      key: "customer_count",
      title: "Customers",
      sortable: true,
      render: (value) => (
        <div className="text-center">
          <div className="flex items-center justify-center">
            <Users className="h-4 w-4 text-gray-400 mr-1" />
            <span className="font-bold text-gray-900 dark:text-white">
              {typeof value === "number" ? value.toLocaleString() : "0"}
            </span>
          </div>
        </div>
      ),
    },
    {
      key: "avg_transaction_value",
      title: "Avg. Transaction",
      sortable: true,
      render: (value) => (
        <div className="text-right">
          <div className="flex items-center justify-end">
            <DollarSign className="h-4 w-4 text-gray-400 mr-1" />
            <span className="font-bold text-gray-900 dark:text-white">
              {typeof value === "number" ? value.toFixed(2) : "0.00"}
            </span>
          </div>
        </div>
      ),
    },
    {
      key: "revenue_per_customer",
      title: "Per Customer",
      sortable: true,
      render: (value) => (
        <div className="text-right">
          <div className="flex items-center justify-end">
            <DollarSign className="h-4 w-4 text-gray-400 mr-1" />
            <span className="font-bold text-gray-900 dark:text-white">
              {typeof value === "number" ? value.toFixed(2) : "0.00"}
            </span>
          </div>
        </div>
      ),
    },
  ];

  const calculateTotals = () => {
    if (revenueData.length === 0) {
      return {
        totalRevenue: 0,
        totalTransactions: 0,
        totalCustomers: 0,
        avgTransaction: 0,
        count: 0
      };
    }

    const totals = revenueData.reduce(
      (acc, item) => ({
        totalRevenue: acc.totalRevenue + (item.total_revenue || 0),
        totalTransactions: acc.totalTransactions + (item.transaction_count || 0),
        totalCustomers: acc.totalCustomers + (item.customer_count || 0),
        count: acc.count + 1,
      }),
      { totalRevenue: 0, totalTransactions: 0, totalCustomers: 0, count: 0 }
    );
    
    totals.avgTransaction = totals.totalTransactions > 0 ? 
      totals.totalRevenue / totals.totalTransactions : 0;
    
    return totals;
  };

  const totals = calculateTotals();

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Revenue Analysis
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Financial performance analysis by country with filters
        </p>
      </div>

      {/* Custom Filter Panel for Revenue Analysis */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center">
            <Filter className="h-5 w-5 text-blue-600 mr-2" />
            <h3 className="font-semibold text-gray-900 dark:text-white">Revenue Analysis Filters</h3>
          </div>
          <button
            onClick={handleResetFilters}
            className="flex items-center px-3 py-1.5 text-sm bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            Reset Filters
          </button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Limit Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Show Top {filters.limit} Countries
            </label>
            <input
              type="range"
              min="5"
              max="50"
              step="5"
              value={filters.limit}
              onChange={(e) => setFilters({...filters, limit: parseInt(e.target.value)})}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>5</span>
              <span>50</span>
            </div>
          </div>

          {/* Country Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Country
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

          {/* Year Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Year
            </label>
            <select
              value={filters.year}
              onChange={(e) => setFilters({...filters, year: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
            >
              <option value="all">All Years</option>
              {availableFilters.years.map((year) => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Revenue Stats */}
      {!loading && revenueData.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="card">
            <div className="flex items-center">
              <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20">
                <DollarSign className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Total Revenue
                </p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  $
                  {totals.totalRevenue.toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="flex items-center">
              <div className="p-3 rounded-lg bg-green-50 dark:bg-green-900/20">
                <TrendingUp className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Total Transactions
                </p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {totals.totalTransactions.toLocaleString()}
                </p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="flex items-center">
              <div className="p-3 rounded-lg bg-purple-50 dark:bg-purple-900/20">
                <Users className="h-6 w-6 text-purple-600 dark:text-purple-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Total Customers
                </p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {totals.totalCustomers.toLocaleString()}
                </p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="flex items-center">
              <div className="p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20">
                <Target className="h-6 w-6 text-yellow-600 dark:text-yellow-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Avg. Transaction
                </p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  ${totals.avgTransaction.toFixed(2)}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Revenue Table */}
      <div className="card">
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Country Revenue Analysis
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Revenue distribution and performance metrics by country
          </p>
        </div>

        {loading ? (
          <LoadingSpinner text="Loading revenue data..." />
        ) : revenueData.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-400 dark:text-gray-500 mb-4">
              <BarChart3 className="h-12 w-12 mx-auto" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No revenue data available
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Try adjusting your filters to see revenue analysis
            </p>
            <div className="flex flex-col md:flex-row gap-3 justify-center">
              <button
                onClick={() => setFilters({...filters, country: 'all', year: 'all'})}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Show All Countries
              </button>
              <button
                onClick={fetchRevenueAnalysis}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
              >
                Retry Loading
              </button>
            </div>
          </div>
        ) : (
          <>
            <DataTable
              columns={columns}
              data={revenueData}
              itemsPerPage={10}
              onRowClick={(item) => console.log("Country selected:", item)}
            />
            <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Showing {Math.min(filters.limit, revenueData.length)} of {revenueData.length} countries
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    Global Average Transaction: <span className="text-blue-600">${totals.avgTransaction.toFixed(2)}</span>
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Across all countries and customers
                  </p>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};