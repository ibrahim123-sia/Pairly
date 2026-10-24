import { useEffect, useState } from 'react';
import { fetchRecommendations, simulateBundle } from '../../api/insightsApi';
import { fetchFilters } from '../../api/analyticsApi';
import { exportCsvUrl } from '../../api/storeApi';
import { getAccessToken } from '../../api/axiosClient';
import axios from 'axios';
import { Sparkles, Download, Lightbulb } from 'lucide-react';
import toast from 'react-hot-toast';

export const Recommendations = () => {
  const [products, setProducts] = useState([]);
  const [selected, setSelected] = useState('');
  const [recs, setRecs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [simResult, setSimResult] = useState(null);
  const [bundleSel, setBundleSel] = useState([]);
  const [discount, setDiscount] = useState(10);
  const [matched, setMatched] = useState(null);

  useEffect(() => {
    fetchFilters().then((r) => {
      const list = r.filters?.products || [];
      setProducts(list);
      if (list.length && !selected) setSelected(list[0]);
    });
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    fetchRecommendations(selected, 15)
      .then((r) => {
        setRecs(r.recommendations || []);
        setMatched(r.matched);
      })
      .catch(() => toast.error('Could not load recommendations'))
      .finally(() => setLoading(false));
  }, [selected]);

  const toggleBundle = (name) => {
    setBundleSel((b) => (b.includes(name) ? b.filter((x) => x !== name) : [...b, name]));
  };

  const runSimulator = async () => {
    const items = [selected, ...bundleSel].filter(Boolean);
    if (items.length < 2) return toast.error('Pick at least 1 recommendation to bundle');
    setSimulating(true);
    try {
      const res = await simulateBundle(items, discount);
      setSimResult(res);
    } catch {
      toast.error('Simulation failed');
    } finally {
      setSimulating(false);
    }
  };

  const downloadAllRecs = async () => {
    try {
      const res = await axios.get(exportCsvUrl('recommendations'), {
        headers: { Authorization: `Bearer ${getAccessToken()}` },
        responseType: 'blob',
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url; a.download = 'recommendations.csv'; a.click();
      URL.revokeObjectURL(url);
      toast.success('Downloaded');
    } catch {
      toast.error('Download failed');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center"><Sparkles className="h-6 w-6 mr-2 text-primary-600" /> Cross-sell Recommendations</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Pick a product to see what customers often buy alongside it. Use this to build product-page recommendations, bundles, and email campaigns.</p>
        </div>
        <button onClick={downloadAllRecs} className="inline-flex items-center bg-primary-600 hover:bg-primary-700 text-white text-sm px-4 py-2 rounded-lg">
          <Download className="h-4 w-4 mr-1" /> Export full recommendation table (CSV)
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 p-5 rounded-xl border border-gray-200 dark:border-gray-700">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Source product</label>
        <select value={selected} onChange={(e) => { setSelected(e.target.value); setBundleSel([]); setSimResult(null); }}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
          {products.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading recommendations...</p>
      ) : matched === false ? (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl p-4 text-yellow-800 dark:text-yellow-300 text-sm">
          No co-purchase history for this product. Try another product or upload more data.
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-900 text-xs uppercase text-gray-500 dark:text-gray-400">
              <tr>
                <th className="px-4 py-3 text-left">Bundle?</th>
                <th className="px-4 py-3 text-left">Recommended product</th>
                <th className="px-4 py-3 text-right">Co-purchase count</th>
                <th className="px-4 py-3 text-right">Co-purchase rate</th>
                <th className="px-4 py-3 text-right">Confidence</th>
                <th className="px-4 py-3 text-right">Lift</th>
                <th className="px-4 py-3 text-right">Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {recs.map((r) => (
                <tr key={r.product} className="text-gray-700 dark:text-gray-300">
                  <td className="px-4 py-3"><input type="checkbox" checked={bundleSel.includes(r.product)} onChange={() => toggleBundle(r.product)} /></td>
                  <td className="px-4 py-3 text-gray-900 dark:text-white">{r.product}</td>
                  <td className="px-4 py-3 text-right">{r.co_purchase_count.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right">{r.co_purchase_rate}%</td>
                  <td className="px-4 py-3 text-right">{r.confidence}</td>
                  <td className="px-4 py-3 text-right"><span className={r.lift >= 2 ? 'text-green-600 font-medium' : ''}>{r.lift}</span></td>
                  <td className="px-4 py-3 text-right font-medium">{r.score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <h2 className="font-semibold text-gray-900 dark:text-white flex items-center mb-3"><Lightbulb className="h-5 w-5 mr-2 text-yellow-500" /> Bundle simulator</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">Check the boxes above to add items to a bundle, set a discount, and project the revenue impact.</p>
        <div className="flex items-end space-x-3 mb-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Discount %</label>
            <input type="number" min="0" max="80" value={discount} onChange={(e) => setDiscount(Number(e.target.value))} className="w-24 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-white" />
          </div>
          <button onClick={runSimulator} disabled={simulating || bundleSel.length === 0} className="bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg">
            {simulating ? 'Simulating...' : `Simulate bundle (${(selected ? 1 : 0) + bundleSel.length} items)`}
          </button>
        </div>
        {simResult && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
            <div className="p-3 bg-gray-50 dark:bg-gray-900/40 rounded">
              <p className="text-xs text-gray-500 uppercase">Currently bought together</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white">{simResult.current?.co_purchase_baskets?.toLocaleString()}</p>
              <p className="text-xs text-gray-500">({simResult.current?.co_purchase_rate}% of orders)</p>
            </div>
            <div className="p-3 bg-primary-50 dark:bg-primary-900/20 rounded">
              <p className="text-xs text-primary-600 uppercase">Projected bundle orders</p>
              <p className="text-lg font-bold text-primary-700 dark:text-primary-300">+{simResult.projected?.extra_bundle_baskets?.toLocaleString()}</p>
              <p className="text-xs text-gray-500">total: {simResult.projected?.total_bundle_baskets?.toLocaleString()}</p>
            </div>
            <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded">
              <p className="text-xs text-green-600 uppercase">Projected revenue</p>
              <p className="text-lg font-bold text-green-700 dark:text-green-300">${simResult.projected?.projected_bundle_revenue?.toLocaleString()}</p>
              <p className="text-xs text-gray-500">delta: ${simResult.projected?.revenue_delta?.toLocaleString()}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
