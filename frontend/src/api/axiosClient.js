import axios from 'axios';

// '/api' works in dev (Vite proxy) and when the frontend and API share a domain.
// For a separately hosted API set VITE_API_BASE_URL, e.g. https://api.example.com/api
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
const baseURL = API_BASE_URL;

const axiosClient = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
});

const ACCESS_KEY = 'mba_access_token';
const REFRESH_KEY = 'mba_refresh_token';

export const getAccessToken = () => localStorage.getItem(ACCESS_KEY);
export const getRefreshToken = () => localStorage.getItem(REFRESH_KEY);

export const setTokens = ({ access_token, refresh_token }) => {
  if (access_token) localStorage.setItem(ACCESS_KEY, access_token);
  if (refresh_token) localStorage.setItem(REFRESH_KEY, refresh_token);
};

export const clearTokens = () => {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
};

axiosClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Exchange the refresh token for a new access token. Used by fetch-based
// calls (the streaming chat) that do not go through the axios interceptors.
export const refreshAccessToken = async () => {
  const refresh = getRefreshToken();
  if (!refresh) throw new Error('No refresh token');
  const res = await axios.post(`${baseURL}/auth/refresh`, {}, { headers: { Authorization: `Bearer ${refresh}` } });
  setTokens({ access_token: res.data.access_token });
  return res.data.access_token;
};

let isRefreshing = false;
let pendingRequests = [];

const flushQueue = (token) => {
  pendingRequests.forEach((cb) => cb(token));
  pendingRequests = [];
};

axiosClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (!error.response || originalRequest._retry) {
      return Promise.reject(error);
    }
    if (error.response.status === 401 && getRefreshToken()) {
      if (isRefreshing) {
        return new Promise((resolve) => {
          pendingRequests.push((newToken) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            resolve(axiosClient(originalRequest));
          });
        });
      }
      originalRequest._retry = true;
      isRefreshing = true;
      try {
        const refresh = getRefreshToken();
        const res = await axios.post(
          `${baseURL}/auth/refresh`,
          {},
          { headers: { Authorization: `Bearer ${refresh}` } }
        );
        const newAccess = res.data.access_token;
        setTokens({ access_token: newAccess });
        flushQueue(newAccess);
        originalRequest.headers.Authorization = `Bearer ${newAccess}`;
        return axiosClient(originalRequest);
      } catch (refreshErr) {
        clearTokens();
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

export default axiosClient;
