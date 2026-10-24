import client, { API_BASE_URL, getAccessToken, refreshAccessToken } from './axiosClient';

export const getAIStatus = () => client.get('/ai/status').then((r) => r.data);
export const getInsights = (params) => client.get('/ai/insights', { params }).then((r) => r.data);
export const regenerateInsights = (params) =>
  client.post('/ai/insights/regenerate', null, { params }).then((r) => r.data);
export const setStoreAI = (ai_enabled) => client.patch('/ai/settings', { ai_enabled }).then((r) => r.data);

export const getAdminAI = (days = 30) => client.get('/admin/ai', { params: { days } }).then((r) => r.data);
export const setPlatformAI = (ai_enabled) => client.patch('/admin/ai', { ai_enabled }).then((r) => r.data);
export const updateStoreAIAdmin = (storeId, body) =>
  client.patch(`/admin/ai/stores/${storeId}`, body).then((r) => r.data);

const errorMessage = async (res) => {
  try {
    const body = await res.json();
    const d = body?.detail;
    return (typeof d === 'string' ? d : d?.message) || `Request failed (${res.status})`;
  } catch {
    return `Request failed (${res.status})`;
  }
};

/**
 * Ask Pairly. Streams Server-Sent Events from POST /ai/chat and calls
 * onEvent(type, data) for tool_start, tool_end, token, done and error.
 * Uses fetch (axios cannot stream in the browser), so it refreshes the
 * access token itself on a 401.
 */
export async function streamChat(messages, onEvent, signal) {
  const send = (token) =>
    fetch(`${API_BASE_URL}/ai/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ messages }),
      signal,
    });

  let res = await send(getAccessToken());
  if (res.status === 401) {
    res = await send(await refreshAccessToken());
  }
  if (!res.ok) {
    throw new Error(await errorMessage(res));
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let cut;
    while ((cut = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      let type = 'message';
      let data = '';
      for (const line of block.split('\n')) {
        if (line.startsWith('event: ')) type = line.slice(7).trim();
        else if (line.startsWith('data: ')) data += line.slice(6);
      }
      if (data) onEvent(type, JSON.parse(data));
    }
  }
}
