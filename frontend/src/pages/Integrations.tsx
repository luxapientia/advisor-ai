import React, { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { apiClient } from '../services/api';
import { IntegrationAccount } from '../types';
import { Mail, Users, CheckCircle, XCircle, RefreshCw, Settings } from 'lucide-react';
import toast from 'react-hot-toast';

const Integrations: React.FC = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);

  useEffect(() => {
    loadIntegrations();
  }, []);

  const loadIntegrations = async () => {
    try {
      // Load integrations data (currently not used in UI but kept for future use)
      await apiClient.get<IntegrationAccount[]>('/integrations/accounts');
    } catch (error) {
      console.error('Failed to load integrations:', error);
      toast.error('Failed to load integrations');
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async (service: string) => {
    try {
      if (service === 'google') {
        const redirectUri = `${window.location.origin}/auth/google/callback`;
        const { authorization_url } = await apiClient.post('/auth/google/authorize', {
          redirect_uri: redirectUri,
        });
        window.location.href = authorization_url;
      } else if (service === 'hubspot') {
        const redirectUri = `${window.location.origin}/auth/hubspot/callback`;
        const { authorization_url } = await apiClient.post('/auth/hubspot/authorize', {
          redirect_uri: redirectUri,
        });
        window.location.href = authorization_url;
      }
    } catch (error) {
      console.error('Failed to initiate connection:', error);
      toast.error('Failed to initiate connection');
    }
  };

  const handleDisconnect = async (service: string) => {
    // Only allow disconnecting HubSpot - Google disconnection is handled by logout
    if (service === 'google') {
      toast.error('Please use the logout button to disconnect Google account');
      return;
    }
    
    if (window.confirm(`Are you sure you want to disconnect ${service}?`)) {
      try {
        await apiClient.delete(`/integrations/accounts/${service}`);
        toast.success(`${service} disconnected successfully`);
        loadIntegrations();
      } catch (error) {
        console.error('Failed to disconnect:', error);
        toast.error('Failed to disconnect integration');
      }
    }
  };

  const handleSync = async (service: string) => {
    setSyncing(service);
    try {
      await apiClient.post('/integrations/sync/trigger', {
        service,
        sync_type: 'manual',
      });
      toast.success(`${service} sync triggered successfully`);
    } catch (error) {
      console.error('Failed to trigger sync:', error);
      toast.error('Failed to trigger sync');
    } finally {
      setSyncing(null);
    }
  };

  const getServiceIcon = (service: string) => {
    switch (service) {
      case 'google':
        return <Mail className="h-6 w-6 text-red-600" />;
      case 'hubspot':
        return <Users className="h-6 w-6 text-orange-600" />;
      default:
        return <Settings className="h-6 w-6 text-gray-600" />;
    }
  };

  const getServiceName = (service: string) => {
    switch (service) {
      case 'google':
        return 'Google (Gmail & Calendar)';
      case 'hubspot':
        return 'HubSpot CRM';
      default:
        return service;
    }
  };

  const getServiceDescription = (service: string) => {
    switch (service) {
      case 'google':
        return 'Access your Gmail emails and Google Calendar events';
      case 'hubspot':
        return 'Manage your CRM contacts, companies, and deals';
      default:
        return 'Third-party service integration';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 text-gray-400 mx-auto mb-4 animate-spin" />
          <p className="text-gray-500">Loading integrations...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Integrations</h1>
        <p className="mt-2 text-gray-600">
          Connect your accounts to enable AI assistant features
        </p>
      </div>

      <div className="space-y-6">
        {/* Google Integration */}
        <div className="bg-white shadow rounded-lg">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                {getServiceIcon('google')}
                <div className="ml-4">
                  <h3 className="text-lg font-medium text-gray-900">
                    {getServiceName('google')}
                  </h3>
                  <p className="text-sm text-gray-600">
                    {getServiceDescription('google')}
                  </p>
                  <div className="mt-2 flex items-center space-x-4">
                    <div className="flex items-center">
                      {user?.has_google_access ? (
                        <CheckCircle className="h-4 w-4 text-green-600 mr-1" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-600 mr-1" />
                      )}
                      <span className="text-sm text-gray-600">
                        {user?.has_google_access ? 'Connected' : 'Not connected'}
                      </span>
                    </div>
                    {user?.has_google_access && (
                      <div className="flex items-center">
                        <span className="text-sm text-gray-600">
                          Last sync: {new Date().toLocaleDateString()}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              
            </div>
          </div>
        </div>

        {/* HubSpot Integration */}
        <div className="bg-white shadow rounded-lg">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                {getServiceIcon('hubspot')}
                <div className="ml-4">
                  <h3 className="text-lg font-medium text-gray-900">
                    {getServiceName('hubspot')}
                  </h3>
                  <p className="text-sm text-gray-600">
                    {getServiceDescription('hubspot')}
                  </p>
                  <div className="mt-2 flex items-center space-x-4">
                    <div className="flex items-center">
                      {user?.has_hubspot_access ? (
                        <CheckCircle className="h-4 w-4 text-green-600 mr-1" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-600 mr-1" />
                      )}
                      <span className="text-sm text-gray-600">
                        {user?.has_hubspot_access ? 'Connected' : 'Not connected'}
                      </span>
                    </div>
                    {user?.has_hubspot_access && (
                      <div className="flex items-center">
                        <span className="text-sm text-gray-600">
                          Last sync: {new Date().toLocaleDateString()}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex space-x-2">
                {user?.has_hubspot_access ? (
                  <>
                    <button
                      onClick={() => handleSync('hubspot')}
                      disabled={syncing === 'hubspot'}
                      className="btn-secondary"
                    >
                      {syncing === 'hubspot' ? (
                        <RefreshCw className="h-4 w-4 animate-spin" />
                      ) : (
                        <RefreshCw className="h-4 w-4" />
                      )}
                    </button>
                    <button
                      onClick={() => handleDisconnect('hubspot')}
                      className="btn-danger"
                    >
                      Disconnect
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => handleConnect('hubspot')}
                    className="btn-primary"
                  >
                    Connect
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Integration Status */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Integration Status</h3>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm font-medium text-gray-900">Gmail Access</span>
                {user?.has_google_access ? (
                  <CheckCircle className="h-5 w-5 text-green-600" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-600" />
                )}
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm font-medium text-gray-900">Calendar Access</span>
                {user?.has_google_access ? (
                  <CheckCircle className="h-5 w-5 text-green-600" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-600" />
                )}
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm font-medium text-gray-900">HubSpot CRM</span>
                {user?.has_hubspot_access ? (
                  <CheckCircle className="h-5 w-5 text-green-600" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-600" />
                )}
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm font-medium text-gray-900">Data Sync</span>
                <CheckCircle className="h-5 w-5 text-green-600" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Integrations;