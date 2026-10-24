import { Sun, Moon, Menu, X, LogOut } from 'lucide-react';
import { Logo } from './Logo';
import { APP_NAME } from '../brand';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';

const initials = (name) => {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] || '') + (parts[1]?.[0] || '')).toUpperCase() || '?';
};

export const Header = ({ toggleSidebar, isSidebarOpen, title, subtitle }) => {
  const { isDark, toggleTheme } = useTheme();
  const { user, store, logout } = useAuth();
  const navigate = useNavigate();

  const onLogout = async () => {
    await logout();
    toast.success('Signed out');
    navigate('/login');
  };

  const displayName = user?.full_name || user?.email || 'User';
  const roleLabel = user?.role === 'super_admin' ? 'Super Admin' : (store?.name || 'Store Manager');

  return (
    <header className="sticky top-0 z-40 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <button
              onClick={toggleSidebar}
              className="p-2 rounded-md text-gray-500 hover:text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-300 dark:hover:bg-gray-800 lg:hidden"
            >
              {isSidebarOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
            <div className="flex items-center ml-2 lg:ml-0">
              <Logo className="h-9 w-9" />
              <div className="ml-3">
                <h1 className="text-xl font-bold text-gray-900 dark:text-white">{title || APP_NAME}</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">{subtitle || 'Market basket analytics'}</p>
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
              aria-label="Toggle theme"
            >
              {isDark ? <Sun size={20} /> : <Moon size={20} />}
            </button>
            <div className="hidden sm:flex items-center space-x-2">
              <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
                <span className="text-sm font-medium text-primary-600 dark:text-primary-300">{initials(displayName)}</span>
              </div>
              <div className="text-sm">
                <p className="font-medium text-gray-900 dark:text-white">{displayName}</p>
                <p className="text-gray-500 dark:text-gray-400 text-xs">{roleLabel}</p>
              </div>
            </div>
            <button
              onClick={onLogout}
              className="p-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-red-100 dark:hover:bg-red-900/20 text-gray-700 dark:text-gray-300 hover:text-red-600 transition-colors"
              title="Sign out"
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
