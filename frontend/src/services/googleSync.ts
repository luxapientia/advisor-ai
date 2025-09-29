/**
 * Google sync service for managing Gmail and Calendar synchronization.
 */

import api from './api';

export interface GoogleSyncStatus {
  status: 'none' | 'pending' | 'syncing' | 'completed' | 'error';
  needed: boolean;
  completed: boolean;
  has_google_access: boolean;
}

export interface GoogleSyncResponse {
  message: string;
}

class GoogleSyncService {
  /**
   * Get Google sync status for the current user.
   */
  async getSyncStatus(): Promise<GoogleSyncStatus> {
    const response = await api.get('/google/sync/status');
    return response.data;
  }

  /**
   * Start Google sync for the current user.
   */
  async startSync(): Promise<GoogleSyncResponse> {
    const response = await api.post('/google/sync/start');
    return response.data;
  }

  /**
   * Reset Google sync status to allow re-sync.
   */
  async resetSync(): Promise<GoogleSyncResponse> {
    const response = await api.post('/google/sync/reset');
    return response.data;
  }
}

export const googleSyncService = new GoogleSyncService();