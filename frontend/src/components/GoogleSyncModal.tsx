import React, { useEffect, useState } from 'react';
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { googleSyncService, GoogleSyncStatus } from '../services/googleSync';
import toast from 'react-hot-toast';

interface GoogleSyncModalProps {
  isOpen: boolean;
  onSyncComplete?: () => void;
}

const GoogleSyncModal: React.FC<GoogleSyncModalProps> = ({
  isOpen,
  onSyncComplete
}) => {
  const [syncStatus, setSyncStatus] = useState<GoogleSyncStatus | null>(null);

  // Auto-start sync and poll for updates
  useEffect(() => {
    if (!isOpen) return;

    const initializeSync = async () => {
      try {
        const status = await googleSyncService.getSyncStatus();
        setSyncStatus(status);
        
        // Auto-start sync if needed
        if (status.needed) {
          await googleSyncService.startSync();
        }
      } catch (error) {
        console.error('Failed to initialize Gmail sync:', error);
        toast.error('Failed to start Gmail sync');
      }
    };

    // Start initial sync
    initializeSync();

    // Poll for status updates
    const pollInterval = setInterval(async () => {
      try {
        const status = await googleSyncService.getSyncStatus();
        setSyncStatus(status);

        // If sync is completed or failed, notify parent
        if (status.completed || status.status === 'error') {
          if (status.completed) {
            toast.success('Google sync completed! Your emails are now searchable.');
          } else {
            toast.error('Google sync failed. Please try again.');
          }
          onSyncComplete?.();
          clearInterval(pollInterval);
        }
      } catch (error) {
        console.error('Failed to get sync status:', error);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(pollInterval);
  }, [isOpen, onSyncComplete]);

  if (!isOpen) return null;

  const getStatusIcon = () => {
    if (!syncStatus) return <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />;
    
    switch (syncStatus.status) {
      case 'completed':
        return <CheckCircle className="h-8 w-8 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-8 w-8 text-red-500" />;
      default:
        return <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />;
    }
  };

  const getStatusText = () => {
    if (!syncStatus) return 'Preparing to sync Google...';
    
    switch (syncStatus.status) {
      case 'none':
        return 'Preparing to sync Google...';
      case 'pending':
        return 'Preparing to sync Google...';
      case 'syncing':
        return 'Syncing your Google emails...';
      case 'completed':
        return 'Google sync completed!';
      case 'error':
        return 'Google sync failed';
      default:
        return 'Syncing your Google emails...';
    }
  };

  const getStatusDescription = () => {
    switch (syncStatus?.status) {
      case 'completed':
        return 'Your emails are now searchable.';
      case 'error':
        return 'Please refresh the page to try again.';
      default:
        return 'We are indexing your emails for AI search.';
    }
  };

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
                Google Sync
              </h3>
            </div>
          </div>
          
          {/* Content */}
          <div className="p-6 text-center">
            <h4 className="text-lg font-medium text-gray-900 mb-2">
              {getStatusText()}
            </h4>
            <p className="text-sm text-gray-600">
              {getStatusDescription()}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GoogleSyncModal;