import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider } from './context/AuthContext';

import { Login } from './pages/auth/Login';
import { ForgotPassword } from './pages/auth/ForgotPassword';
import { ResetPassword } from './pages/auth/ResetPassword';

import { ProtectedRoute } from './routes/ProtectedRoute';
import { RoleRoute } from './routes/RoleRoute';
import { RoleRedirect } from './routes/RoleRedirect';

import { AdminLayout } from './layouts/AdminLayout';
import { StoreLayout } from './layouts/StoreLayout';

import { AdminDashboard } from './pages/admin/AdminDashboard';
import { Stores } from './pages/admin/Stores';
import { StoreForm } from './pages/admin/StoreForm';
import { AuditLog } from './pages/admin/AuditLog';

import { Settings } from './pages/store/Settings';
import { Datasets } from './pages/store/Datasets';
import { ScheduledJob } from './pages/store/ScheduledJob';
import { Exports } from './pages/store/Exports';
import { Recommendations } from './pages/store/Recommendations';
import { Customers } from './pages/store/Customers';
import { Trends } from './pages/store/Trends';
import { AskPairly } from './pages/store/AskPairly';

import { Dashboard } from './pages/Dashboard';
import { AssociationRules } from './pages/AssociationRules';
import { ProductBundles } from './pages/ProductBundles';
import { RevenueAnalysis } from './pages/RevenueAnalysis';
import { SeasonalAnalysis } from './pages/SeasonalAnalysis';
import { NetworkView } from './pages/NetworkView';
import { DataSummary } from './pages/DataSummary';

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />

            <Route path="/" element={<RoleRedirect />} />

            <Route
              path="/admin"
              element={
                <RoleRoute roles={['super_admin']}>
                  <AdminLayout />
                </RoleRoute>
              }
            >
              <Route index element={<AdminDashboard />} />
              <Route path="stores" element={<Stores />} />
              <Route path="stores/new" element={<StoreForm />} />
              <Route path="audit-log" element={<AuditLog />} />
            </Route>

            <Route
              element={
                <ProtectedRoute>
                  <StoreLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/ask" element={<AskPairly />} />
              <Route path="/association-rules" element={<AssociationRules />} />
              <Route path="/product-bundles" element={<ProductBundles />} />
              <Route path="/recommendations" element={<Recommendations />} />
              <Route path="/customers" element={<Customers />} />
              <Route path="/trends" element={<Trends />} />
              <Route path="/revenue-analysis" element={<RevenueAnalysis />} />
              <Route path="/seasonal-analysis" element={<SeasonalAnalysis />} />
              <Route path="/network-view" element={<NetworkView />} />
              <Route path="/data-summary" element={<DataSummary />} />

              <Route path="/store/settings" element={<Settings />} />
              <Route path="/store/datasets" element={<Datasets />} />
              <Route path="/store/scheduled-job" element={<ScheduledJob />} />
              <Route path="/store/exports" element={<Exports />} />
            </Route>
          </Routes>

          <Toaster
            position="top-right"
            toastOptions={{
              duration: 3000,
              style: { background: '#1f2937', color: '#fff' },
              success: { duration: 3000, style: { background: '#10b981' } },
              error: { duration: 4000, style: { background: '#ef4444' } },
            }}
          />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
