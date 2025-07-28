import messaging, {
  FirebaseMessagingTypes,
} from '@react-native-firebase/messaging';
import notifee, {
  AndroidChannel,
  AndroidImportance,
  AndroidNotificationSetting,
  AuthorizationStatus,
  EventType,
  Notification,
} from '@notifee/react-native';
import { Platform, Alert } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { store } from '@store/index';
import { addNotification, updateBadgeCount } from '@store/slices/notificationSlice';
import { ApiService } from '@services/api/ApiService';
import { NavigationService } from '@navigation/NavigationService';
import { AnalyticsService } from '@services/analytics/AnalyticsService';
import { CrashlyticsService } from '@services/crashlytics/CrashlyticsService';
import { hapticFeedback } from '@utils/haptics';

const FCM_TOKEN_KEY = '@FcmToken';

interface NotificationHandler {
  (notification: Notification): void;
}

export class NotificationService {
  private static isInitialized = false;
  private static fcmToken: string | null = null;
  private static unsubscribeOnMessage: (() => void) | null = null;
  private static unsubscribeOnTokenRefresh: (() => void) | null = null;
  private static notificationHandlers: Map<string, NotificationHandler> = new Map();

  // Notification channels
  static readonly CHANNELS = {
    ALERTS: {
      id: 'alerts',
      name: 'System Alerts',
      importance: AndroidImportance.HIGH,
      sound: 'alert_sound',
      vibration: true,
      badge: true,
    },
    ORDERS: {
      id: 'orders',
      name: 'Order Updates',
      importance: AndroidImportance.DEFAULT,
      sound: 'default',
      vibration: true,
      badge: true,
    },
    MARKETING: {
      id: 'marketing',
      name: 'Marketing & Promotions',
      importance: AndroidImportance.LOW,
      sound: null,
      vibration: false,
      badge: false,
    },
  };

  static async initialize(): Promise<void> {
    if (this.isInitialized) return;

    try {
      // Request permissions
      const hasPermission = await this.requestPermissions();
      if (!hasPermission) {
        console.log('Notification permissions not granted');
        return;
      }

      // Create notification channels (Android)
      if (Platform.OS === 'android') {
        await this.createNotificationChannels();
      }

      // Get or refresh FCM token
      await this.setupFCMToken();

      // Setup message handlers
      this.setupMessageHandlers();

      // Setup Notifee handlers
      this.setupNotifeeHandlers();

      // Check initial notification (app opened from notification)
      await this.checkInitialNotification();

      this.isInitialized = true;
      AnalyticsService.track('notifications_initialized');
    } catch (error) {
      console.error('Notification initialization failed:', error);
      CrashlyticsService.recordError(error as Error, 'NotificationService.initialize');
    }
  }

  static cleanup(): void {
    if (this.unsubscribeOnMessage) {
      this.unsubscribeOnMessage();
      this.unsubscribeOnMessage = null;
    }

    if (this.unsubscribeOnTokenRefresh) {
      this.unsubscribeOnTokenRefresh();
      this.unsubscribeOnTokenRefresh = null;
    }

    this.notificationHandlers.clear();
  }

  private static async requestPermissions(): Promise<boolean> {
    try {
      const authStatus = await messaging().requestPermission();
      const enabled =
        authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
        authStatus === messaging.AuthorizationStatus.PROVISIONAL;

      if (enabled) {
        // Also request Notifee permissions for local notifications
        const settings = await notifee.requestPermission();
        
        if (settings.authorizationStatus >= AuthorizationStatus.AUTHORIZED) {
          return true;
        }
      }

      return false;
    } catch (error) {
      console.error('Error requesting permissions:', error);
      return false;
    }
  }

  private static async createNotificationChannels(): Promise<void> {
    for (const channel of Object.values(this.CHANNELS)) {
      await notifee.createChannel({
        id: channel.id,
        name: channel.name,
        importance: channel.importance,
        sound: channel.sound || undefined,
        vibration: channel.vibration,
        badge: channel.badge,
      } as AndroidChannel);
    }
  }

