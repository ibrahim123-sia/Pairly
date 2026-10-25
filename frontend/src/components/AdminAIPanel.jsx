import { useEffect, useState } from 'react';
import { Sparkles, Cpu, Activity, Hash } from 'lucide-react';
import toast from 'react-hot-toast';
import { getAdminAI, setPlatformAI, updateStoreAIAdmin } from '../api/aiApi';

const fmt = (n) => (n ?? 0).toLocaleString();

const Switch = ({ on, onClick, disabled, label }) => (
  <button type="button" role="switch" aria-checked={on} aria-label={label} onClick={onClick} disabled={disabled}
    className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors disabled:opacity-50 ${on ? 'bg-primary-600' : 'bg-gray-300 dark:bg-gray-600'}`}>
    <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${on ? 'translate-x-4' : 'translate-x-0.5'}`} />
  </button>
);

const LimitInput = ({ row, onSave }) => {
  const [value, setValue] = useState(String(row.daily_limit));
  const save = () => {
    const n = parseInt(value, 10);
    if (Number.isNaN(n) || n < 0) return setValue(String(row.daily_limit));
    if (n !== row.daily_limit) onSave(n);
  };
  return (
    <input type="number" min="0" value={value} onChange={(e) => setValue(e.target.value)} onBlur={save}
      onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()} aria-label={`Daily AI limit for ${row.store_name}`}
      className="w-20 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-white" />
  );
};

export const AdminAIPanel = () => {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getAdminAI().then(setData).catch(() => toast.error('Could not load AI usage'));
  }, []);

  const run = async (fn, okMsg) => {
    setBusy(true);
    try {
      setData(await fn());
      if (okMsg) toast.success(okMsg);
    } catch {
      toast.error('Update failed');
    } finally {
      setBusy(false);
    }
  };

  if (!data) return <div className="h-48 rounded-xl bg-gray-100 dark:bg-gray-800 animate-pulse" />;

  const tiles = [
    { icon: Activity, label: 'AI requests (30 days)', value: fmt(data.totals.requests) },
    { icon: Hash, label: 'Tokens (30 days)', value: fmt(data.totals.tokens) },
    { icon: Sparkles, label: 'Requests today', value: fmt(data.totals.requests_today) },
    { icon: Cpu, label: 'Model', value: data.configured ? data.model : 'Not configured', small: true },
  ];

  return (
    <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 space-y-5"
      aria-labelledby="admin-ai-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="admin-ai-title" className="text-lg font-semibold text-gray-900 dark:text-white">AI usage</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Insights and Ask Pairly requests per store. {data.configured ? `Provider: ${(data.providers || [data.provider]).join(' → then ')}.` : 'Set GROQ_API_KEY or GEMINI_API_KEY on the server to enable AI.'}
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
          AI for all stores
          <Switch on={data.platform_enabled} disabled={busy} label="AI for all stores"
            onClick={() => run(() => setPlatformAI(!data.platform_enabled), data.platform_enabled ? 'AI turned off for all stores' : 'AI turned on')} />
        </label>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {tiles.map(({ icon: Icon, label, value, small }) => (
          <div key={label} className="rounded-lg bg-gray-50 dark:bg-gray-900/50 p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1.5"><Icon className="h-3.5 w-3.5" />{label}</p>
            <p className={`${small ? 'text-sm mt-1' : 'text-xl'} font-semibold text-gray-900 dark:text-white truncate`} title={String(value)}>{value}</p>
          </div>
        ))}
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
              <th className="py-2 pr-4">Store</th>
              <th className="py-2 pr-4 text-right">Today</th>
              <th className="py-2 pr-4 text-right">30 days</th>
              <th className="py-2 pr-4 text-right">Tokens</th>
              <th className="py-2 pr-4 text-right">Fallbacks</th>
              <th className="py-2 pr-4">Daily limit</th>
              <th className="py-2 pr-4">Manager switch</th>
              <th className="py-2">Allowed</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700/60">
            {data.stores.map((s) => (
              <tr key={s.store_id} className="text-gray-800 dark:text-gray-200">
                <td className="py-2 pr-4 font-medium">{s.store_name}{!s.store_active && <span className="ml-2 text-xs text-gray-400">(disabled)</span>}</td>
                <td className="py-2 pr-4 text-right tabular-nums">{fmt(s.requests_today)}</td>
                <td className="py-2 pr-4 text-right tabular-nums">{fmt(s.requests)}</td>
                <td className="py-2 pr-4 text-right tabular-nums">{fmt(s.tokens)}</td>
                <td className="py-2 pr-4 text-right tabular-nums">{fmt(s.fallbacks)}</td>
                <td className="py-2 pr-4">
                  <LimitInput key={s.daily_limit} row={s}
                    onSave={(n) => run(() => updateStoreAIAdmin(s.store_id, { daily_limit: n }), 'Limit saved')} />
                </td>
                <td className="py-2 pr-4 text-gray-500 dark:text-gray-400">{s.store_ai_enabled ? 'On' : 'Off'}</td>
                <td className="py-2">
                  <Switch on={s.admin_ai_enabled} disabled={busy} label={`Allow AI for ${s.store_name}`}
                    onClick={() => run(() => updateStoreAIAdmin(s.store_id, { admin_ai_enabled: !s.admin_ai_enabled }))} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};
