import { useState, useEffect, useCallback } from 'react';
import { useQuery, useQueryClient } from 'react-query';
import api from '../services/api';

interface DashboardData {
  metrics: any;
  health: any;
  businessMetrics: any;
  performance: any;
  alerts: any[];
  logs: any[];
}

export function useDashboardData(period: string = '24h') {
  const queryClient = useQueryClient();
  const [selectedPeriod, setSelectedPeriod] = useState(period);

  // Fetch dashboard metrics
  const { data: metrics, isLoading: metricsLoading, error: metricsError } = useQuery(
    ['dashboardMetrics', selectedPeriod],
    async () => {
      const response = await api.get(`/api/v1/dashboard/metrics?period=${selectedPeriod}`);
      return response.data;
    },
    {
      refetchInterval: 60000, // Refetch every minute
      staleTime: 30000, // Consider data stale after 30 seconds
    }
  );

  // Fetch system health
  const { data: health, isLoading: healthLoading, error: healthError } = useQuery(
    'systemHealth',
    async () => {
      const response = await api.get('/api/v1/dashboard/health');
      return response.data;
    },
    {
      refetchInterval: 30000, // Refetch every 30 seconds
      staleTime: 15000,
    }
  );

  // Fetch business metrics
  const { data: businessMetrics, isLoading: businessLoading, error: businessError } = useQuery(
    ['businessMetrics', selectedPeriod],
    async () => {
      const endDate = new Date();
      const startDate = new Date();
      
      switch (selectedPeriod) {
        case '1h':
          startDate.setHours(startDate.getHours() - 1);
          break;
        case '24h':
          startDate.setDate(startDate.getDate() - 1);
          break;
        case '7d':
          startDate.setDate(startDate.getDate() - 7);
          break;
        case '30d':
          startDate.setDate(startDate.getDate() - 30);
          break;
      }

      const response = await api.get('/api/v1/dashboard/business-metrics', {
        params: {
          start_date: startDate.toISOString(),
          end_date: endDate.toISOString(),
        },
      });
      return response.data;
    },
    {
      refetchInterval: 300000, // Refetch every 5 minutes
      staleTime: 120000,
    }
  );

  // Fetch performance metrics
  const { data: performance, isLoading: perfLoading, error: perfError } = useQuery(
    'performanceMetrics',
    async () => {
      const response = await api.get('/api/v1/dashboard/performance');
      return response.data;
    },
    {
      refetchInterval: 30000,
      staleTime: 15000,
    }
  );

  // Fetch alerts
  const { data: alerts, isLoading: alertsLoading, error: alertsError } = useQuery(
    'dashboardAlerts',
    async () => {
      const response = await api.get('/api/v1/dashboard/alerts', {
        params: {
          status: 'active',
          limit: 100,
        },
      });
      return response.data;
    },
    {
      refetchInterval: 10000, // Refetch every 10 seconds
      staleTime: 5000,
    }
  );

  // Fetch logs
  const { data: logs, isLoading: logsLoading, error: logsError } = useQuery(
    'dashboardLogs',
    async () => {
      const response = await api.get('/api/v1/dashboard/logs', {
        params: {
          limit: 100,
        },
      });
      return response.data;
    },
    {
      refetchInterval: 60000,
      staleTime: 30000,
    }
  );

  // Combined loading state
  const loading = metricsLoading || healthLoading || businessLoading || perfLoading || alertsLoading || logsLoading;

  // Combined error
  const error = metricsError || healthError || businessError || perfError || alertsError || logsError;

  // Refetch all data
  const refetch = useCallback(() => {
    queryClient.invalidateQueries('dashboardMetrics');
    queryClient.invalidateQueries('systemHealth');
    queryClient.invalidateQueries('businessMetrics');
    queryClient.invalidateQueries('performanceMetrics');
    queryClient.invalidateQueries('dashboardAlerts');
    queryClient.invalidateQueries('dashboardLogs');
  }, [queryClient]);

  // Export data
  const exportData = useCallback(async (dataType: string, format: string, dateRange: any) => {
    try {
      const response = await api.post('/api/v1/dashboard/export', {
        data_type: dataType,
        format: format,
        start_date: dateRange.startDate,
        end_date: dateRange.endDate,
      });
      return response.data;
    } catch (error) {
      console.error('Export failed:', error);
      throw error;
    }
  }, []);

  // Get top products
  const getTopProducts = useCallback(async (limit: number = 10, metric: string = 'revenue') => {
    try {
      const response = await api.get('/api/v1/dashboard/top-products', {
        params: { limit, metric },
      });
      return response.data;
    } catch (error) {
      console.error('Failed to fetch top products:', error);
      throw error;
    }
  }, []);

  // Get revenue breakdown
  const getRevenueBreakdown = useCallback(async (period: string = '30d') => {
    try {
      const response = await api.get('/api/v1/dashboard/revenue-breakdown', {
        params: { period },
      });
      return response.data;
    } catch (error) {
      console.error('Failed to fetch revenue breakdown:', error);
      throw error;
    }
  }, []);

  // Get metrics history for charts
  const getMetricsHistory = useCallback(async (metricType: string, period: string, interval: string) => {
    try {
      const response = await api.get('/api/v1/dashboard/metrics/history', {
        params: {
          metric_type: metricType,
          period,
          interval,
        },
      });
      return response.data;
    } catch (error) {
      console.error('Failed to fetch metrics history:', error);
      throw error;
    }
  }, []);

  // Acknowledge alert
  const acknowledgeAlert = useCallback(async (alertId: string) => {
    try {
      await api.put(`/api/v1/dashboard/alerts/${alertId}/acknowledge`);
      queryClient.invalidateQueries('dashboardAlerts');
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
      throw error;
    }
  }, [queryClient]);

  return {
    data: {
      ...metrics,
      health,
      businessMetrics,
      performance,
      alerts: alerts || [],
      logs: logs || [],
    },
    loading,
    error,
    refetch,
    exportData,
    getTopProducts,
    getRevenueBreakdown,
    getMetricsHistory,
    acknowledgeAlert,
    setSelectedPeriod,
    selectedPeriod,
  };
}