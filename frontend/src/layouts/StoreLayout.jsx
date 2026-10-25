import { useState, useEffect } from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { Home, Link as LinkIcon, Package, TrendingUp, Calendar, Database, Settings, Upload, FileDown, Clock, Sparkles, Users, BarChart3, MessageSquareText } from 'lucide-react';
import { Header } from '../components/Header';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';

const menuItems = [
  { icon: Home, label: 'Dashboard', path: '/dashboard' },
  { icon: MessageSquareText, label: 'Ask Pairly', path: '/ask' },
  { icon: Sparkles, label: 'Recommendations', path: '/recommendations' },
  { icon: Users, label: 'Customers (RFM)', path: '/customers' },
  { icon: BarChart3, label: 'Trends', path: '/trends' },
  { type: 'divider' },
  { icon: LinkIcon, label: 'Association Rules', path: '/association-rules' },
  { icon: Package, label: 'Product Bundles', path: '/product-bundles' },
  { icon: TrendingUp, label: 'Revenue Analysis', path: '/revenue-analysis' },
  { icon: Calendar, label: 'Seasonal Analysis', path: '/seasonal-analysis' },
  { icon: Database, label: 'Data Summary', path: '/data-summary' },
  { type: 'divider' },
  { icon: Upload, label: 'My Datasets', path: '/store/datasets' },
  { icon: FileDown, label: 'Exports', path: '/store/exports' },
  { icon: Clock, label: 'Scheduled Job', path: '/store/scheduled-job' },
  { icon: Settings, label: 'Settings', path: '/store/settings' },
];

export const StoreLayout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { store } = useAuth();
  const { setBrand } = useTheme();

  useEffect(() => {
    if (store?.brand_primary_color) {
      document.documentElement.style.setProperty('--brand-primary', store.brand_primary_color);
    }
    if (store?.theme_mode) {
      setBrand && setBrand(store.theme_mode);
    }
  }, [store?.brand_primary_color, store?.theme_mode]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Header
        toggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        isSidebarOpen={sidebarOpen}
        title={store?.name || 'My Store'}
        subtitle="Pairly · Market basket analytics"
      />
      <div className="flex min-h-[calc(100vh-4rem)]">
        <aside
          className={`${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} fixed inset-y-0 left-0 z-30 w-64 mt-16 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 transform transition-transform duration-200 ease-in-out lg:translate-x-0 lg:static lg:inset-0 lg:mt-0`}
        >
          <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
            {menuItems.map((item, idx) =>
              item.type === 'divider' ? (
                <div key={idx} className="my-3 border-t border-gray-200 dark:border-gray-800" />
              ) : (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/dashboard'}
                  className={({ isActive }) =>
                    `flex items-center px-4 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                      isActive
                        ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400 border border-primary-100 dark:border-primary-800'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                    }`
                  }
                  onClick={() => setSidebarOpen(false)}
                >
                  <item.icon className="mr-3 h-5 w-5" />
                  {item.label}
                </NavLink>
              )
            )}
          </nav>
        </aside>
        <main
          className="flex-1 p-4 md:p-6 lg:p-8 overflow-auto"
          onClick={() => sidebarOpen && setSidebarOpen(false)}
        >
          <div className="max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
