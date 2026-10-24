import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { MessageSquareText, Send, Square, Wrench, ShieldCheck, AlertTriangle, Loader2, Sparkles } from 'lucide-react';
import { getAIStatus, streamChat } from '../../api/aiApi';
import { MiniMarkdown } from '../../components/MiniMarkdown';

const SUGGESTIONS = [
  'What should I bundle with tea cups?',
  'Which customers are about to leave?',
  'What are my best-selling products?',
  'When is my busiest month?',
  'Which countries bring the most revenue?',
];

const TOOL_LABELS = {
  get_association_rules: 'Association rules',
  get_bundles: 'Bundles',
  get_recommendations_for_product: 'Product recommendations',
  get_revenue_breakdown: 'Revenue breakdown',
  get_seasonal_trend: 'Seasonal trend',
  get_rfm_segments: 'RFM segments',
  get_top_products: 'Top products',
};

const toolLabel = (name) => TOOL_LABELS[name] || name;

const Answer = ({ msg }) => (
  <div className="max-w-3xl">
    <div className="rounded-2xl rounded-tl-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-3 text-gray-800 dark:text-gray-100 text-[15px] leading-relaxed">
      {msg.running.length > 0 && !msg.content && (
        <div className="flex flex-wrap gap-2 text-sm text-gray-500 dark:text-gray-400">
          {msg.running.map((t) => (
            <span key={t} className="inline-flex items-center gap-1.5">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Checking {toolLabel(t).toLowerCase()}…
            </span>
          ))}
        </div>
      )}
      {msg.content ? <MiniMarkdown text={msg.content} /> : msg.pending && msg.running.length === 0 && (
        <span className="inline-flex items-center gap-2 text-sm text-gray-500"><Loader2 className="h-4 w-4 animate-spin" /> Thinking…</span>
      )}
      {msg.error && <p className="text-sm text-red-600 dark:text-red-400 mt-2">{msg.error}</p>}
    </div>
    {msg.done && (
      <div className="flex flex-wrap items-center gap-2 mt-2 text-xs">
        {msg.tools.length > 0 ? (
          <span className="inline-flex items-center gap-1 text-gray-500 dark:text-gray-400">
            <Wrench className="h-3.5 w-3.5" /> Tools used:
            {[...new Set(msg.tools.map((t) => t.name))].map((n) => (
              <span key={n} className="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">{toolLabel(n)}</span>
            ))}
          </span>
        ) : (
          <span className="text-gray-500 dark:text-gray-400">No tools used</span>
        )}
        {msg.verified === true && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300">
            <ShieldCheck className="h-3.5 w-3.5" /> Numbers match your data
          </span>
        )}
        {msg.verified === false && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
            title={`Not found in the data: ${msg.unverified.join(', ')}`}>
            <AlertTriangle className="h-3.5 w-3.5" /> Some numbers could not be checked: {msg.unverified.join(', ')}
          </span>
        )}
      </div>
    )}
  </div>
);

export const AskPairly = () => {
  const [status, setStatus] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const abortRef = useRef(null);
  const endRef = useRef(null);

  useEffect(() => {
    getAIStatus().then(setStatus).catch(() => setStatus({ available: false, message: 'Could not reach the AI service.' }));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  const patchLast = (fn) => setMessages((prev) => {
    const next = [...prev];
    next[next.length - 1] = fn(next[next.length - 1]);
    return next;
  });

  const ask = async (question) => {
    const q = question.trim();
    if (!q || busy) return;
    const history = [...messages, { role: 'user', content: q }]
      .filter((m) => m.content)
      .map(({ role, content }) => ({ role, content }));
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: q },
      { role: 'assistant', content: '', pending: true, running: [], tools: [], done: false },
    ]);
    setInput('');
    setBusy(true);
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamChat(history, (type, data) => {
        if (type === 'tool_start') patchLast((m) => ({ ...m, running: [...m.running, data.name] }));
        else if (type === 'tool_end') patchLast((m) => ({ ...m, running: m.running.filter((n) => n !== data.name) }));
        else if (type === 'token') patchLast((m) => ({ ...m, content: m.content + data.text }));
        else if (type === 'error') patchLast((m) => ({ ...m, error: data.message }));
        else if (type === 'done') {
          patchLast((m) => ({
            ...m, pending: false, running: [], done: true, tools: data.tools_used || [],
            verified: data.verified, unverified: data.unverified_numbers || [],
          }));
          setStatus((s) => (s ? { ...s, used_today: (s.used_today || 0) + 1 } : s));
        }
      }, controller.signal);
    } catch (err) {
      if (err.name === 'AbortError') patchLast((m) => ({ ...m, pending: false, running: [], error: 'Stopped.' }));
      else patchLast((m) => ({ ...m, pending: false, running: [], error: err.message }));
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      ask(input);
    }
  };

  const unavailable = status && !status.available;

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] min-h-[520px]">
      <div className="flex flex-wrap items-end justify-between gap-2 mb-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <MessageSquareText className="h-6 w-6 text-primary-600" /> Ask Pairly
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mt-1 text-sm">
            Ask about your sales in plain English. Answers come from your store&apos;s analytics, and Pairly says so when the data can&apos;t answer.
          </p>
        </div>
        {status?.available && (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {status.used_today} of {status.daily_limit} questions used today
          </p>
        )}
      </div>

      {unavailable && (
        <div className="mb-4 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 px-4 py-3 text-sm text-amber-800 dark:text-amber-200">
          {status.message || 'AI is not available right now.'}{' '}
          {status.reason === 'store_disabled' && <Link to="/store/settings" className="underline">Turn it on in Settings.</Link>}
        </div>
      )}

      <div className="flex-1 overflow-y-auto rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/60 p-4 space-y-5">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center px-4">
            <div className="p-3 rounded-2xl bg-gradient-to-br from-primary-600 to-teal-500 text-white mb-3">
              <Sparkles className="h-6 w-6" />
            </div>
            <p className="font-medium text-gray-900 dark:text-white">What would you like to know?</p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">Try one of these:</p>
            <div className="flex flex-wrap justify-center gap-2 max-w-2xl">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => ask(s)} disabled={busy || unavailable}
                  className="text-sm px-3 py-1.5 rounded-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:border-primary-400 disabled:opacity-50">
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m, i) =>
            m.role === 'user' ? (
              <div key={i} className="flex justify-end">
                <div className="max-w-2xl rounded-2xl rounded-tr-sm bg-primary-600 text-white px-4 py-2.5 text-[15px]">{m.content}</div>
              </div>
            ) : (
              <Answer key={i} msg={m} />
            )
          )
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); ask(input); }} className="mt-3 flex gap-2 items-end">
        <label htmlFor="ask-input" className="sr-only">Your question</label>
        <textarea id="ask-input" rows={1} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={onKeyDown}
          placeholder={unavailable ? 'AI is not available' : 'e.g. What should I bundle with coffee mugs?'}
          disabled={unavailable} maxLength={2000}
          className="flex-1 resize-none input-field py-2.5 max-h-40" />
        {busy ? (
          <button type="button" onClick={() => abortRef.current?.abort()} className="btn-secondary inline-flex items-center gap-1.5 py-2.5">
            <Square className="h-4 w-4" /> Stop
          </button>
        ) : (
          <button type="submit" disabled={!input.trim() || unavailable} className="btn-primary inline-flex items-center gap-1.5 py-2.5">
            <Send className="h-4 w-4" /> Ask
          </button>
        )}
      </form>
    </div>
  );
};
