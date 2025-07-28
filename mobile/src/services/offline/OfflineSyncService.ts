import NetInfo, { NetInfoState } from '@react-native-community/netinfo';
import { MMKV } from 'react-native-mmkv';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { ApiService } from '@services/api/ApiService';
import { store } from '@store/index';
import { setSyncStatus, addPendingSync } from '@store/slices/syncSlice';
import { AnalyticsService } from '@services/analytics/AnalyticsService';
import { CrashlyticsService } from '@services/crashlytics/CrashlyticsService';

// Initialize MMKV for fast storage
const storage = new MMKV({
  id: 'offline-sync-storage',
  encryptionKey: 'yooni-offline-sync-key',
});

interface SyncRequest {
  id: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  endpoint: string;
  data?: any;
  timestamp: number;
  retryCount: number;
  priority: 'high' | 'medium' | 'low';
}

interface CacheEntry {
  data: any;
  timestamp: number;
  ttl: number;
}

export class OfflineSyncService {
  private static isOnline = true;
  private static syncQueue: SyncRequest[] = [];
  private static isSyncing = false;
  private static syncTimer: NodeJS.Timeout | null = null;
  private static networkListener: (() => void) | null = null;

  // Constants
  private static readonly SYNC_QUEUE_KEY = 'offline_sync_queue';
  private static readonly CACHE_PREFIX = 'cache_';
  private static readonly MAX_RETRY_COUNT = 3;
  private static readonly RETRY_DELAY_BASE = 1000; // 1 second
  private static readonly SYNC_BATCH_SIZE = 10;
  private static readonly DEFAULT_CACHE_TTL = 5 * 60 * 1000; // 5 minutes

  static async initialize(): Promise<void> {
    try {
      // Load sync queue from storage
      await this.loadSyncQueue();

      // Setup network listener
      this.networkListener = NetInfo.addEventListener(this.handleNetworkChange.bind(this));

      // Check initial network state
      const state = await NetInfo.fetch();
      this.handleNetworkChange(state);

      // Start periodic sync check
      this.startPeriodicSync();

      AnalyticsService.track('offline_sync_initialized');
    } catch (error) {
      console.error('OfflineSync initialization failed:', error);
      CrashlyticsService.recordError(error as Error, 'OfflineSyncService.initialize');
    }
  }

  static cleanup(): void {
    if (this.networkListener) {
      this.networkListener();
      this.networkListener = null;
    }

    if (this.syncTimer) {
      clearInterval(this.syncTimer);
      this.syncTimer = null;
    }
  }

  private static handleNetworkChange(state: NetInfoState): void {
    const wasOffline = !this.isOnline;
    this.isOnline = state.isConnected || false;

    store.dispatch(setSyncStatus({
      isOnline: this.isOnline,
      isSyncing: this.isSyncing,
      pendingCount: this.syncQueue.length,
    }));

    // If we just came online, trigger sync
    if (wasOffline && this.isOnline && this.syncQueue.length > 0) {
      this.processSyncQueue();
    }

    AnalyticsService.track('network_state_changed', {
      is_online: this.isOnline,
      connection_type: state.type,
    });
  }

  private static startPeriodicSync(): void {
    this.syncTimer = setInterval(() => {
      if (this.isOnline && this.syncQueue.length > 0 && !this.isSyncing) {
        this.processSyncQueue();
      }
    }, 30000); // Check every 30 seconds
  }

  private static async loadSyncQueue(): Promise<void> {
    try {
      const queueJson = await AsyncStorage.getItem(this.SYNC_QUEUE_KEY);
      if (queueJson) {
        this.syncQueue = JSON.parse(queueJson);
        
        // Update store with pending count
        store.dispatch(setSyncStatus({
          pendingCount: this.syncQueue.length,
        }));
      }
    } catch (error) {
      console.error('Error loading sync queue:', error);
      this.syncQueue = [];
    }
  }

  private static async saveSyncQueue(): Promise<void> {
    try {
      await AsyncStorage.setItem(this.SYNC_QUEUE_KEY, JSON.stringify(this.syncQueue));
    } catch (error) {
      console.error('Error saving sync queue:', error);
    }
  }

  static async addToSyncQueue(request: Omit<SyncRequest, 'id' | 'timestamp' | 'retryCount'>): Promise<void> {
    const syncRequest: SyncRequest = {
      ...request,
      id: `sync_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      retryCount: 0,
    };

    this.syncQueue.push(syncRequest);
    await this.saveSyncQueue();

    store.dispatch(addPendingSync(syncRequest));
    store.dispatch(setSyncStatus({
      pendingCount: this.syncQueue.length,
    }));

    // If online, process immediately
    if (this.isOnline && !this.isSyncing) {
      this.processSyncQueue();
    }
  }

  private static async processSyncQueue(): Promise<void> {
    if (this.isSyncing || this.syncQueue.length === 0) return;

    this.isSyncing = true;
    store.dispatch(setSyncStatus({ isSyncing: true }));

    try {
      // Sort queue by priority and timestamp
      const sortedQueue = [...this.syncQueue].sort((a, b) => {
        const priorityWeight = { high: 0, medium: 1, low: 2 };
        if (priorityWeight[a.priority] !== priorityWeight[b.priority]) {
          return priorityWeight[a.priority] - priorityWeight[b.priority];
        }
        return a.timestamp - b.timestamp;
      });

      // Process in batches
      const batch = sortedQueue.slice(0, this.SYNC_BATCH_SIZE);
      
      for (const request of batch) {
        try {
          await this.processSingleRequest(request);
          
          // Remove from queue
          this.syncQueue = this.syncQueue.filter(r => r.id !== request.id);
        } catch (error) {
          console.error(`Sync request failed: ${request.id}`, error);
          
          // Handle retry logic
          request.retryCount++;
          
          if (request.retryCount >= this.MAX_RETRY_COUNT) {
            // Max retries reached, remove from queue
            this.syncQueue = this.syncQueue.filter(r => r.id !== request.id);
            
            AnalyticsService.track('sync_request_failed', {
              endpoint: request.endpoint,
              method: request.method,
              retry_count: request.retryCount,
            });
          }
        }
      }

      await this.saveSyncQueue();
    } finally {
      this.isSyncing = false;
      store.dispatch(setSyncStatus({
        isSyncing: false,
        pendingCount: this.syncQueue.length,
      }));

      // Continue processing if more items in queue
      if (this.syncQueue.length > 0) {
        setTimeout(() => this.processSyncQueue(), this.RETRY_DELAY_BASE);
      }
    }
  }

  private static async processSingleRequest(request: SyncRequest): Promise<void> {
    const delay = this.RETRY_DELAY_BASE * Math.pow(2, request.retryCount);
    await new Promise(resolve => setTimeout(resolve, delay));

    switch (request.method) {
      case 'GET':
        await ApiService.get(request.endpoint);
        break;
      case 'POST':
        await ApiService.post(request.endpoint, request.data);
        break;
      case 'PUT':
        await ApiService.put(request.endpoint, request.data);
        break;
      case 'DELETE':
        await ApiService.delete(request.endpoint);
        break;
    }

    AnalyticsService.track('sync_request_completed', {
      endpoint: request.endpoint,
      method: request.method,
      retry_count: request.retryCount,
    });
  }

  // Cache management
  static setCacheItem(key: string, data: any, ttl?: number): void {
    const cacheKey = `${this.CACHE_PREFIX}${key}`;
    const cacheEntry: CacheEntry = {
      data,
      timestamp: Date.now(),
      ttl: ttl || this.DEFAULT_CACHE_TTL,
    };
    
    storage.set(cacheKey, JSON.stringify(cacheEntry));
  }

  static getCacheItem<T>(key: string): T | null {
    const cacheKey = `${this.CACHE_PREFIX}${key}`;
    const cached = storage.getString(cacheKey);
    
    if (!cached) return null;

    try {
      const cacheEntry: CacheEntry = JSON.parse(cached);
      const now = Date.now();
      
      // Check if cache is expired
      if (now - cacheEntry.timestamp > cacheEntry.ttl) {
        storage.delete(cacheKey);
        return null;
      }
      
      return cacheEntry.data as T;
    } catch (error) {
      console.error('Error parsing cache:', error);
      storage.delete(cacheKey);
      return null;
    }
  }

  static clearCache(): void {
    const keys = storage.getAllKeys();
    const cacheKeys = keys.filter(key => key.startsWith(this.CACHE_PREFIX));
    cacheKeys.forEach(key => storage.delete(key));
    
    AnalyticsService.track('cache_cleared', {
      items_count: cacheKeys.length,
    });
  }

  static async clearAllData(): Promise<void> {
    try {
      // Clear sync queue
      this.syncQueue = [];
      await AsyncStorage.removeItem(this.SYNC_QUEUE_KEY);
      
      // Clear all cache
      this.clearCache();
      
      // Update store
      store.dispatch(setSyncStatus({
        pendingCount: 0,
      }));
      
      AnalyticsService.track('offline_data_cleared');
    } catch (error) {
      console.error('Error clearing offline data:', error);
      CrashlyticsService.recordError(error as Error, 'OfflineSyncService.clearAllData');
    }
  }

  // Utility methods
  static isNetworkAvailable(): boolean {
    return this.isOnline;
  }

  static getPendingSyncCount(): number {
    return this.syncQueue.length;
  }

  static async forceSyncNow(): Promise<void> {
    if (this.isOnline && !this.isSyncing) {
      await this.processSyncQueue();
    }
  }
}