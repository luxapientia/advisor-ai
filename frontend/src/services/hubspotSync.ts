/**
 * HubSpot sync service for managing CRM synchronization.
 */

import api from './api';

export interface HubSpotSyncStatus {
  status: 'none' | 'pending' | 'syncing' | 'completed' | 'error';
  needed: boolean;
  completed: boolean;
  has_hubspot_access: boolean;
}

export interface HubSpotSyncResponse {
  message: string;
}

class HubSpotSyncService {
  /**
   * Get HubSpot sync status for the current user.
   */
  async getSyncStatus(): Promise<HubSpotSyncStatus> {
    const response = await api.get('/hubspot/sync/status');
    return response.data;
  }

  /**
   * Start HubSpot sync for the current user.
   */
  async startSync(): Promise<HubSpotSyncResponse> {
    const response = await api.post('/hubspot/sync/start');
    return response.data;
  }

  /**
   * Reset HubSpot sync status to allow re-sync.
   */
  async resetSync(): Promise<HubSpotSyncResponse> {
    const response = await api.post('/hubspot/sync/reset');
    return response.data;
  }
}

export const hubspotSyncService = new HubSpotSyncService();