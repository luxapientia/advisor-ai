import React from 'react';
import { MessageSquare } from 'lucide-react';

const ChatEmptyState: React.FC = () => {
  return (
    <div className="flex items-center justify-center h-full px-4">
      <div className="max-w-lg w-full">
        <div className="mb-8 text-center">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <MessageSquare className="h-8 w-8 text-blue-600" />
          </div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            I can help you with your financial advisory tasks
          </h3>
        </div>
        <div className="text-left">
          <p className="text-gray-600 mb-6 text-center">
            Ask me anything about your clients, schedule meetings, manage your CRM, or get insights from your data.
          </p>
          <div className="space-y-3 text-sm text-gray-500">
            <p>• "Show me emails from clients asking about market volatility"</p>
            <p>• "Schedule a meeting with John Smith next Tuesday"</p>
            <p>• "Find all contacts in HubSpot from last month"</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatEmptyState;