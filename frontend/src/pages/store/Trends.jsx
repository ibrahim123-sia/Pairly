import { useEffect, useState } from 'react';
import { fetchPeriodComparison } from '../../api/insightsApi';
import { TrendingUp, TrendingDown, Minus, BarChart3 } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import toast from 'react-hot-toast';

const Kpi = ({ label, value, delta, format = (v) => v }) => {
  const Icon = delta == null ? Minus : delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus;
  const color = delta == null ? 'text-gray-500' : delta > 0 ? 'text-green-600' : delta < 0 ? 'text-red-600' : 'text-gray-500';
  return (
    <div className="bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700">
      <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{format(value)}</p>
      {delta != null && (
        <p className={`text-xs mt-1 inline-flex items-center ${color}`}>
          <Icon className="h-3 w-3 mr-1" /> {delta > 0 ? '+' : ''}{delta}% vs prior
        </p>
      )}
    </div>
  );
};

export const Trends = () => {
  const [period, setPeriod] = useState(30);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const selectPeriod = (d) => {
    if (d === period) return;
    setLoading(true);
    setPeriod(d);
  };

  useEffect(() => {
    fetchPeriodComparison(period)
      .then(setData)
      .catch(() => toast.error('Could not load trends'))
      .finally(() => setLoading(false));
  }, [period]);

  const currency = (v) => `$${(v || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  const number = (v) => (v || 0).toLocaleString();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center"><BarChart3 className="h-6 w-6 mr-2 text-primary-600" /> Trends</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Compare the most recent window of activity against the previous window.</p>
        </div>
        <div className="flex space-x-2">
          {[7, 30, 90, 180].map((d) => (
            <button key={d} onClick={() => selectPeriod(d)} className={`px-3 py-1.5 text-sm rounded-lg ${period === d ? 'bg-primary-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'}`}>
              {d} days
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : data?.error ? (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 rounded-xl p-4 text-sm">{data.error}</div>
      ) : (
        <>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            <strong>Current:</strong> {data?.current_period?.start} → {data?.current_period?.end} &nbsp;|&nbsp;
            <strong>Prior:</strong> {data?.prior_period?.start} → {data?.prior_period?.end}
          </p>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Kpi label="Revenue" value={data?.current_period?.revenue} delta={data?.deltas_pct?.revenue} format={currency} />
            <Kpi label="Transactions" value={data?.current_period?.transactions} delta={data?.deltas_pct?.transactions} format={number} />
            <Kpi label="Customers" value={data?.current_period?.customers} delta={data?.deltas_pct?.customers} format={number} />
            <Kpi label="Units sold" value={data?.current_period?.units} delta={data?.deltas_pct?.units} format={number} />
            <Kpi label="Avg order value" value={data?.current_period?.avg_order_value} delta={data?.deltas_pct?.avg_order_value} format={currency} />
          </div>

          <div className="bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700">
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Daily revenue (current period)</h3>
            {data?.daily_revenue?.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={data.daily_revenue} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563eb" stopOpacity={0.5} />
                      <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v) => currency(v)} />
                  <Area type="monotone" dataKey="revenue" stroke="#2563eb" fill="url(#grad)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-500 text-sm">No daily data in the selected window.</p>
            )}
          </div>
        </>
      )}
    </div>
  );
};
