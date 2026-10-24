import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AuthLayout } from '../../layouts/AuthLayout';
import { forgotPasswordApi } from '../../api/authApi';
import toast from 'react-hot-toast';

export const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await forgotPasswordApi(email);
      setSent(true);
      toast.success('If the account exists, a reset email has been sent.');
    } catch {
      toast.error('Something went wrong, please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout title="Reset your password" subtitle="Enter your email and we'll send a reset link.">
      {sent ? (
        <div className="text-center space-y-4">
          <p className="text-gray-700 dark:text-gray-300">Check your inbox for a reset link (valid for 60 minutes).</p>
          <Link to="/login" className="text-primary-600 hover:underline">Back to login</Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 outline-none"
              required
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-primary-600 hover:bg-primary-700 disabled:opacity-60 text-white font-medium py-2.5 rounded-lg"
          >
            {submitting ? 'Sending...' : 'Send reset link'}
          </button>
          <div className="text-center text-sm">
            <Link to="/login" className="text-primary-600 hover:underline">Back to login</Link>
          </div>
        </form>
      )}
    </AuthLayout>
  );
};
