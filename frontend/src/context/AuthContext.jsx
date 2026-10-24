import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { loginApi, meApi, logoutApi } from '../api/authApi';
import { getAccessToken, setTokens, clearTokens } from '../api/axiosClient';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [store, setStore] = useState(null);
  const [loading, setLoading] = useState(true);

  const hydrate = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const res = await meApi();
      setUser(res.data.user);
      setStore(res.data.store || null);
    } catch {
      clearTokens();
      setUser(null);
      setStore(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const login = async (email, password) => {
    const res = await loginApi(email, password);
    setTokens({ access_token: res.data.access_token, refresh_token: res.data.refresh_token });
    setUser(res.data.user);
    setStore(res.data.store || null);
    return res.data;
  };

  const logout = async () => {
    try { await logoutApi(); } catch { /* sign out locally even if the API call fails */ }
    clearTokens();
    setUser(null);
    setStore(null);
  };

  const refreshMe = useCallback(async () => {
    try {
      const res = await meApi();
      setUser(res.data.user);
      setStore(res.data.store || null);
    } catch { /* keep the current session data */ }
  }, []);

  const value = {
    user,
    store,
    loading,
    isAuthenticated: !!user,
    isSuperAdmin: user?.role === 'super_admin',
    isStoreManager: user?.role === 'store_manager',
    login,
    logout,
    refreshMe,
    setStore,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// eslint-disable-next-line react-refresh/only-export-components -- the hook belongs next to its provider
export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
