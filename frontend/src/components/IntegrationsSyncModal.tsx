import React, { useEffect, useState } from 'react';
import { Loader2, CheckCircle, AlertCircle, Mail, Calendar, Users } from 'lucide-react';
import { googleSyncService, GoogleSyncStatus } from '../services/googleSync';
import { hubspotSyncService, HubSpotSyncStatus } from '../services/hubspotSync';
import toast from 'react-hot-toast';
import { AxiosError } from 'axios';

interface IntegrationsSyncModalProps {
  isOpen: boolean;
  onSyncComplete?: () => void;
}

const IntegrationsSyncModal: React.FC<IntegrationsSyncModalProps> = ({
  isOpen,
  onSyncComplete
}) => {
  const [googleSyncStatus, setGoogleSyncStatus] = useState<GoogleSyncStatus | null>(null);
  const [hubspotSyncStatus, setHubspotSyncStatus] = useState<HubSpotSyncStatus | null>(null);

  // Auto-start sync and poll for updates
  useEffect(() => {
    if (!isOpen) return;

    const initializeSync = async () => {
      try {
        // Check both Google and HubSpot sync status
        const [googleStatus, hubspotStatus] = await Promise.all([
          googleSyncService.getSyncStatus(),
          hubspotSyncService.getSyncStatus()
        ]);
        
        setGoogleSyncStatus(googleStatus);
        setHubspotSyncStatus(hubspotStatus);
        
        // Auto-start sync if user has access
        if (googleStatus.has_google_access) {
          try {
            await googleSyncService.startSync();
          } catch (error) {
            // Handle 'already in progress' errors gracefully
            if (error instanceof AxiosError && error.response?.status === 400) {
              console.log('Google sync already in progress, skipping');
            } else {
              console.error('Failed to start Google sync:', error);
            }
          }
        }
        if (hubspotStatus.has_hubspot_access) {
          try {
            await hubspotSyncService.startSync();
          } catch (error) {
            // Handle 'already in progress' errors gracefully
            if (error instanceof AxiosError && error.response?.status === 400) {
              console.log('HubSpot sync already in progress, skipping');
            } else {
              console.error('Failed to start HubSpot sync:', error);
            }
          }
        }
      } catch (error) {
        console.error('Failed to initialize integrations sync:', error);
        
        // If we get a 403 error, user is not authenticated - don't show error toast
        if (error instanceof AxiosError && error.response?.status === 403) {
          return; // Just return silently
        }
        
        // If we get a 400 error, sync is already in progress - don't show error toast
        if (error instanceof AxiosError && error.response?.status === 400) {
          return; // Just return silently
        }
        
        toast.error('Failed to start integrations sync');
      }
    };

    // Start initial sync
    initializeSync();

    // Poll for status updates
    const pollInterval = setInterval(async () => {
      try {
        const [googleStatus, hubspotStatus] = await Promise.all([
          googleSyncService.getSyncStatus(),
          hubspotSyncService.getSyncStatus()
        ]);
        
        setGoogleSyncStatus(googleStatus);
        setHubspotSyncStatus(hubspotStatus);

        // Check if all syncs are completed or failed
        const allCompleted = (googleStatus.completed || !googleStatus.has_google_access) && 
                           (hubspotStatus.completed || !hubspotStatus.has_hubspot_access);
        const anyError = googleStatus.status === 'error' || hubspotStatus.status === 'error';

        console.log('Sync status check:', { 
          googleStatus: googleStatus.status, 
          hubspotStatus: hubspotStatus.status,
          allCompleted, 
          anyError 
        });

        if (allCompleted || anyError) {
          if (allCompleted) {
            const completedServices = [];
            if (googleStatus.completed) completedServices.push('Google');
            if (hubspotStatus.completed) completedServices.push('HubSpot');
            
            if (completedServices.length > 0) {
              toast.success(`${completedServices.join(' and ')} sync completed! Your data is now searchable.`);
            }
          } else {
            toast.error('Sync failed. Please try again.');
          }
          onSyncComplete?.();
          clearInterval(pollInterval);
        }
      } catch (error) {
        console.error('Failed to get sync status:', error);
        
        // If we get a 403 error, user is not authenticated - stop polling
        if (error instanceof AxiosError && error.response?.status === 403) {
          clearInterval(pollInterval);
          onSyncComplete?.();
        }
      }
    }, 2000); // Poll every 2 seconds

    // Add timeout to prevent infinite polling (5 minutes max)
    const timeoutId = setTimeout(() => {
      console.log('Sync polling timeout reached, stopping polling');
      clearInterval(pollInterval);
      onSyncComplete?.();
    }, 5 * 60 * 1000); // 5 minutes

    return () => {
      clearInterval(pollInterval);
      clearTimeout(timeoutId);
    };
  }, [isOpen, onSyncComplete]);

  if (!isOpen) return null;

  const getOverallStatus = () => {
    if (!googleSyncStatus && !hubspotSyncStatus) return 'syncing';
    
    const googleStatus = googleSyncStatus?.status || 'none';
    const hubspotStatus = hubspotSyncStatus?.status || 'none';
    
    // If any is syncing, overall is syncing
    if (googleStatus === 'syncing' || hubspotStatus === 'syncing') return 'syncing';
    
    // If any has error, overall has error
    if (googleStatus === 'error' || hubspotStatus === 'error') return 'error';
    
    // If all are completed or user doesn't have access, overall is completed
    const googleCompleted = googleStatus === 'completed' || !googleSyncStatus?.has_google_access;
    const hubspotCompleted = hubspotStatus === 'completed' || !hubspotSyncStatus?.has_hubspot_access;
    
    if (googleCompleted && hubspotCompleted) return 'completed';
    
    return 'syncing';
  };

  const getStatusIcon = () => {
    const status = getOverallStatus();
    
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-8 w-8 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-8 w-8 text-red-500" />;
      default:
        return <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />;
    }
  };

  const getStatusText = () => {
    const status = getOverallStatus();
    
    switch (status) {
      case 'syncing':
        return 'Syncing your data...';
      case 'completed':
        return 'Sync completed!';
      case 'error':
        return 'Sync failed';
      default:
        return 'Syncing your data...';
    }
  };

  const getStatusDescription = () => {
    const status = getOverallStatus();
    
    switch (status) {
      case 'completed':
        return 'Your data is now searchable by AI.';
      case 'error':
        return 'Please refresh the page to try again.';
      default:
        return 'We are indexing your data for AI search.';
    }
  };

  // const getActiveServices = () => {
  //   const services = [];
    
  //   if (googleSyncStatus?.has_google_access && googleSyncStatus.status === 'syncing') {
  //     services.push('Google');
  //   }
  //   if (hubspotSyncStatus?.has_hubspot_access && hubspotSyncStatus.status === 'syncing') {
  //     services.push('HubSpot');
  //   }
    
  //   return services;
  // };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        {/* Backdrop */}
        <div className="fixed inset-0 bg-gray-600 bg-opacity-75 transition-opacity" />
        
        {/* Modal */}
        <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-auto">
          {/* Header */}
          <div className="flex items-center justify-center p-6 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              {getStatusIcon()}
              <h3 className="text-lg font-semibold text-gray-900">
                Integrations Sync
              </h3>
            </div>
          </div>
          
          {/* Content */}
          <div className="p-6 text-center">
            <h4 className="text-lg font-medium text-gray-900 mb-2">
              {getStatusText()}
            </h4>
            <p className="text-sm text-gray-600 mb-4">
              {getStatusDescription()}
            </p>
            
            {/* Sync Progress Indicators */}
            {getOverallStatus() === 'syncing' && (
              <div className="space-y-3">
                {googleSyncStatus?.has_google_access && (
                  <div className="flex items-center justify-center space-x-2 text-sm text-gray-600">
                    <Mail className="h-4 w-4" />
                    <span>Syncing Gmail emails...</span>
                  </div>
                )}
                {googleSyncStatus?.has_google_access && (
                  <div className="flex items-center justify-center space-x-2 text-sm text-gray-600">
                    <Calendar className="h-4 w-4" />
                    <span>Syncing Calendar events...</span>
                  </div>
                )}
                {hubspotSyncStatus?.has_hubspot_access && (
                  <div className="flex items-center justify-center space-x-2 text-sm text-gray-600">
                    <Users className="h-4 w-4" />
                    <span>Syncing HubSpot contacts...</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default IntegrationsSyncModal;