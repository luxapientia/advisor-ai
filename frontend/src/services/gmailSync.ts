/**
 * Gmail sync service for managing email synchronization.
 */

import api from './api';

export interface GmailSyncStatus {
  status: 'none' | 'pending' | 'syncing' | 'completed' | 'error';
  needed: boolean;
  completed: boolean;
  has_google_access: boolean;
}

export interface GmailSyncResponse {
  message: string;
}

class GmailSyncService {
  /**
   * Get Gmail sync status for the current user.
   */
  async getSyncStatus(): Promise<GmailSyncStatus> {
    const response = await api.get('/gmail/sync/status');
    return response.data;
  }

  /**
   * Start Gmail sync for the current user.
   */
  async startSync(): Promise<GmailSyncResponse> {
    const response = await api.post('/gmail/sync/start');
    return response.data;
  }

  /**
   * Reset Gmail sync status to allow re-sync.
   */
  async resetSync(): Promise<GmailSyncResponse> {
    const response = await api.post('/gmail/sync/reset');
    return response.data;
  }
}

export const gmailSyncService = new GmailSyncService();