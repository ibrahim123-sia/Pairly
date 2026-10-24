import { Logo } from '../components/Logo';
import { APP_NAME, APP_TAGLINE } from '../brand';

export const AuthLayout = ({ children, title, subtitle }) => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <Logo className="h-14 w-14" />
          <h1 className="mt-3 text-2xl font-bold text-gray-900 dark:text-white">{APP_NAME}</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 text-center max-w-xs">{APP_TAGLINE}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8 border border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-1">{title}</h2>
          {subtitle && <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">{subtitle}</p>}
          {children}
        </div>
      </div>
    </div>
  );
};
