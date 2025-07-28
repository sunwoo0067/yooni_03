import React from 'react';
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  Skeleton,
  Chip,
  LinearProgress,
  useTheme,
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  ShoppingCart,
  Inventory,
  AttachMoney,
  People,
  Speed,
  Error,
} from '@mui/icons-material';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: React.ReactNode;
  color: string;
  loading?: boolean;
  subtitle?: string;
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  change,
  icon,
  color,
  loading,
  subtitle,
}) => {
  const theme = useTheme();

  if (loading) {
    return (
      <Card sx={{ height: '100%' }}>
        <CardContent>
          <Skeleton variant="text" width="60%" />
          <Skeleton variant="text" width="40%" height={40} />
          <Skeleton variant="text" width="80%" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      sx={{
        height: '100%',
        background: `linear-gradient(135deg, ${color}15 0%, ${color}05 100%)`,
        borderTop: `3px solid ${color}`,
      }}
    >
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box>
            <Typography color="textSecondary" gutterBottom variant="body2">
              {title}
            </Typography>
            <Typography variant="h4" component="div">
              {value}
            </Typography>
            {subtitle && (
              <Typography variant="caption" color="textSecondary">
                {subtitle}
              </Typography>
            )}
            {change !== undefined && (
              <Box display="flex" alignItems="center" mt={1}>
                {change >= 0 ? (
                  <TrendingUp sx={{ color: 'success.main', fontSize: 20, mr: 0.5 }} />
                ) : (
                  <TrendingDown sx={{ color: 'error.main', fontSize: 20, mr: 0.5 }} />
                )}
                <Typography
                  variant="body2"
                  color={change >= 0 ? 'success.main' : 'error.main'}
                >
                  {Math.abs(change)}%
                </Typography>
              </Box>
            )}
          </Box>
          <Box
            sx={{
              backgroundColor: color,
              borderRadius: '50%',
              p: 1.5,
              color: 'white',
            }}
          >
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};

interface MetricsOverviewProps {
  data: any;
  loading: boolean;
  realtime: any;
}

const MetricsOverview: React.FC<MetricsOverviewProps> = ({ data, loading, realtime }) => {
  const theme = useTheme();

  // Prepare chart data
  const revenueChartData = {
    labels: data?.revenue?.daily?.map((d: any) => d.date) || [],
    datasets: [
      {
        label: 'Revenue',
        data: data?.revenue?.daily?.map((d: any) => d.revenue) || [],
        borderColor: theme.palette.primary.main,
        backgroundColor: theme.palette.primary.main + '20',
        tension: 0.4,
      },
    ],
  };

  const platformChartData = {
    labels: Object.keys(data?.platforms || {}),
    datasets: [
      {
        data: Object.values(data?.platforms || {}).map((p: any) => p.revenue),
        backgroundColor: [
          theme.palette.primary.main,
          theme.palette.secondary.main,
          theme.palette.success.main,
          theme.palette.warning.main,
        ],
      },
    ],
  };

  const orderStatusData = {
    labels: ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled'],
    datasets: [
      {
        label: 'Orders',
        data: [
          data?.orders?.pending || 0,
          data?.orders?.processing || 0,
          data?.orders?.shipped || 0,
          data?.orders?.delivered || 0,
          data?.orders?.cancelled || 0,
        ],
        backgroundColor: [
          theme.palette.warning.main,
          theme.palette.info.main,
          theme.palette.primary.main,
          theme.palette.success.main,
          theme.palette.error.main,
        ],
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
    },
  };

  return (
    <Box>
      {/* Key Metrics */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Total Revenue"
            value={`₩${data?.revenue?.total?.toLocaleString() || 0}`}
            change={data?.revenue?.growth_rate}
            icon={<AttachMoney />}
            color={theme.palette.primary.main}
            loading={loading}
            subtitle={data?.period || '24h'}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Total Orders"
            value={data?.orders?.total || 0}
            change={data?.orders?.growth_rate}
            icon={<ShoppingCart />}
            color={theme.palette.secondary.main}
            loading={loading}
            subtitle={`AOV: ₩${data?.revenue?.average_order_value?.toLocaleString() || 0}`}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Active Products"
            value={data?.products?.active || 0}
            icon={<Inventory />}
            color={theme.palette.success.main}
            loading={loading}
            subtitle={`${data?.products?.out_of_stock || 0} out of stock`}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="API Performance"
            value={`${data?.api_performance?.avg_response_time || 0}ms`}
            icon={<Speed />}
            color={theme.palette.info.main}
            loading={loading}
            subtitle={`${data?.api_performance?.requests_per_minute || 0} req/min`}
          />
        </Grid>
      </Grid>

      {/* Charts Row */}
      <Grid container spacing={3} mb={3}>
        {/* Revenue Trend */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Revenue Trend
            </Typography>
            {loading ? (
              <Skeleton variant="rectangular" height={320} />
            ) : (
              <Box sx={{ height: 320 }}>
                <Line data={revenueChartData} options={chartOptions} />
              </Box>
            )}
          </Paper>
        </Grid>

        {/* Platform Distribution */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Revenue by Platform
            </Typography>
            {loading ? (
              <Skeleton variant="circular" width={250} height={250} />
            ) : (
              <Box sx={{ height: 320, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                <Box sx={{ width: 250, height: 250 }}>
                  <Doughnut data={platformChartData} options={chartOptions} />
                </Box>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Status Overview */}
      <Grid container spacing={3}>
        {/* Order Status */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: 350 }}>
            <Typography variant="h6" gutterBottom>
              Order Status Distribution
            </Typography>
            {loading ? (
              <Skeleton variant="rectangular" height={270} />
            ) : (
              <Box sx={{ height: 270 }}>
                <Bar data={orderStatusData} options={chartOptions} />
              </Box>
            )}
          </Paper>
        </Grid>

        {/* System Status */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: 350 }}>
            <Typography variant="h6" gutterBottom>
              System Status
            </Typography>
            {loading ? (
              <Box>
                <Skeleton variant="text" height={40} />
                <Skeleton variant="text" height={40} />
                <Skeleton variant="text" height={40} />
              </Box>
            ) : (
              <Box>
                {/* Error Rate */}
                <Box mb={3}>
                  <Box display="flex" justifyContent="space-between" mb={1}>
                    <Typography variant="body2">Error Rate</Typography>
                    <Typography variant="body2" color={data?.error_rate > 5 ? 'error' : 'success'}>
                      {data?.error_rate || 0}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={Math.min(data?.error_rate || 0, 100)}
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      bgcolor: 'grey.200',
                      '& .MuiLinearProgress-bar': {
                        bgcolor: data?.error_rate > 5 ? 'error.main' : 'success.main',
                      },
                    }}
                  />
                </Box>

                {/* Uptime */}
                <Box mb={3}>
                  <Box display="flex" justifyContent="space-between" mb={1}>
                    <Typography variant="body2">System Uptime</Typography>
                    <Typography variant="body2" color="success">
                      {data?.api_performance?.uptime || 99.9}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={data?.api_performance?.uptime || 99.9}
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      bgcolor: 'grey.200',
                      '& .MuiLinearProgress-bar': {
                        bgcolor: 'success.main',
                      },
                    }}
                  />
                </Box>

                {/* Active Alerts */}
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="body2">Active Alerts</Typography>
                  <Chip
                    label={data?.alerts_count || 0}
                    color={data?.alerts_count > 0 ? 'warning' : 'default'}
                    size="small"
                  />
                </Box>

                {/* AI Usage */}
                <Box>
                  <Typography variant="body2" gutterBottom>
                    AI Service Usage
                  </Typography>
                  <Box display="flex" gap={1} flexWrap="wrap">
                    {Object.entries(data?.ai_usage?.by_service || {}).map(([service, usage]: any) => (
                      <Chip
                        key={service}
                        label={`${service}: ${usage.calls}`}
                        size="small"
                        variant="outlined"
                      />
                    ))}
                  </Box>
                </Box>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Real-time Metrics Bar */}
      {realtime && (
        <Box
          sx={{
            position: 'fixed',
            bottom: 0,
            left: 0,
            right: 0,
            bgcolor: 'background.paper',
            borderTop: 1,
            borderColor: 'divider',
            p: 2,
          }}
        >
          <Grid container spacing={2} alignItems="center">
            <Grid item>
              <Typography variant="body2" color="textSecondary">
                Real-time:
              </Typography>
            </Grid>
            <Grid item>
              <Chip
                label={`${realtime.requests_per_minute} req/min`}
                size="small"
                color="primary"
              />
            </Grid>
            <Grid item>
              <Chip
                label={`${realtime.active_users} active users`}
                size="small"
                color="secondary"
              />
            </Grid>
            <Grid item>
              <Chip
                label={`${realtime.recent_orders} recent orders`}
                size="small"
                color="success"
              />
            </Grid>
            <Grid item>
              <Chip
                label={`${realtime.error_rate}% errors`}
                size="small"
                color={realtime.error_rate > 5 ? 'error' : 'default'}
              />
            </Grid>
          </Grid>
        </Box>
      )}
    </Box>
  );
};

export default MetricsOverview;