import React from 'react';
import { Plus, LogOut, Settings } from 'lucide-react';

interface ChatHeaderProps {
  onNewChat: () => void;
  onLogout: () => void;
  onSettingsToggle: () => void;
  showSettings: boolean;
}

const ChatHeader: React.FC<ChatHeaderProps> = ({
  onNewChat,
  onLogout,
  onSettingsToggle,
  showSettings,
}) => {
  return (
    <div className="bg-white border-b border-gray-200 px-4 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <h1 className="text-lg font-semibold text-gray-900">Ask Anything</h1>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={onNewChat}
            className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <Plus className="h-4 w-4 mr-1" />
            New thread
          </button>
          <button
            onClick={onSettingsToggle}
            className="p-2 text-gray-400 hover:text-gray-500"
          >
            <Settings className="h-5 w-5" />
          </button>
          <button
            onClick={onLogout}
            className="p-2 text-gray-400 hover:text-gray-500"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </div>
      
      {/* Navigation Tabs */}
      <div className="flex mt-3 space-x-1">
        <button className="px-3 py-2 text-sm font-medium text-gray-900 bg-gray-100 rounded-md">
          Chat
        </button>
        <button className="px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-700">
          History
        </button>
      </div>
    </div>
  );
};

export default ChatHeader;