  private static async setupFCMToken(): Promise<void> {
    try {
      // Get token
      const token = await messaging().getToken();
      this.fcmToken = token;

      // Check if token changed
      const savedToken = await AsyncStorage.getItem(FCM_TOKEN_KEY);
      if (savedToken !== token) {
        await AsyncStorage.setItem(FCM_TOKEN_KEY, token);
        await this.registerTokenWithServer(token);
      }

      // Setup token refresh handler
      this.unsubscribeOnTokenRefresh = messaging().onTokenRefresh(async (newToken) => {
        this.fcmToken = newToken;
        await AsyncStorage.setItem(FCM_TOKEN_KEY, newToken);
        await this.registerTokenWithServer(newToken);
      });
    } catch (error) {
      console.error('Error setting up FCM token:', error);
    }
  }

  private static async registerTokenWithServer(token: string): Promise<void> {
    try {
      await ApiService.post('/notifications/register', {
        token,
        platform: Platform.OS,
        device_info: {
          os_version: Platform.Version,
          app_version: '1.0.0', // Get from your app config
        },
      });

      AnalyticsService.track('fcm_token_registered');
    } catch (error) {
      console.error('Error registering FCM token:', error);
      CrashlyticsService.recordError(error as Error, 'NotificationService.registerToken');
    }
  }

  private static setupMessageHandlers(): void {
    // Foreground messages
    this.unsubscribeOnMessage = messaging().onMessage(async (remoteMessage) => {
      await this.handleRemoteMessage(remoteMessage, true);
    });

    // Background/Quit messages
    messaging().setBackgroundMessageHandler(async (remoteMessage) => {
      await this.handleRemoteMessage(remoteMessage, false);
    });
  }

  private static setupNotifeeHandlers(): void {
    // Handle notification interactions
    notifee.onForegroundEvent(async ({ type, detail }) => {
      switch (type) {
        case EventType.DISMISSED:
          await this.handleNotificationDismissed(detail.notification!);
          break;
        case EventType.PRESS:
          await this.handleNotificationPress(detail.notification!);
          break;
        case EventType.ACTION_PRESS:
          await this.handleNotificationAction(detail.notification!, detail.pressAction!.id);
          break;
      }
    });

    // Background event handler
    notifee.onBackgroundEvent(async ({ type, detail }) => {
      if (type === EventType.PRESS && detail.notification) {
        await this.handleNotificationPress(detail.notification);
      }
    });
  }

  private static async handleRemoteMessage(
    remoteMessage: FirebaseMessagingTypes.RemoteMessage,
    isAppInForeground: boolean
  ): Promise<void> {
    try {
      const { notification, data } = remoteMessage;
      
      if (!notification) return;

      // Create local notification
      const notifeeNotification: Notification = {
        id: remoteMessage.messageId,
        title: notification.title || 'Yooni Dashboard',
        body: notification.body || '',
        data: data || {},
        android: {
          channelId: data?.channel || this.CHANNELS.ALERTS.id,
          smallIcon: 'ic_notification',
          largeIcon: notification.android?.imageUrl,
          sound: data?.sound || 'default',
          pressAction: {
            id: 'default',
          },
        },
        ios: {
          sound: data?.sound || 'default',
          badge: notification.ios?.badge ? Number(notification.ios.badge) : undefined,
        },
      };

      // Add custom actions if specified
      if (data?.actions) {
        try {
          const actions = JSON.parse(data.actions);
          notifeeNotification.android!.actions = actions;
          notifeeNotification.ios!.categoryId = data.categoryId;
        } catch (error) {
          console.error('Error parsing notification actions:', error);
        }
      }

      // Store in Redux
      store.dispatch(addNotification({
        id: remoteMessage.messageId!,
        title: notification.title || '',
        body: notification.body || '',
        data: data || {},
        timestamp: Date.now(),
        read: false,
      }));

      // Update badge count
      if (Platform.OS === 'ios' && notification.ios?.badge) {
        store.dispatch(updateBadgeCount(Number(notification.ios.badge)));
        notifee.setBadgeCount(Number(notification.ios.badge));
      }

      // Show notification if app is in foreground
      if (isAppInForeground) {
        hapticFeedback('notification');
        await notifee.displayNotification(notifeeNotification);
      }

      // Track analytics
      AnalyticsService.track('notification_received', {
        notification_id: remoteMessage.messageId,
        channel: data?.channel,
        is_foreground: isAppInForeground,
      });

      // Call custom handlers
      const handler = this.notificationHandlers.get(data?.type || 'default');
      if (handler) {
        handler(notifeeNotification);
      }
    } catch (error) {
      console.error('Error handling remote message:', error);
      CrashlyticsService.recordError(error as Error, 'NotificationService.handleRemoteMessage');
    }
  }

  private static async handleNotificationPress(notification: Notification): Promise<void> {
    hapticFeedback('light');
    
    // Navigate based on notification data
    const { data } = notification;
    
    if (data?.navigate_to) {
      NavigationService.navigate(data.navigate_to as any, data.navigate_params);
    } else if (data?.deep_link) {
      NavigationService.handleDeepLink(data.deep_link);
    }

    // Mark as read
    if (data?.notification_id) {
      await ApiService.put(`/notifications/${data.notification_id}/read`);
    }

    AnalyticsService.track('notification_opened', {
      notification_id: notification.id,
      navigate_to: data?.navigate_to,
    });
  }

  private static async handleNotificationAction(
    notification: Notification,
    actionId: string
  ): Promise<void> {
    hapticFeedback('light');
    
    const { data } = notification;

    // Handle predefined actions
    switch (actionId) {
      case 'mark_read':
        if (data?.notification_id) {
          await ApiService.put(`/notifications/${data.notification_id}/read`);
        }
        break;
      
      case 'view_details':
        if (data?.navigate_to) {
          NavigationService.navigate(data.navigate_to as any, data.navigate_params);
        }
        break;
      
      default:
        // Custom action handling
        if (data?.action_endpoint) {
          await ApiService.post(data.action_endpoint, { action: actionId });
        }
    }

    AnalyticsService.track('notification_action', {
      notification_id: notification.id,
      action_id: actionId,
    });
  }

  private static async handleNotificationDismissed(notification: Notification): Promise<void> {
    AnalyticsService.track('notification_dismissed', {
      notification_id: notification.id,
    });
  }

  private static async checkInitialNotification(): Promise<void> {
    try {
      // Check if app was opened from a notification
      const initialNotification = await notifee.getInitialNotification();
      
      if (initialNotification) {
        await this.handleNotificationPress(initialNotification.notification);
      }
    } catch (error) {
      console.error('Error checking initial notification:', error);
    }
  }

  // Public methods
  static async showLocalNotification(
    title: string,
    body: string,
    data?: any,
    channelId?: string
  ): Promise<void> {
    try {
      await notifee.displayNotification({
        title,
        body,
        data,
        android: {
          channelId: channelId || this.CHANNELS.ALERTS.id,
          smallIcon: 'ic_notification',
          pressAction: {
            id: 'default',
          },
        },
      });

      hapticFeedback('notification');
    } catch (error) {
      console.error('Error showing local notification:', error);
    }
  }

  static async scheduleNotification(
    notification: Notification,
    timestamp: number
  ): Promise<string> {
    try {
      const trigger = {
        type: notifee.TriggerType.TIMESTAMP,
        timestamp,
      };

      return await notifee.createTriggerNotification(notification, trigger);
    } catch (error) {
      console.error('Error scheduling notification:', error);
      throw error;
    }
  }

  static async cancelNotification(notificationId: string): Promise<void> {
    await notifee.cancelNotification(notificationId);
  }

  static async cancelAllNotifications(): Promise<void> {
    await notifee.cancelAllNotifications();
  }

  static async getBadgeCount(): Promise<number> {
    if (Platform.OS === 'ios') {
      return await notifee.getBadgeCount();
    }
    return 0;
  }

  static async setBadgeCount(count: number): Promise<void> {
    if (Platform.OS === 'ios') {
      await notifee.setBadgeCount(count);
      store.dispatch(updateBadgeCount(count));
    }
  }

  static registerNotificationHandler(type: string, handler: NotificationHandler): void {
    this.notificationHandlers.set(type, handler);
  }

  static unregisterNotificationHandler(type: string): void {
    this.notificationHandlers.delete(type);
  }

  static async requestNotificationSettings(): Promise<void> {
    if (Platform.OS === 'android') {
      await notifee.openNotificationSettings();
    } else {
      Alert.alert(
        'Notification Settings',
        'Would you like to open notification settings?',
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Open Settings',
            onPress: () => notifee.openNotificationSettings(),
          },
        ]
      );
    }
  }
}