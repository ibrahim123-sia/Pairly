import { useState, useEffect } from 'react';
import { Filter, ChevronDown } from 'lucide-react';
import api from '../api/axiosClient';

export const FilterPanel = ({ onFilterChange, loading }) => {
  const [filters, setFilters] = useState({
    country: 'all',
    year: 'all',
    month: 'all',
    hour: 'all',
    product: 'all',
    weekday: 'all',
    min_support: 0.01,
    min_confidence: 0.3,
    min_lift: 1.0,
  });

  const [filterOptions, setFilterOptions] = useState({
    countries: [],
    years: [],
    months: [],
    hours: [],
    products: [],
    weekdays: [],
  });

  const [isOpen, setIsOpen] = useState(true);

  useEffect(() => {
    fetchFilterOptions();
  }, []);

  const fetchFilterOptions = async () => {
    try {
      const response = await api.get('/analytics/filters');
      if (response.data.success) {
        setFilterOptions(response.data.filters);
      }
    } catch (error) {
      console.error('Error fetching filters:', error);
    }
  };

  const handleFilterChange = (key, value) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  const handleReset = () => {
    const resetFilters = {
      country: 'all',
      year: 'all',
      month: 'all',
      hour: 'all',
      product: 'all',
      weekday: 'all',
      min_support: 0.01,
      min_confidence: 0.3,
      min_lift: 1.0,
    };
    setFilters(resetFilters);
    onFilterChange(resetFilters);
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <Filter className="h-5 w-5 text-gray-500 dark:text-gray-400 mr-2" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Data Filters
            </h3>
          </div>
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <ChevronDown
              className={`h-5 w-5 text-gray-500 dark:text-gray-400 transition-transform ${
                isOpen ? 'rotate-180' : ''
              }`}
            />
          </button>
        </div>
      </div>

      <div className={`px-4 py-4 space-y-4 ${isOpen ? 'block' : 'hidden'}`}>
        {/* Algorithm Parameters */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Min Support: {(filters.min_support * 100).toFixed(2)}%
            </label>
            <input
              type="range"
              min="0.001"
              max="0.05"
              step="0.001"
              value={filters.min_support}
              onChange={(e) => handleFilterChange('min_support', parseFloat(e.target.value))}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              disabled={loading}
            />
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
              <span>0.1%</span>
              <span>2.5%</span>
              <span>5%</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Min Confidence: {(filters.min_confidence * 100).toFixed(0)}%
            </label>
            <input
              type="range"
              min="0.1"
              max="1"
              step="0.05"
              value={filters.min_confidence}
              onChange={(e) => handleFilterChange('min_confidence', parseFloat(e.target.value))}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              disabled={loading}
            />
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
              <span>10%</span>
              <span>50%</span>
              <span>100%</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Min Lift: {filters.min_lift.toFixed(2)}
            </label>
            <input
              type="range"
              min="0.5"
              max="3"
              step="0.1"
              value={filters.min_lift}
              onChange={(e) => handleFilterChange('min_lift', parseFloat(e.target.value))}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              disabled={loading}
            />
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
              <span>0.5</span>
              <span>1.5</span>
              <span>3.0</span>
            </div>
          </div>
        </div>

        {/* Country, Year, Month, Hour, Weekday, Product Filters */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Country
            </label>
            <select
              value={filters.country}
              onChange={(e) => handleFilterChange('country', e.target.value)}
              className="input-field"
              disabled={loading}
            >
              <option value="all">All Countries</option>
              {filterOptions.countries?.map((country) => (
                <option key={country} value={country}>
                  {country}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Year
            </label>
            <select
              value={filters.year}
              onChange={(e) => handleFilterChange('year', e.target.value)}
              className="input-field"
              disabled={loading}
            >
              <option value="all">All Years</option>
              {filterOptions.years?.map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Month
            </label>
            <select
              value={filters.month}
              onChange={(e) => handleFilterChange('month', e.target.value)}
              className="input-field"
              disabled={loading}
            >
              <option value="all">All Months</option>
              {filterOptions.months?.map((month) => (
                <option key={month.value} value={month.value}>
                  {month.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Hour
            </label>
            <select
              value={filters.hour}
              onChange={(e) => handleFilterChange('hour', e.target.value)}
              className="input-field"
              disabled={loading}
            >
              <option value="all">All Hours</option>
              {filterOptions.hours?.map((hour) => (
                <option key={hour.value} value={hour.value}>
                  {hour.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Weekday
            </label>
            <select
              value={filters.weekday}
              onChange={(e) => handleFilterChange('weekday', e.target.value)}
              className="input-field"
              disabled={loading}
            >
              <option value="all">All Weekdays</option>
              {filterOptions.weekdays?.map((weekday) => (
                <option key={weekday} value={weekday}>
                  {weekday}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Product Filter
            </label>
            <select
              value={filters.product}
              onChange={(e) => handleFilterChange('product', e.target.value)}
              className="input-field"
              disabled={loading}
            >
              <option value="all">All Products</option>
              {filterOptions.products?.map((product) => (
                <option key={product} value={product}>
                  {product.length > 30 ? product.substring(0, 30) + '...' : product}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Filter Statistics */}
        {filterOptions.statistics && (
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
              <div>
                <p className="text-gray-500 dark:text-gray-400">Countries</p>
                <p className="font-medium text-gray-900 dark:text-white">{filterOptions.statistics.total_countries}</p>
              </div>
              <div>
                <p className="text-gray-500 dark:text-gray-400">Years</p>
                <p className="font-medium text-gray-900 dark:text-white">{filterOptions.statistics.total_years}</p>
              </div>
              <div>
                <p className="text-gray-500 dark:text-gray-400">Products</p>
                <p className="font-medium text-gray-900 dark:text-white">{filterOptions.statistics.total_products}</p>
              </div>
              <div>
                <p className="text-gray-500 dark:text-gray-400">Data Range</p>
                <p className="font-medium text-gray-900 dark:text-white">
                  {filterOptions.statistics.data_range?.min_year || 'N/A'} - {filterOptions.statistics.data_range?.max_year || 'N/A'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={fetchFilterOptions}
            className="btn-secondary px-4 py-2"
            disabled={loading}
          >
            Refresh Options
          </button>
          <button
            onClick={handleReset}
            className="btn-secondary px-4 py-2"
            disabled={loading}
          >
            Reset Filters
          </button>
          <button
            onClick={() => onFilterChange(filters)}
            className="btn-primary px-4 py-2"
            disabled={loading}
          >
            {loading ? 'Applying...' : 'Apply Filters'}
          </button>
        </div>
      </div>
    </div>
  );
};