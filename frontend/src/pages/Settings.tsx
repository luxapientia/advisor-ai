import React, { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { apiClient } from '../services/api';
import { UserUpdateForm, UserPreferencesForm } from '../types';
import { User, Save, Mail, Bell, Palette, Globe } from 'lucide-react';
import toast from 'react-hot-toast';

const Settings: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');
  const [loading, setLoading] = useState(false);

  // Profile form state
  const [profileForm, setProfileForm] = useState<UserUpdateForm>({
    first_name: '',
    last_name: '',
    full_name: '',
    avatar_url: '',
  });

  // Preferences form state
  const [preferencesForm, setPreferencesForm] = useState<UserPreferencesForm>({
    preferences: {
      theme: 'light',
      notifications: {
        email: true,
        push: false,
      },
      chat: {
        streaming: true,
        context_length: 5,
      },
      integrations: {
        auto_sync: true,
        sync_interval: 3600,
      },
    },
  });

  // Initialize forms with user data
  useEffect(() => {
    if (user) {
      setProfileForm({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        full_name: user.full_name || '',
        avatar_url: user.avatar_url || '',
      });

      setPreferencesForm({
        preferences: user.preferences || {
          theme: 'light',
          notifications: { email: true, push: false },
          chat: { streaming: true, context_length: 5 },
          integrations: { auto_sync: true, sync_interval: 3600 },
        },
      });
    }
  }, [user]);

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await apiClient.put('/users/me', profileForm);
      await refreshUser();
      toast.success('Profile updated successfully');
    } catch (error) {
      console.error('Failed to update profile:', error);
      toast.error('Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  const handlePreferencesSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await apiClient.put('/users/me/preferences', preferencesForm);
      await refreshUser();
      toast.success('Preferences updated successfully');
    } catch (error) {
      console.error('Failed to update preferences:', error);
      toast.error('Failed to update preferences');
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'profile', name: 'Profile', icon: User },
    { id: 'preferences', name: 'Preferences', icon: Palette },
    { id: 'notifications', name: 'Notifications', icon: Bell },
    { id: 'integrations', name: 'Integrations', icon: Globe },
  ];

  if (!user) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <User className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">Loading user data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="mt-2 text-gray-600">
          Manage your account settings and preferences
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Sidebar */}
        <div className="lg:w-64 flex-shrink-0">
          <nav className="space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200 ${
                    activeTab === tab.id
                      ? 'bg-primary-100 text-primary-900'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  <Icon className="mr-3 h-5 w-5" />
                  {tab.name}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1">
          {activeTab === 'profile' && (
            <div className="bg-white shadow rounded-lg">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">Profile Information</h2>
                <p className="mt-1 text-sm text-gray-600">
                  Update your personal information and profile details
                </p>
              </div>
              <form onSubmit={handleProfileSubmit} className="p-6 space-y-6">
                <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                  <div>
                    <label htmlFor="first_name" className="block text-sm font-medium text-gray-700">
                      First Name
                    </label>
                    <input
                      type="text"
                      id="first_name"
                      value={profileForm.first_name}
                      onChange={(e) => setProfileForm(prev => ({ ...prev, first_name: e.target.value }))}
                      className="mt-1 input"
                    />
                  </div>
                  <div>
                    <label htmlFor="last_name" className="block text-sm font-medium text-gray-700">
                      Last Name
                    </label>
                    <input
                      type="text"
                      id="last_name"
                      value={profileForm.last_name}
                      onChange={(e) => setProfileForm(prev => ({ ...prev, last_name: e.target.value }))}
                      className="mt-1 input"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="full_name" className="block text-sm font-medium text-gray-700">
                    Full Name
                  </label>
                  <input
                    type="text"
                    id="full_name"
                    value={profileForm.full_name}
                    onChange={(e) => setProfileForm(prev => ({ ...prev, full_name: e.target.value }))}
                    className="mt-1 input"
                  />
                </div>

                <div>
                  <label htmlFor="avatar_url" className="block text-sm font-medium text-gray-700">
                    Avatar URL
                  </label>
                  <input
                    type="url"
                    id="avatar_url"
                    value={profileForm.avatar_url}
                    onChange={(e) => setProfileForm(prev => ({ ...prev, avatar_url: e.target.value }))}
                    className="mt-1 input"
                    placeholder="https://example.com/avatar.jpg"
                  />
                </div>

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={loading}
                    className="btn-primary"
                  >
                    <Save className="h-4 w-4 mr-2" />
                    {loading ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {activeTab === 'preferences' && (
            <div className="bg-white shadow rounded-lg">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">Preferences</h2>
                <p className="mt-1 text-sm text-gray-600">
                  Customize your application preferences
                </p>
              </div>
              <form onSubmit={handlePreferencesSubmit} className="p-6 space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Theme
                  </label>
                  <div className="space-y-2">
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="theme"
                        value="light"
                        checked={preferencesForm.preferences.theme === 'light'}
                        onChange={(e) => setPreferencesForm(prev => ({
                          ...prev,
                          preferences: { ...prev.preferences, theme: e.target.value }
                        }))}
                        className="mr-2"
                      />
                      Light
                    </label>
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="theme"
                        value="dark"
                        checked={preferencesForm.preferences.theme === 'dark'}
                        onChange={(e) => setPreferencesForm(prev => ({
                          ...prev,
                          preferences: { ...prev.preferences, theme: e.target.value }
                        }))}
                        className="mr-2"
                      />
                      Dark
                    </label>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Chat Settings
                  </label>
                  <div className="space-y-3">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={preferencesForm.preferences.chat?.streaming || false}
                        onChange={(e) => setPreferencesForm(prev => ({
                          ...prev,
                          preferences: {
                            ...prev.preferences,
                            chat: { ...prev.preferences.chat, streaming: e.target.checked }
                          }
                        }))}
                        className="mr-2"
                      />
                      Enable streaming responses
                    </label>
                    <div>
                      <label htmlFor="context_length" className="block text-sm text-gray-600">
                        Context Length
                      </label>
                      <input
                        type="number"
                        id="context_length"
                        min="1"
                        max="20"
                        value={preferencesForm.preferences.chat?.context_length || 5}
                        onChange={(e) => setPreferencesForm(prev => ({
                          ...prev,
                          preferences: {
                            ...prev.preferences,
                            chat: { ...prev.preferences.chat, context_length: parseInt(e.target.value) }
                          }
                        }))}
                        className="mt-1 input w-20"
                      />
                    </div>
                  </div>
                </div>

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={loading}
                    className="btn-primary"
                  >
                    <Save className="h-4 w-4 mr-2" />
                    {loading ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="bg-white shadow rounded-lg">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">Notifications</h2>
                <p className="mt-1 text-sm text-gray-600">
                  Manage your notification preferences
                </p>
              </div>
              <div className="p-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-gray-900">Email Notifications</h3>
                      <p className="text-sm text-gray-600">Receive notifications via email</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={preferencesForm.preferences.notifications?.email || false}
                        onChange={(e) => setPreferencesForm(prev => ({
                          ...prev,
                          preferences: {
                            ...prev.preferences,
                            notifications: { ...prev.preferences.notifications, email: e.target.checked }
                          }
                        }))}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-gray-900">Push Notifications</h3>
                      <p className="text-sm text-gray-600">Receive push notifications in browser</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={preferencesForm.preferences.notifications?.push || false}
                        onChange={(e) => setPreferencesForm(prev => ({
                          ...prev,
                          preferences: {
                            ...prev.preferences,
                            notifications: { ...prev.preferences.notifications, push: e.target.checked }
                          }
                        }))}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                    </label>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'integrations' && (
            <div className="bg-white shadow rounded-lg">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">Integrations</h2>
                <p className="mt-1 text-sm text-gray-600">
                  Manage your connected services and data synchronization
                </p>
              </div>
              <div className="p-6">
                <div className="space-y-6">
                  <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-center">
                      <Mail className="h-8 w-8 text-red-600 mr-3" />
                      <div>
                        <h3 className="text-sm font-medium text-gray-900">Google (Gmail & Calendar)</h3>
                        <p className="text-sm text-gray-600">
                          {user.has_google_access ? 'Connected' : 'Not connected'}
                        </p>
                      </div>
                    </div>
                    <button className="btn-secondary">
                      {user.has_google_access ? 'Manage' : 'Connect'}
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-center">
                      <Globe className="h-8 w-8 text-orange-600 mr-3" />
                      <div>
                        <h3 className="text-sm font-medium text-gray-900">HubSpot CRM</h3>
                        <p className="text-sm text-gray-600">
                          {user.has_hubspot_access ? 'Connected' : 'Not connected'}
                        </p>
                      </div>
                    </div>
                    <button className="btn-secondary">
                      {user.has_hubspot_access ? 'Manage' : 'Connect'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Settings;