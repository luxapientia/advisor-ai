import React, { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { authService } from '../services/auth';
import { MessageSquare, Mail, Calendar, Users } from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';

const Login: React.FC = () => {
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Handle OAuth callback
    const handleOAuthCallback = async () => {
      const urlParams = new URLSearchParams(window.location.search);
      const accessToken = urlParams.get('access_token');
      const refreshToken = urlParams.get('refresh_token');
      const userId = urlParams.get('user');
      const error = urlParams.get('error');

      if (error) {
        setError('Authentication failed. Please try again.');
        return;
      }

      if (accessToken && refreshToken && userId) {
        setLoading(true);
        try {
          // Get user details from backend
          const response = await fetch('/api/v1/auth/me', {
            headers: {
              'Authorization': `Bearer ${accessToken}`,
            },
          });

          if (response.ok) {
            const user = await response.json();
            login(accessToken, refreshToken, user);
            window.location.href = '/chat';
          } else {
            setError('Failed to get user information. Please try again.');
          }
        } catch (err) {
          setError('Authentication failed. Please try again.');
        } finally {
          setLoading(false);
        }
      }
    };

    handleOAuthCallback();
  }, [login]);

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const { authorization_url } = await authService.getGoogleAuthUrl();
      window.location.href = authorization_url;
    } catch (err) {
      setError('Failed to initiate Google authentication. Please try again.');
      setLoading(false);
    }
  };


  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-gray-600">Authenticating...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="flex justify-center">
            <div className="h-12 w-12 bg-primary-600 rounded-lg flex items-center justify-center">
              <MessageSquare className="h-8 w-8 text-white" />
            </div>
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Financial Advisor AI
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Sign in to access your AI assistant
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">
                  Authentication Error
                </h3>
                <div className="mt-2 text-sm text-red-700">
                  {error}
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="space-y-4">
          <button
            onClick={handleGoogleLogin}
            disabled={loading}
            className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
          >
            <Mail className="h-5 w-5 mr-2" />
            Sign in with Google
          </button>

        </div>

        <div className="mt-8">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-gray-50 text-gray-500">Features</span>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-4">
            <div className="flex items-center">
              <Mail className="h-5 w-5 text-primary-600 mr-3" />
              <span className="text-sm text-gray-600">Gmail integration for email management</span>
            </div>
            <div className="flex items-center">
              <Calendar className="h-5 w-5 text-primary-600 mr-3" />
              <span className="text-sm text-gray-600">Google Calendar for scheduling</span>
            </div>
            <div className="flex items-center">
              <Users className="h-5 w-5 text-primary-600 mr-3" />
              <span className="text-sm text-gray-600">HubSpot CRM for client management</span>
            </div>
          </div>
        </div>

        <div className="text-center">
          <p className="text-xs text-gray-500">
            By signing in, you agree to our Terms of Service and Privacy Policy
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;