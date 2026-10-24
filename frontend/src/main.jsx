import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import axios from 'axios'
import './index.css'
import App from './App.jsx'
import { API_BASE_URL, getAccessToken, getRefreshToken, setTokens, clearTokens } from './api/axiosClient'

// Pages use the shared axiosClient; these interceptors only cover the few
// bare-axios calls (file downloads) so they also get a token and refresh.
axios.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let queue = [];

axios.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    if (!error.response || original?._retry) return Promise.reject(error);
    if (error.response.status === 401 && getRefreshToken()) {
      if (isRefreshing) {
        return new Promise((resolve) => {
          queue.push((t) => {
            original.headers.Authorization = `Bearer ${t}`;
            resolve(axios(original));
          });
        });
      }
      original._retry = true;
      isRefreshing = true;
      try {
        const res = await axios.post(`${API_BASE_URL}/auth/refresh`, {}, {
          headers: { Authorization: `Bearer ${getRefreshToken()}` },
        });
        const newAccess = res.data.access_token;
        setTokens({ access_token: newAccess });
        queue.forEach((cb) => cb(newAccess));
        queue = [];
        original.headers.Authorization = `Bearer ${newAccess}`;
        return axios(original);
      } catch (err) {
        clearTokens();
        if (window.location.pathname !== '/login') window.location.href = '/login';
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
