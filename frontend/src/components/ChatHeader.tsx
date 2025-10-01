import React from 'react';
import { LogOut, Users, Menu } from 'lucide-react';
import { User } from '../types';

interface ChatHeaderProps {
  onLogout: () => void;
  hasHubSpotAccess: boolean;
  onConnectHubSpot: () => void;
  connectingHubSpot: boolean;
  user: User | null;
  onSidebarToggle: () => void;
}

const ChatHeader: React.FC<ChatHeaderProps> = ({
  onLogout,
  hasHubSpotAccess,
  onConnectHubSpot,
  connectingHubSpot,
  user,
  onSidebarToggle,
}) => {
  const getUserInitials = (user: User) => {
    if (user.first_name && user.last_name) {
      return `${user.first_name[0]}${user.last_name[0]}`.toUpperCase();
    }
    if (user.display_name) {
      return user.display_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    }
    return user.email[0].toUpperCase();
  };

  const getUserDisplayName = (user: User) => {
    if (user.display_name) return user.display_name;
    if (user.first_name && user.last_name) return `${user.first_name} ${user.last_name}`;
    return user.email.split('@')[0];
  };

  return (
    <div className="bg-white border-b border-gray-200 px-4 py-3">
      <div className="flex items-center justify-between">
        {/* Left side - Sidebar toggle and Title */}
        <div className="flex items-center space-x-3">
          <button
            onClick={onSidebarToggle}
            className="p-2 text-gray-400 hover:text-gray-500 md:hidden"
            title="Toggle sidebar"
          > 
            <Menu className="h-5 w-5" />
          </button>
          <h1 className="text-lg font-semibold text-gray-900">Ask Anything</h1>
        </div>


        {/* Right side - HubSpot Connection Button, User info and logout */}
        <div className="flex items-center space-x-3">
          {/* HubSpot Connection Button */}
          {!hasHubSpotAccess ? (
            <button
              onClick={onConnectHubSpot}
              disabled={connectingHubSpot}
              className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Users className="h-4 w-4 mr-1" />
              {connectingHubSpot ? 'Connecting...' : 'Connect HubSpot'}
            </button>
          ) : (
            <div className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-green-700 bg-green-100 border border-green-200 rounded-md">
              <Users className="h-4 w-4 mr-1" />
              HubSpot Connected
            </div>
          )}
          
          {/* User info */}
          {user && (
            <div className="flex items-center space-x-2">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center text-white text-sm font-medium">
                  {getUserInitials(user)}
                </div>
                <div className="text-sm">
                  <div className="font-medium text-gray-900">{getUserDisplayName(user)}</div>
                  <div className="text-gray-500">{user.email}</div>
                </div>
              </div>
              <button
                onClick={onLogout}
                className="p-1 text-gray-400 hover:text-gray-500"
                title="Logout"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatHeader;