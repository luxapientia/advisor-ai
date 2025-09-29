import React from 'react';
import { LogOut } from 'lucide-react';

interface SettingsDropdownProps {
  onLogout: () => void;
}

const SettingsDropdown: React.FC<SettingsDropdownProps> = ({
  onLogout,
}) => {
  return (
    <div className="bg-white border-b border-gray-200 px-4 py-3">
      <div className="space-y-2">
        <button
          onClick={onLogout}
          className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md"
        >
          <LogOut className="h-4 w-4 inline mr-2" />
          Logout
        </button>
      </div>
    </div>
  );
};

export default SettingsDropdown;