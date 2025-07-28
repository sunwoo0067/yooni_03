import ReactNativeBiometrics, { BiometryType } from 'react-native-biometrics';
import * as Keychain from 'react-native-keychain';
import { Alert, Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { store } from '@store/index';
import { setAuthenticated, setUser } from '@store/slices/authSlice';
import { ApiService } from '@services/api/ApiService';
import { SecureStorage } from '@services/storage/SecureStorage';
import { AnalyticsService } from '@services/analytics/AnalyticsService';
import { CrashlyticsService } from '@services/crashlytics/CrashlyticsService';

const BIOMETRIC_ENABLED_KEY = '@BiometricEnabled';
const BIOMETRIC_CREDENTIALS_KEY = 'BiometricCredentials';

interface BiometricCredentials {
  username: string;
  password: string;
  refreshToken?: string;
}

export class BiometricService {
  private static rnBiometrics = new ReactNativeBiometrics();
  private static isInitialized = false;
  private static biometryType: BiometryType | null = null;

  static async initialize(): Promise<void> {
    if (this.isInitialized) return;

    try {
      const { available, biometryType } = await this.rnBiometrics.isSensorAvailable();
      
      if (available) {
        this.biometryType = biometryType as BiometryType;
        this.isInitialized = true;
        
        // Check if biometric is enabled for auto-login
        const isEnabled = await this.isBiometricEnabled();
        if (isEnabled) {
          // Try auto-login silently
          this.attemptBiometricLogin().catch(() => {
            // Silent fail - user will need to login manually
          });
        }
      }
    } catch (error) {
      console.error('Biometric initialization failed:', error);
      CrashlyticsService.recordError(error as Error, 'BiometricService.initialize');
    }
  }

  static async isBiometricAvailable(): Promise<boolean> {
    try {
      const { available } = await this.rnBiometrics.isSensorAvailable();
      return available;
    } catch (error) {
      console.error('Error checking biometric availability:', error);
      return false;
    }
  }

  static async getBiometryType(): Promise<string> {
    if (!this.biometryType) {
      const { biometryType } = await this.rnBiometrics.isSensorAvailable();
      this.biometryType = biometryType as BiometryType;
    }

    switch (this.biometryType) {
      case 'TouchID':
        return Platform.OS === 'ios' ? 'Touch ID' : 'Fingerprint';
      case 'FaceID':
        return 'Face ID';
      case 'Biometrics':
        return 'Biometrics';
      default:
        return 'Biometric Authentication';
    }
  }

  static async isBiometricEnabled(): Promise<boolean> {
    try {
      const enabled = await AsyncStorage.getItem(BIOMETRIC_ENABLED_KEY);
      return enabled === 'true';
    } catch (error) {
      console.error('Error checking biometric status:', error);
      return false;
    }
  }

  static async enableBiometric(credentials: BiometricCredentials): Promise<boolean> {
    try {
      const isAvailable = await this.isBiometricAvailable();
      if (!isAvailable) {
        Alert.alert('Biometric Not Available', 'Your device does not support biometric authentication.');
        return false;
      }

      const biometryType = await this.getBiometryType();
      
      const { success } = await this.rnBiometrics.simplePrompt({
        promptMessage: `Enable ${biometryType} for quick login?`,
        fallbackPromptMessage: 'Use passcode',
      });

      if (success) {
        // Store credentials securely
        await Keychain.setInternetCredentials(
          BIOMETRIC_CREDENTIALS_KEY,
          credentials.username,
          credentials.password,
          {
            accessible: Keychain.ACCESSIBLE.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
            service: 'com.yooni.dashboard',
          }
        );

        // Store refresh token separately if available
        if (credentials.refreshToken) {
          await SecureStorage.setItem('refreshToken', credentials.refreshToken);
        }

        // Enable biometric flag
        await AsyncStorage.setItem(BIOMETRIC_ENABLED_KEY, 'true');

        // Track analytics
        AnalyticsService.track('biometric_enabled', {
          biometry_type: biometryType,
        });

        return true;
      }

      return false;
    } catch (error) {
      console.error('Error enabling biometric:', error);
      CrashlyticsService.recordError(error as Error, 'BiometricService.enableBiometric');
      return false;
    }
  }

  static async disableBiometric(): Promise<void> {
    try {
      const biometryType = await this.getBiometryType();
      
      const { success } = await this.rnBiometrics.simplePrompt({
        promptMessage: `Disable ${biometryType}?`,
        fallbackPromptMessage: 'Use passcode',
      });

      if (success) {
        // Remove stored credentials
        await Keychain.resetInternetCredentials(BIOMETRIC_CREDENTIALS_KEY);
        await SecureStorage.removeItem('refreshToken');
        await AsyncStorage.setItem(BIOMETRIC_ENABLED_KEY, 'false');

        // Track analytics
        AnalyticsService.track('biometric_disabled', {
          biometry_type: biometryType,
        });
      }
    } catch (error) {
      console.error('Error disabling biometric:', error);
      CrashlyticsService.recordError(error as Error, 'BiometricService.disableBiometric');
    }
  }

  static async authenticate(reason?: string): Promise<boolean> {
    try {
      const isAvailable = await this.isBiometricAvailable();
      if (!isAvailable) {
        return false;
      }

      const biometryType = await this.getBiometryType();
      
      const { success, error } = await this.rnBiometrics.simplePrompt({
        promptMessage: reason || `Authenticate with ${biometryType}`,
        fallbackPromptMessage: 'Use passcode',
      });

      if (success) {
        AnalyticsService.track('biometric_auth_success', {
          biometry_type: biometryType,
        });
        return true;
      }

      if (error) {
        AnalyticsService.track('biometric_auth_failed', {
          biometry_type: biometryType,
          error: error,
        });
      }

      return false;
    } catch (error) {
      console.error('Biometric authentication failed:', error);
      CrashlyticsService.recordError(error as Error, 'BiometricService.authenticate');
      return false;
    }
  }

  static async attemptBiometricLogin(): Promise<boolean> {
    try {
      const isEnabled = await this.isBiometricEnabled();
      if (!isEnabled) {
        return false;
      }

      const authenticated = await this.authenticate('Login to Yooni Dashboard');
      if (!authenticated) {
        return false;
      }

      // Retrieve stored credentials
      const credentials = await Keychain.getInternetCredentials(BIOMETRIC_CREDENTIALS_KEY);
      if (!credentials) {
        // Credentials not found, disable biometric
        await this.disableBiometric();
        return false;
      }

      // Attempt login with stored credentials
      try {
        const response = await ApiService.login({
          email: credentials.username,
          password: credentials.password,
        });

        if (response.success) {
          // Update store
          store.dispatch(setUser(response.user));
          store.dispatch(setAuthenticated(true));

          // Update refresh token if new one received
          if (response.refreshToken) {
            await SecureStorage.setItem('refreshToken', response.refreshToken);
          }

          AnalyticsService.track('biometric_login_success');
          return true;
        }
      } catch (apiError) {
        // Login failed, credentials might be invalid
        console.error('Biometric login failed:', apiError);
        
        // Ask user if they want to disable biometric
        Alert.alert(
          'Login Failed',
          'Your saved credentials appear to be invalid. Would you like to disable biometric login?',
          [
            { text: 'Cancel', style: 'cancel' },
            {
              text: 'Disable',
              onPress: () => this.disableBiometric(),
              style: 'destructive',
            },
          ]
        );
      }

      return false;
    } catch (error) {
      console.error('Biometric login attempt failed:', error);
      CrashlyticsService.recordError(error as Error, 'BiometricService.attemptBiometricLogin');
      return false;
    }
  }

  static async updateStoredCredentials(credentials: BiometricCredentials): Promise<void> {
    try {
      const isEnabled = await this.isBiometricEnabled();
      if (!isEnabled) return;

      // Update stored credentials
      await Keychain.setInternetCredentials(
        BIOMETRIC_CREDENTIALS_KEY,
        credentials.username,
        credentials.password,
        {
          accessible: Keychain.ACCESSIBLE.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
          service: 'com.yooni.dashboard',
        }
      );

      if (credentials.refreshToken) {
        await SecureStorage.setItem('refreshToken', credentials.refreshToken);
      }
    } catch (error) {
      console.error('Error updating stored credentials:', error);
      CrashlyticsService.recordError(error as Error, 'BiometricService.updateStoredCredentials');
    }
  }

  static async createKeys(): Promise<boolean> {
    try {
      const { publicKey } = await this.rnBiometrics.createKeys();
      console.log('Biometric public key created:', publicKey);
      return true;
    } catch (error) {
      console.error('Error creating biometric keys:', error);
      return false;
    }
  }

  static async deleteKeys(): Promise<boolean> {
    try {
      const { keysDeleted } = await this.rnBiometrics.deleteKeys();
      return keysDeleted;
    } catch (error) {
      console.error('Error deleting biometric keys:', error);
      return false;
    }
  }
}