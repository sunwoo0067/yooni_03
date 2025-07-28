import React, { useEffect } from 'react';
import {
  SafeAreaProvider,
  initialWindowMetrics,
} from 'react-native-safe-area-context';
import { NavigationContainer } from '@react-navigation/native';
import { Provider } from 'react-redux';
import { PersistGate } from 'redux-persist/integration/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SplashScreen from 'react-native-splash-screen';
import CodePush from 'react-native-code-push';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { enableScreens } from 'react-native-screens';

import { store, persistor } from '@store/index';
import { RootNavigator } from '@navigation/RootNavigator';
import { NotificationService } from '@services/notification/NotificationService';
import { BiometricService } from '@services/auth/BiometricService';
import { ThemeProvider } from '@hooks/useTheme';
import { ErrorBoundary } from '@components/common/ErrorBoundary';
import { LoadingOverlay } from '@components/common/LoadingOverlay';
import { NetworkStatus } from '@components/common/NetworkStatus';
import { navigationRef } from '@navigation/NavigationService';
import { initializeAnalytics } from '@services/analytics/AnalyticsService';
import { initializeCrashlytics } from '@services/crashlytics/CrashlyticsService';
import { checkForUpdates } from '@services/codepush/CodePushService';
import { setupDeepLinking } from '@navigation/DeepLinkingService';

// Enable screens for better performance
enableScreens();

// Create a QueryClient instance
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes
    },
    mutations: {
      retry: 1,
    },
  },
});

const App: React.FC = () => {
  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Initialize services
        await Promise.all([
          initializeAnalytics(),
          initializeCrashlytics(),
          NotificationService.initialize(),
          BiometricService.initialize(),
          setupDeepLinking(),
        ]);

        // Check for CodePush updates
        await checkForUpdates();

        // Hide splash screen
        SplashScreen.hide();
      } catch (error) {
        console.error('App initialization failed:', error);
        SplashScreen.hide();
      }
    };

    initializeApp();

    // Clean up
    return () => {
      NotificationService.cleanup();
    };
  }, []);

  return (
    <ErrorBoundary>
      <GestureHandlerRootView style={{ flex: 1 }}>
        <Provider store={store}>
          <PersistGate loading={<LoadingOverlay />} persistor={persistor}>
            <QueryClientProvider client={queryClient}>
              <SafeAreaProvider initialMetrics={initialWindowMetrics}>
                <ThemeProvider>
                  <NavigationContainer ref={navigationRef}>
                    <NetworkStatus />
                    <RootNavigator />
                  </NavigationContainer>
                </ThemeProvider>
              </SafeAreaProvider>
            </QueryClientProvider>
          </PersistGate>
        </Provider>
      </GestureHandlerRootView>
    </ErrorBoundary>
  );
};

// CodePush configuration
const codePushOptions = {
  checkFrequency: CodePush.CheckFrequency.ON_APP_RESUME,
  installMode: CodePush.InstallMode.ON_NEXT_RESTART,
  minimumBackgroundDuration: 60 * 10, // 10 minutes
};

export default CodePush(codePushOptions)(App);