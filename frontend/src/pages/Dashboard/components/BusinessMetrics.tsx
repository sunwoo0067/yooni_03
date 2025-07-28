import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Skeleton,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  useTheme,
} from '@mui/material';
import {
  TrendingUp,
  Category,
  People,
  ShoppingCart,
  AttachMoney,
} from '@mui/icons-material';
import { Line, Bar, Pie } from 'react-chartjs-2';
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

interface BusinessMetricsProps {
  data: any;
  loading: boolean;
}

const BusinessMetrics: React.FC<BusinessMetricsProps> = ({ data, loading }) => {
  const theme = useTheme();
  const [selectedMetric, setSelectedMetric] = useState('revenue');

  if (loading) {
    return (
      <Box>
        <Grid container spacing={3}>
          {[1, 2, 3, 4].map((i) => (
            <Grid item xs={12} md={6} key={i}>
              <Skeleton variant="rectangular" height={300} />
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  }

  // Prepare chart data
  const dailyRevenueData = {
    labels: data?.daily_revenue?.map((d: any) => d.date) || [],
    datasets: [
      {
        label: 'Revenue',
        data: data?.daily_revenue?.map((d: any) => d.revenue) || [],
        borderColor: theme.palette.primary.main,
        backgroundColor: theme.palette.primary.main + '20',
        tension: 0.4,
      },
      {
        label: 'Orders',
        data: data?.daily_revenue?.map((d: any) => d.orders) || [],
        borderColor: theme.palette.secondary.main,
        backgroundColor: theme.palette.secondary.main + '20',
        tension: 0.4,
        yAxisID: 'y1',
      },
    ],
  };

  const categoryData = {
    labels: data?.top_categories?.map((c: any) => c.category) || [],
    datasets: [
      {
        label: 'Revenue by Category',
        data: data?.top_categories?.map((c: any) => c.revenue) || [],
        backgroundColor: [
          theme.palette.primary.main,
          theme.palette.secondary.main,
          theme.palette.success.main,
          theme.palette.warning.main,
          theme.palette.info.main,
          theme.palette.error.main,
        ],
      },
    ],
  };

  const conversionFunnelData = {
    labels: ['Visitors', 'Product Views', 'Add to Cart', 'Checkout', 'Purchase'],
    datasets: [
      {
        label: 'Conversion Funnel',
        data: [10000, 6000, 3000, 1500, 1200], // Mock data
        backgroundColor: theme.palette.primary.main,
        borderColor: theme.palette.primary.dark,
        borderWidth: 1,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
      },
      y1: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        grid: {
          drawOnChartArea: false,
        },
      },
    },
  };

  const pieChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right' as const,
      },
    },
  };

  return (
    <Box>
      {/* Summary Cards */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography color="textSecondary" variant="body2" gutterBottom>
                    Total Customers
                  </Typography>
                  <Typography variant="h4">
                    {data?.customer_metrics?.total_customers || 0}
                  </Typography>
                  <Typography variant="body2" color="success.main">
                    +{data?.customer_metrics?.new_customers || 0} new
                  </Typography>
                </Box>
                <People sx={{ fontSize: 40, color: theme.palette.primary.main, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography color="textSecondary" variant="body2" gutterBottom>
                    Repeat Rate
                  </Typography>
                  <Typography variant="h4">
                    {data?.customer_metrics?.repeat_rate || 0}%
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Customer retention
                  </Typography>
                </Box>
                <TrendingUp sx={{ fontSize: 40, color: theme.palette.success.main, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography color="textSecondary" variant="body2" gutterBottom>
                    Conversion Rate
                  </Typography>
                  <Typography variant="h4">
                    {data?.conversion_rate || 0}%
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Visitor to customer
                  </Typography>
                </Box>
                <ShoppingCart sx={{ fontSize: 40, color: theme.palette.secondary.main, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography color="textSecondary" variant="body2" gutterBottom>
                    Avg. Customer Value
                  </Typography>
                  <Typography variant="h4">
                    ₩{((data?.customer_metrics?.total_revenue || 0) / (data?.customer_metrics?.total_customers || 1)).toLocaleString()}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Lifetime value
                  </Typography>
                </Box>
                <AttachMoney sx={{ fontSize: 40, color: theme.palette.warning.main, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts */}
      <Grid container spacing={3} mb={3}>
        {/* Revenue & Orders Trend */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Revenue & Orders Trend
            </Typography>
            <Box sx={{ height: 320 }}>
              <Line data={dailyRevenueData} options={chartOptions} />
            </Box>
          </Paper>
        </Grid>

        {/* Category Performance */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Top Categories
            </Typography>
            <Box sx={{ height: 320 }}>
              <Pie data={categoryData} options={pieChartOptions} />
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Conversion Funnel */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: 350 }}>
            <Typography variant="h6" gutterBottom>
              Conversion Funnel
            </Typography>
            <Box sx={{ height: 280 }}>
              <Bar
                data={conversionFunnelData}
                options={{
                  ...chartOptions,
                  indexAxis: 'y' as const,
                  scales: {
                    x: {
                      beginAtZero: true,
                    },
                  },
                }}
              />
            </Box>
          </Paper>
        </Grid>

        {/* Top Products Table */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: 350, overflow: 'auto' }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6">
                Top Products
              </Typography>
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <Select
                  value={selectedMetric}
                  onChange={(e) => setSelectedMetric(e.target.value)}
                >
                  <MenuItem value="revenue">By Revenue</MenuItem>
                  <MenuItem value="orders">By Orders</MenuItem>
                  <MenuItem value="views">By Views</MenuItem>
                </Select>
              </FormControl>
            </Box>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Product</TableCell>
                    <TableCell>Category</TableCell>
                    <TableCell align="right">Revenue</TableCell>
                    <TableCell align="right">Orders</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data?.top_products?.slice(0, 5).map((product: any, index: number) => (
                    <TableRow key={index}>
                      <TableCell>{product.name}</TableCell>
                      <TableCell>
                        <Chip label={product.category} size="small" />
                      </TableCell>
                      <TableCell align="right">
                        ₩{product.revenue.toLocaleString()}
                      </TableCell>
                      <TableCell align="right">{product.orders}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>
      </Grid>

      {/* Platform Performance */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Platform Performance Comparison
        </Typography>
        <Grid container spacing={2}>
          {data?.platform_comparison?.map((platform: any) => (
            <Grid item xs={12} sm={6} md={3} key={platform.name}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle2" color="textSecondary">
                    {platform.name}
                  </Typography>
                  <Typography variant="h6">
                    ₩{platform.revenue.toLocaleString()}
                  </Typography>
                  <Box display="flex" justifyContent="space-between" mt={1}>
                    <Chip
                      label={`${platform.orders} orders`}
                      size="small"
                      variant="outlined"
                    />
                    <Typography variant="body2" color={platform.growth > 0 ? 'success.main' : 'error.main'}>
                      {platform.growth > 0 ? '+' : ''}{platform.growth}%
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Paper>
    </Box>
  );
};

export default BusinessMetrics;