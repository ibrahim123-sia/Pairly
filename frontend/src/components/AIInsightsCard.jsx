import { useCallback, useEffect, useState } from 'react';
import { Sparkles, RefreshCw, Package, ShoppingBag, DollarSign, Users, CalendarDays, ShieldCheck, ArrowRight } from 'lucide-react';
import toast from 'react-hot-toast';
import { getInsights, regenerateInsights } from '../api/aiApi';

const KIND = {
  bundle: { icon: Package, tint: 'text-blue-600 bg-blue-50 dark:bg-blue-900/30 dark:text-blue-300' },
  cross_sell: { icon: ShoppingBag, tint: 'text-teal-600 bg-teal-50 dark:bg-teal-900/30 dark:text-teal-300' },
  revenue: { icon: DollarSign, tint: 'text-amber-600 bg-amber-50 dark:bg-amber-900/30 dark:text-amber-300' },
  customers: { icon: Users, tint: 'text-rose-600 bg-rose-50 dark:bg-rose-900/30 dark:text-rose-300' },
  seasonal: { icon: CalendarDays, tint: 'text-violet-600 bg-violet-50 dark:bg-violet-900/30 dark:text-violet-300' },
};

const FALLBACK_NOTE = {
  not_configured: 'AI is not set up on this server, so this is an automatic summary.',
  disabled_by_env: 'AI is not set up on this server, so this is an automatic summary.',
  platform_disabled: 'AI is turned off by the administrator, so this is an automatic summary.',
  admin_disabled: 'AI is turned off for this store by the administrator, so this is an automatic summary.',
  store_disabled: 'AI is turned off in Settings, so this is an automatic summary.',
  limit_reached: "Today's AI requests are used up, so this is an automatic summary.",
  check_failed: 'The AI text included numbers that are not in your data, so Pairly showed an automatic summary instead.',
  llm_error: 'The AI service did not respond, so this is an automatic summary.',
};

const timeAgo = (iso) => {
  if (!iso) return '';
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  return hours < 24 ? `${hours} h ago` : new Date(iso).toLocaleDateString();
};

export const AIInsightsCard = ({ params }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setData(await getInsights(params));
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not load insights');
    } finally {
      setLoading(false);
    }
  }, [params]);

  useEffect(() => {
    load();
  }, [load]);

  const regenerate = async () => {
    setRegenerating(true);
    try {
      const next = await regenerateInsights(params);
      setData(next);
      if (next.source !== 'ai') toast(FALLBACK_NOTE[next.reason] || 'Showing an automatic summary.');
    } catch (err) {
      toast.error(err.response?.data?.detail?.message || 'Could not regenerate insights');
    } finally {
      setRegenerating(false);
    }
  };

  const isAI = data?.source === 'ai';

  return (
    <section className="card border border-primary-100 dark:border-primary-900/40" aria-labelledby="ai-insights-title">
      <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gradient-to-br from-primary-600 to-teal-500 text-white">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <h3 id="ai-insights-title" className="text-lg font-semibold text-gray-900 dark:text-white">AI Insights</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {isAI ? 'Written by AI from your analytics' : 'Automatic summary of your analytics'}
              {data?.generated_at && ` · ${timeAgo(data.generated_at)}`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {data?.verified && (
            <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300"
              title="Every number in these insights was checked against your data">
              <ShieldCheck className="h-3.5 w-3.5" /> Numbers checked
            </span>
          )}
          <button onClick={regenerate} disabled={regenerating || loading}
            className="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50">
            <RefreshCw className={`h-4 w-4 ${regenerating ? 'animate-spin' : ''}`} />
            {regenerating ? 'Regenerating…' : 'Regenerate'}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="space-y-3" aria-busy="true">
          {[0, 1, 2].map((i) => <div key={i} className="h-16 rounded-lg bg-gray-100 dark:bg-gray-700/50 animate-pulse" />)}
        </div>
      ) : error ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">{typeof error === 'string' ? error : 'Could not load insights'}</p>
      ) : (
        <>
          <ul className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {data.insights.map((it, i) => {
              const k = KIND[it.kind] || KIND.revenue;
              const Icon = k.icon;
              return (
                <li key={i} className="flex gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-900/40">
                  <div className={`shrink-0 h-9 w-9 rounded-lg flex items-center justify-center ${k.tint}`}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-medium text-gray-900 dark:text-white">{it.title}</p>
                    <p className="text-sm text-gray-600 dark:text-gray-300 mt-0.5">{it.text}</p>
                    {it.action && (
                      <p className="text-sm mt-1.5 text-primary-700 dark:text-primary-300 flex gap-1">
                        <ArrowRight className="h-4 w-4 shrink-0 mt-0.5" />
                        <span>{it.action}</span>
                      </p>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
          {!isAI && FALLBACK_NOTE[data.reason] && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-3">{FALLBACK_NOTE[data.reason]}</p>
          )}
        </>
      )}
    </section>
  );
};
