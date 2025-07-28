import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  ScrollView,
  RefreshControl,
  StyleSheet,
  Alert,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { Container } from '@components/common/Container';
import { Header } from '@components/common/Header';
import { MetricCard } from '@components/metrics/MetricCard';
import { RevenueChart } from '@components/charts/RevenueChart';
import { OrderStatusChart } from '@components/charts/OrderStatusChart';
import { SystemHealthCard } from '@components/metrics/SystemHealthCard';
import { RecentAlerts } from '@components/alerts/RecentAlerts';
import { LoadingView } from '@components/common/LoadingView';
import { ErrorView } from '@components/common/ErrorView';
import { useTheme } from '@hooks/useTheme';
import { useWebSocket } from '@hooks/useWebSocket';
import { useAppSelector } from '@hooks/redux';
import { DashboardService } from '@services/api/DashboardService';
import { formatCurrency, formatNumber } from '@utils/formatters';
import { hapticFeedback } from '@utils/haptics';
import type { DashboardMetrics } from '@types/dashboard';

export const DashboardScreen: React.FC = () => {
  const navigation = useNavigation();
  const { theme } = useTheme();
  const { t } = useTranslation();
  const [refreshing, setRefreshing] = useState(false);
  
  // WebSocket for real-time updates
  const { subscribe, unsubscribe } = useWebSocket();
  const [realtimeMetrics, setRealtimeMetrics] = useState<Partial<DashboardMetrics>>({});

  // Get user preferences
  const { currency, dateFormat } = useAppSelector((state) => state.user.preferences);

  // Fetch dashboard data
  const {
    data: dashboardData,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['dashboard', 'overview'],
    queryFn: DashboardService.getOverview,
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Merge API data with real-time updates
  const metrics = React.useMemo(() => {
    if (!dashboardData) return null;
    return {
      ...dashboardData,
      ...realtimeMetrics,
    };
  }, [dashboardData, realtimeMetrics]);

  // Subscribe to real-time updates
  useEffect(() => {
    const channel = 'dashboard.metrics';
    
    const handleMetricsUpdate = (data: Partial<DashboardMetrics>) => {
      setRealtimeMetrics(prev => ({ ...prev, ...data }));
    };

    subscribe(channel, handleMetricsUpdate);

    return () => {
      unsubscribe(channel, handleMetricsUpdate);
    };
  }, [subscribe, unsubscribe]);

  // Pull to refresh handler
  const onRefresh = useCallback(async () => {
    hapticFeedback('light');
    setRefreshing(true);
    try {
      await refetch();
    } catch (error) {
      Alert.alert(t('error'), t('dashboard.refreshError'));
    } finally {
      setRefreshing(false);
    }
  }, [refetch, t]);

  // Navigate to detail screens
  const navigateToMetrics = useCallback(() => {
    hapticFeedback('light');
    navigation.navigate('Metrics' as never);
  }, [navigation]);

  const navigateToAlerts = useCallback(() => {
    hapticFeedback('light');
    navigation.navigate('Alerts' as never);
  }, [navigation]);

  const navigateToSystemHealth = useCallback(() => {
    hapticFeedback('light');
    navigation.navigate('SystemHealth' as never);
  }, [navigation]);

  if (isLoading && !refreshing) {
    return <LoadingView message={t('dashboard.loading')} />;
  }

  if (isError && !metrics) {
    return (
      <ErrorView
        message={t('dashboard.loadError')}
        onRetry={refetch}
      />
    );
  }

  return (
    <Container>
      <Header
        title={t('dashboard.title')}
        showNotifications
        showSettings
      />
      
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={theme.colors.primary}
          />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Key Metrics */}
        <View style={styles.metricsGrid}>
          <MetricCard
            title={t('dashboard.totalRevenue')}
            value={formatCurrency(metrics?.revenue.total || 0, currency)}
            change={metrics?.revenue.changePercent || 0}
            icon="trending-up"
            onPress={navigateToMetrics}
          />
          
          <MetricCard
            title={t('dashboard.totalOrders')}
            value={formatNumber(metrics?.orders.total || 0)}
            change={metrics?.orders.changePercent || 0}
            icon="shopping-cart"
            onPress={navigateToMetrics}
          />
          
          <MetricCard
            title={t('dashboard.activeProducts')}
            value={formatNumber(metrics?.products.active || 0)}
            subtitle={`${metrics?.products.outOfStock || 0} ${t('dashboard.outOfStock')}`}
            icon="package"
            onPress={navigateToMetrics}
          />
          
          <MetricCard
            title={t('dashboard.conversionRate')}
            value={`${metrics?.conversion.rate || 0}%`}
            change={metrics?.conversion.changePercent || 0}
            icon="percent"
            onPress={navigateToMetrics}
          />
        </View>

        {/* Revenue Chart */}
        <View style={styles.chartContainer}>
          <RevenueChart
            data={metrics?.revenueChart || []}
            period="week"
            currency={currency}
          />
        </View>

        {/* Order Status Distribution */}
        <View style={styles.chartContainer}>
          <OrderStatusChart
            data={metrics?.orderStatusDistribution || []}
          />
        </View>

        {/* System Health */}
        <SystemHealthCard
          health={metrics?.systemHealth}
          onPress={navigateToSystemHealth}
        />

        {/* Recent Alerts */}
        <RecentAlerts
          alerts={metrics?.recentAlerts || []}
          onViewAll={navigateToAlerts}
        />
      </ScrollView>
    </Container>
  );
};

const styles = StyleSheet.create({
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 20,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 16,
    paddingTop: 16,
    gap: 12,
  },
  chartContainer: {
    marginHorizontal: 16,
    marginTop: 20,
  },
});