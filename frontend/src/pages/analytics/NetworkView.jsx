import { useState, useEffect } from 'react';
import api from '../../api/axiosClient';
import { FilterPanel } from '../../components/FilterPanel';
import { NetworkGraph } from '../../components/NetworkGraph';
import { LoadingSpinner } from '../../components/LoadingSpinner';
import { Network, GitBranch, Target, BarChart3, AlertCircle } from 'lucide-react';

export const NetworkView = () => {
  const [loading, setLoading] = useState(true);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [metadata, setMetadata] = useState(null);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    min_support: 0.02,
    limit: 20,
    country: 'all',
    year: 'all',
    month: 'all',
    hour: 'all',
    product: 'all',
    weekday: 'all'
  });

  useEffect(() => {
    fetchNetworkData();
  }, [filters]);

  const fetchNetworkData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/analytics/frequent_itemsets', {
        params: filters,
      });

      if (response.data.success && response.data.network) {
        const { nodes, links } = response.data.network;
        
        setGraphData({
          nodes: nodes,
          links: links,
        });
        setMetadata(response.data.metadata || null);
        
        if (nodes.length === 0) {
          setError({
            message: 'No network data available',
            details: 'Try lowering the minimum support threshold or adjusting filters',
            suggestions: [
              'Lower minimum support to 1%',
              'Remove product filter if applied',
              'Try different country or time filters'
            ]
          });
        }
      } else {
        setError({
          message: 'Failed to load network data',
          details: response.data.error || 'Unknown error',
          suggestions: ['Check backend connection', 'Try refreshing the page']
        });
        setGraphData({ nodes: [], links: [] });
      }
    } catch (error) {
      console.error('Error fetching network data:', error);
      setError({
        message: 'Network error',
        details: 'Failed to connect to server',
        suggestions: ['Make sure backend is running', 'Check network connection']
      });
      setGraphData({ nodes: [], links: [] });
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = () => {
    fetchNetworkData();
  };

  const handleResetFilters = () => {
    setFilters({
      min_support: 0.02,
      limit: 20,
      country: 'all',
      year: 'all',
      month: 'all',
      hour: 'all',
      product: 'all',
      weekday: 'all'
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Network View
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Visualize product relationships as an interactive network graph
        </p>
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-3">
        <button
          onClick={() => setFilters({...filters, min_support: 0.01})}
          className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
        >
          <Target className="h-4 w-4 mr-2" />
          Lower Support (1%)
        </button>
        <button
          onClick={handleResetFilters}
          className="flex items-center px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
        >
          <BarChart3 className="h-4 w-4 mr-2" />
          Reset Filters
        </button>
      </div>

      <FilterPanel onFilterChange={setFilters} loading={loading} />

      {/* Network Stats */}
      {!loading && graphData.nodes.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="card">
            <div className="flex items-center">
              <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20">
                <Network className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Total Products
                </p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {graphData.nodes.length}
                </p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="flex items-center">
              <div className="p-3 rounded-lg bg-green-50 dark:bg-green-900/20">
                <GitBranch className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Total Connections
                </p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {graphData.links.length}
                </p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="flex items-center">
              <div className="p-3 rounded-lg bg-purple-50 dark:bg-purple-900/20">
                <Target className="h-6 w-6 text-purple-600 dark:text-purple-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Min. Support
                </p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {(filters.min_support * 100).toFixed(1)}%
                </p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="flex items-center">
              <div className="p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20">
                <BarChart3 className="h-6 w-6 text-yellow-600 dark:text-yellow-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Avg. Node Degree
                </p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {metadata?.avg_node_degree ? metadata.avg_node_degree.toFixed(2) : '0.00'}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Network Graph Visualization */}
      <div className="card p-0 overflow-hidden">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Product Relationship Network
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Nodes represent products (size = revenue), edges represent co-purchase frequency
              </p>
            </div>
            <button
              onClick={handleRetry}
              className="flex items-center px-3 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
              disabled={loading}
            >
              <BarChart3 className="h-4 w-4 mr-2" />
              Refresh
            </button>
          </div>
        </div>
        
        {error ? (
          <div className="text-center py-12">
            <div className="text-red-400 dark:text-red-500 mb-4">
              <AlertCircle className="h-16 w-16 mx-auto" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              {error.message}
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              {error.details}
            </p>
            {error.suggestions && (
              <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4 mb-6 max-w-md mx-auto">
                <h4 className="font-medium text-yellow-800 dark:text-yellow-300 mb-2">
                  Try these solutions:
                </h4>
                <ul className="text-sm text-yellow-700 dark:text-yellow-400 text-left space-y-1">
                  {error.suggestions.map((suggestion, idx) => (
                    <li key={idx} className="flex items-start">
                      <span className="mr-2">•</span>
                      <span>{suggestion}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="flex justify-center space-x-4">
              <button 
                onClick={() => setFilters({...filters, min_support: 0.01})}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                Try Lower Support (1%)
              </button>
              <button 
                onClick={handleRetry}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center h-[500px]">
            <LoadingSpinner text="Loading network graph..." />
          </div>
        ) : graphData.nodes.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-400 dark:text-gray-500 mb-4">
              <Network className="h-12 w-12 mx-auto" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No network data available
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              This usually happens when:
            </p>
            <ul className="text-sm text-gray-600 dark:text-gray-400 text-left max-w-md mx-auto mb-6 space-y-2">
              <li className="flex items-start">
                <AlertCircle className="h-4 w-4 mr-2 mt-0.5 text-yellow-500" />
                <span>Support threshold is too high (try 1% instead of 2%)</span>
              </li>
              <li className="flex items-start">
                <AlertCircle className="h-4 w-4 mr-2 mt-0.5 text-yellow-500" />
                <span>Product filter is too restrictive</span>
              </li>
              <li className="flex items-start">
                <AlertCircle className="h-4 w-4 mr-2 mt-0.5 text-yellow-500" />
                <span>Dataset has few product associations</span>
              </li>
            </ul>
            <div className="flex justify-center space-x-4">
              <button 
                onClick={() => setFilters({...filters, min_support: 0.01})}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                Try Lower Support (1%)
              </button>
              <button 
                onClick={handleResetFilters}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
              >
                Remove All Filters
              </button>
            </div>
          </div>
        ) : (
          <NetworkGraph
            data={graphData}
            loading={loading}
            height={600}
          />
        )}
        
        {metadata && (
          <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Network Statistics: {metadata.nodes_count} nodes • {metadata.links_count} links • 
              Avg degree: {metadata.avg_node_degree?.toFixed(2) || '0.00'} • 
              Max degree: {metadata.max_node_degree || '0'}
            </div>
          </div>
        )}
      </div>

      {/* Network Legend */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h4 className="font-semibold text-gray-900 dark:text-white mb-4">
            How to Read the Network
          </h4>
          <div className="space-y-3">
            <div className="flex items-center">
              <div className="w-4 h-4 rounded-full bg-blue-500 mr-3"></div>
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">Node Size</p>
                <p className="text-xs text-gray-600 dark:text-gray-400">Larger nodes = higher revenue products</p>
              </div>
            </div>
            <div className="flex items-center">
              <div className="w-8 h-1 bg-gray-400 mr-3"></div>
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">Edge Thickness</p>
                <p className="text-xs text-gray-600 dark:text-gray-400">Thicker edges = stronger co-purchase relationship</p>
              </div>
            </div>
            <div className="flex items-center">
              <div className="w-8 h-1 bg-green-500 mr-3"></div>
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">Edge Color</p>
                <p className="text-xs text-gray-600 dark:text-gray-400">Green edges = high lift (strong positive association)</p>
              </div>
            </div>
          </div>
        </div>
        <div className="card">
          <h4 className="font-semibold text-gray-900 dark:text-white mb-4">
            Network Insights
          </h4>
          <ul className="space-y-2">
            <li className="flex items-start">
              <div className="flex-shrink-0 mt-1">
                <div className="w-2 h-2 rounded-full bg-blue-500"></div>
              </div>
              <p className="ml-3 text-sm text-gray-700 dark:text-gray-300">
                Densely connected clusters indicate frequently co-purchased product groups
              </p>
            </li>
            <li className="flex items-start">
              <div className="flex-shrink-0 mt-1">
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
              </div>
              <p className="ml-3 text-sm text-gray-700 dark:text-gray-300">
                Central nodes are key products that connect multiple product groups
              </p>
            </li>
            <li className="flex items-start">
              <div className="flex-shrink-0 mt-1">
                <div className="w-2 h-2 rounded-full bg-purple-500"></div>
              </div>
              <p className="ml-3 text-sm text-gray-700 dark:text-gray-300">
                Isolated nodes may represent niche products or require cross-selling
              </p>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};