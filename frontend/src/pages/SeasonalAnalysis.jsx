import { useState, useEffect } from 'react';
import api from '../api/axiosClient';
import { DataTable } from '../components/DataTable';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { Calendar, Clock, Globe, TrendingUp, BarChart3, TrendingDown, Filter, Package } from 'lucide-react';

export const SeasonalAnalysis = () => {
  const [loading, setLoading] = useState(true);
  const [seasonalData, setSeasonalData] = useState(null);
  const [filters, setFilters] = useState({
    product: 'all',
    year: 'all',
    month: 'all'
  });

  const [availableFilters, setAvailableFilters] = useState({
    products: [],
    years: [],
    months: []
  });

  useEffect(() => {
    fetchAvailableFilters();
  }, []);

  useEffect(() => {
    fetchSeasonalData();
  }, [filters]);

  const fetchAvailableFilters = async () => {
    try {
      const response = await api.get('/analytics/filters');
      if (response.data.success) {
        setAvailableFilters({
          products: response.data.filters.products || [],
          years: response.data.filters.years || [],
          months: response.data.filters.months || []
        });
      }
    } catch (error) {
      console.error('Error fetching filters:', error);
    }
  };

  const fetchSeasonalData = async () => {
    setLoading(true);
    try {
      // Use the seasonal product analysis endpoint
      const response = await api.get('/analytics/seasonal_product_analysis', {
        params: filters
      });
      
      if (response.data.success) {
        setSeasonalData(response.data);
      } else {
        console.error('API error:', response.data.error);
        setSeasonalData(null);
      }
    } catch (error) {
      console.error("Error fetching seasonal data:", error);
      setSeasonalData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleResetFilters = () => {
    setFilters({
      product: 'all',
      year: 'all',
      month: 'all'
    });
  };

  const calculateSeasonalInsights = () => {
    if (!seasonalData || !seasonalData.monthly_data || seasonalData.monthly_data.length === 0) {
      return {
        best_month: 'N/A',
        best_month_revenue: 0,
        peak_hour: 'N/A',
        peak_hour_revenue: 0,
        top_weekday: 'N/A',
        top_weekday_revenue: 0,
        monthly_trend: 0,
      };
    }
    
    const monthlyData = seasonalData.monthly_data || [];
    const hourlyData = seasonalData.hourly_data || [];
    const weekdayData = seasonalData.weekday_data || [];
    
    const bestMonth = monthlyData.reduce((max, month) => 
      month.revenue > max.revenue ? month : max, { revenue: 0, month_name: 'N/A' }
    );
    
    const bestHour = hourlyData.reduce((max, hour) => 
      hour.revenue > max.revenue ? hour : max, { revenue: 0, hour: 'N/A' }
    );
    
    const bestWeekday = weekdayData.reduce((max, day) => 
      day.revenue > max.revenue ? day : max, { revenue: 0, weekday: 'N/A' }
    );
    
    // Calculate trends
    const sortedMonths = [...monthlyData].sort((a, b) => a.month - b.month);
    const monthlyTrend = sortedMonths.length > 1 ? 
      ((sortedMonths[sortedMonths.length-1].revenue / sortedMonths[0].revenue - 1) * 100) || 0 : 0;
    
    return {
      best_month: bestMonth.month_name,
      best_month_revenue: bestMonth.revenue,
      peak_hour: typeof bestHour.hour === 'number' ? `${bestHour.hour}:00` : 'N/A',
      peak_hour_revenue: bestHour.revenue,
      top_weekday: bestWeekday.weekday,
      top_weekday_revenue: bestWeekday.revenue,
      monthly_trend: monthlyTrend,
    };
  };

  const monthColumns = [
    { key: 'month_name', title: 'Month', sortable: true },
    { key: 'revenue', title: 'Revenue', sortable: true, render: (value) => `$${typeof value === 'number' ? value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}` },
    { key: 'transactions', title: 'Transactions', sortable: true, render: (value) => typeof value === 'number' ? value.toLocaleString() : '0' },
    { key: 'quantity', title: 'Quantity', sortable: true, render: (value) => typeof value === 'number' ? value.toLocaleString() : '0' },
    { key: 'products', title: 'Products', sortable: true, render: (value) => typeof value === 'number' ? value.toLocaleString() : '0' },
  ];

  const hourlyColumns = [
    { key: 'hour', title: 'Hour', sortable: true, render: (value) => `${value}:00` },
    { key: 'time_period', title: 'Period', sortable: true },
    { key: 'revenue', title: 'Revenue', sortable: true, render: (value) => `$${typeof value === 'number' ? value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}` },
    { key: 'transactions', title: 'Transactions', sortable: true, render: (value) => typeof value === 'number' ? value.toLocaleString() : '0' },
    { key: 'quantity', title: 'Quantity', sortable: true, render: (value) => typeof value === 'number' ? value.toLocaleString() : '0' },
  ];

  const weekdayColumns = [
    { key: 'weekday', title: 'Day', sortable: true },
    { key: 'revenue', title: 'Revenue', sortable: true, render: (value) => `$${typeof value === 'number' ? value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}` },
    { key: 'transactions', title: 'Transactions', sortable: true, render: (value) => typeof value === 'number' ? value.toLocaleString() : '0' },
    { key: 'customers', title: 'Customers', sortable: true, render: (value) => typeof value === 'number' ? value.toLocaleString() : '0' },
    { key: 'quantity', title: 'Quantity', sortable: true, render: (value) => typeof value === 'number' ? value.toLocaleString() : '0' },
  ];

  const insights = calculateSeasonalInsights();

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Seasonal Analysis
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Analyze purchasing patterns by time and product seasonality
        </p>
      </div>

      {/* Custom Filter Panel for Seasonal Analysis */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center">
            <Filter className="h-5 w-5 text-blue-600 mr-2" />
            <h3 className="font-semibold text-gray-900 dark:text-white">Seasonal Analysis Filters</h3>
          </div>
          <button
            onClick={handleResetFilters}
            className="flex items-center px-3 py-1.5 text-sm bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            Reset Filters
          </button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Product Filter - Main for seasonal analysis */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              <div className="flex items-center">
                <Package className="h-4 w-4 mr-1" />
                Product
              </div>
            </label>
            <select
              value={filters.product}
              onChange={(e) => setFilters({...filters, product: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
            >
              <option value="all">All Products</option>
              {availableFilters.products.slice(0, 50).map((product) => (
                <option key={product} value={product}>
                  {product.length > 40 ? product.substring(0, 40) + '...' : product}
                </option>
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

          {/* Month Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Month
            </label>
            <select
              value={filters.month}
              onChange={(e) => setFilters({...filters, month: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
            >
              <option value="all">All Months</option>
              {availableFilters.months.map((month) => (
                <option key={month.value} value={month.value}>{month.name}</option>
              ))}
            </select>
          </div>
        </div>
        
        {/* Product-specific seasonal insights */}
        {filters.product !== 'all' && (
          <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <div className="flex items-center mb-2">
              <Package className="h-5 w-5 text-blue-600 dark:text-blue-400 mr-2" />
              <h4 className="font-medium text-gray-900 dark:text-white">
                Analyzing seasonal patterns for: <span className="font-bold">{filters.product}</span>
              </h4>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Viewing how this product performs across different months, hours, and weekdays.
            </p>
          </div>
        )}
      </div>

      {/* Seasonal Insights */}
      {!loading && seasonalData?.monthly_data?.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="card">
            <div className="flex items-center">
              <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20">
                <Calendar className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Best Month
                </p>
                <p className="text-lg font-bold text-gray-900 dark:text-white">
                  {insights.best_month}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  ${insights.best_month_revenue.toFixed(2)}
                </p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="flex items-center">
              <div className="p-3 rounded-lg bg-green-50 dark:bg-green-900/20">
                <Clock className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Peak Hour
                </p>
                <p className="text-lg font-bold text-gray-900 dark:text-white">
                  {insights.peak_hour}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  ${insights.peak_hour_revenue.toFixed(2)}
                </p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="flex items-center">
              <div className="p-3 rounded-lg bg-purple-50 dark:bg-purple-900/20">
                <Globe className="h-6 w-6 text-purple-600 dark:text-purple-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Best Weekday
                </p>
                <p className="text-lg font-bold text-gray-900 dark:text-white">
                  {insights.top_weekday}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  ${insights.top_weekday_revenue.toFixed(2)}
                </p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="flex items-center">
              <div className="p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20">
                {insights.monthly_trend >= 0 ? (
                  <TrendingUp className="h-6 w-6 text-yellow-600 dark:text-yellow-400" />
                ) : (
                  <TrendingDown className="h-6 w-6 text-yellow-600 dark:text-yellow-400" />
                )}
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Monthly Trend
                </p>
                <p className={`text-lg font-bold ${insights.monthly_trend >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {insights.monthly_trend >= 0 ? '+' : ''}{insights.monthly_trend.toFixed(1)}%
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Year-over-year
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Top Products Section */}
      {!loading && seasonalData?.top_products && seasonalData.top_products.length > 0 && (
        <div className="card">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {filters.product !== 'all' ? 'Related Products' : 'Top Products'}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {filters.product !== 'all' 
                ? `Products frequently purchased with "${filters.product}"`
                : 'Most popular products in the selected time period'}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {seasonalData.top_products.slice(0, 5).map((product, index) => (
              <span 
                key={index} 
                className="inline-block bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 text-sm px-3 py-1.5 rounded-lg"
              >
                {product.length > 40 ? product.substring(0, 40) + '...' : product}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Monthly Analysis */}
      <div className="card">
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Monthly Performance
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {filters.product !== 'all' 
              ? `Revenue and transaction patterns for "${filters.product}" by month`
              : 'Revenue and transaction patterns by month'}
            {seasonalData?.metadata?.total_revenue && ` • Total: $${seasonalData.metadata.total_revenue.toFixed(2)}`}
          </p>
        </div>
        {loading ? (
          <LoadingSpinner />
        ) : seasonalData?.monthly_data?.length > 0 ? (
          <DataTable
            columns={monthColumns}
            data={seasonalData.monthly_data}
            itemsPerPage={12}
          />
        ) : (
          <div className="text-center py-12">
            <div className="text-gray-400 dark:text-gray-500 mb-4">
              <Calendar className="h-12 w-12 mx-auto" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No monthly data available
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              {filters.product !== 'all' 
                ? `No data found for "${filters.product}" with the selected filters.`
                : 'No data found with the selected filters.'}
            </p>
            <button
              onClick={handleResetFilters}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Reset Filters
            </button>
          </div>
        )}
      </div>

      {/* Hourly Analysis */}
      <div className="card">
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Hourly Shopping Patterns
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {filters.product !== 'all'
              ? `Revenue distribution for "${filters.product}" throughout the day`
              : 'Revenue distribution throughout the day'}
          </p>
        </div>
        {loading ? (
          <LoadingSpinner />
        ) : seasonalData?.hourly_data?.length > 0 ? (
          <DataTable
            columns={hourlyColumns}
            data={seasonalData.hourly_data}
            itemsPerPage={6}
          />
        ) : (
          <div className="text-center py-12">
            <div className="text-gray-400 dark:text-gray-500 mb-4">
              <Clock className="h-12 w-12 mx-auto" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No hourly data available
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              Try adjusting your filters to see hourly patterns
            </p>
          </div>
        )}
      </div>

      {/* Weekday Analysis */}
      <div className="card">
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Weekday Performance
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {filters.product !== 'all'
              ? `Revenue distribution for "${filters.product}" by day of week`
              : 'Revenue distribution by day of week'}
          </p>
        </div>
        {loading ? (
          <LoadingSpinner />
        ) : seasonalData?.weekday_data?.length > 0 ? (
          <DataTable
            columns={weekdayColumns}
            data={seasonalData.weekday_data}
            itemsPerPage={7}
          />
        ) : (
          <div className="text-center py-12">
            <div className="text-gray-400 dark:text-gray-500 mb-4">
              <Globe className="h-12 w-12 mx-auto" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No weekday data available
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              Try adjusting your filters to see weekday patterns
            </p>
          </div>
        )}
      </div>
    </div>
  );
};