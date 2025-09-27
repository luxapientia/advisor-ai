import React from 'react';
import { Users, X } from 'lucide-react';

interface HubSpotBannerProps {
  onConnect: () => void;
  onDismiss: () => void;
  connecting: boolean;
}

const HubSpotBanner: React.FC<HubSpotBannerProps> = ({
  onConnect,
  onDismiss,
  connecting,
}) => {
  return (
    <div className="bg-orange-50 border-b border-orange-200 px-4 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Users className="h-5 w-5 text-orange-600 mr-2" />
          <div>
            <p className="text-sm font-medium text-orange-800">
              Connect your HubSpot account to unlock CRM features
            </p>
            <p className="text-xs text-orange-600">
              Access client data, manage contacts, and get better AI insights
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={onConnect}
            disabled={connecting}
            className="bg-orange-600 text-white px-3 py-1 rounded text-sm hover:bg-orange-700 disabled:opacity-50"
          >
            {connecting ? 'Connecting...' : 'Connect HubSpot'}
          </button>
          <button
            onClick={onDismiss}
            className="text-orange-600 hover:text-orange-800"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default HubSpotBanner;