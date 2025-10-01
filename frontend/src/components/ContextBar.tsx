import React from 'react';

interface ContextBarProps {
  hasGoogleAccess: boolean;
  hasHubSpotAccess: boolean;
}

const ContextBar: React.FC<ContextBarProps> = ({
  hasGoogleAccess,
  hasHubSpotAccess,
}) => {
  const getContextText = () => {
    if (hasGoogleAccess && hasHubSpotAccess) {
      return 'Gmail + Calendar + HubSpot CRM';
    } else if (hasGoogleAccess) {
      return 'Gmail + Calendar';
    } else {
      return 'Limited access - connect accounts for full features';
    }
  };

  return (
    <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-600">
          Context set to {getContextText()}
        </span>
        <span className="text-xs text-gray-500">
          {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {new Date().toLocaleDateString()}
        </span>
      </div>
    </div>
  );
};

export default ContextBar;