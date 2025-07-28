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
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  useTheme,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import {
  Speed,
  Timer,
  DataUsage,
  CloudQueue,
  TrendingUp,
  TrendingDown,
  AccessTime,
} from '@mui/icons-material';
import { Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
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
  Title,
  Tooltip,
  Legend
);

interface PerformanceMetricsProps {
  data: any;
  loading: boolean;
}

const PerformanceMetrics: React.FC<PerformanceMetricsProps> = ({ data, loading }) => {
  const theme = useTheme();
  const [timeRange, setTimeRange] = useState('1h');
  const [selectedService, setSelectedService] = useState('all');

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
  const responseTimeData = {
    labels: data?.response_times?.map((rt: any) => new Date(rt.timestamp).toLocaleTimeString()) || [],
    datasets: [
      {
        label: 'Response Time (ms)',
        data: data?.response_times?.map((rt: any) => rt.value) || [],
        borderColor: theme.palette.primary.main,
        backgroundColor: theme.palette.primary.main + '20',
        tension: 0.4,
      },
    ],
  };

  const throughputData = {
    labels: Object.keys(data?.throughput || {}),
    datasets: [
      {
        label: 'Requests per Minute',
        data: Object.values(data?.throughput || {}),
        backgroundColor: theme.palette.secondary.main,
        borderColor: theme.palette.secondary.dark,
        borderWidth: 1,
      },
    ],
  };

  const errorRateData = {
    labels: Object.keys(data?.error_rates || {}),
    datasets: [
      {
        label: 'Error Rate (%)',
        data: Object.values(data?.error_rates || {}).map((rate: any) => parseFloat(rate)),
        borderColor: theme.palette.error.main,
        backgroundColor: theme.palette.error.main + '20',
        tension: 0.4,
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

  // Calculate performance score
  const calculatePerformanceScore = () => {
    const avgResponseTime = data?.response_times?.reduce((acc: number, rt: any) => acc + rt.value, 0) / data?.response_times?.length || 0;
    const avgErrorRate = Object.values(data?.error_rates || {}).reduce((acc: any, rate: any) => acc + parseFloat(rate), 0) / Object.keys(data?.error_rates || {}).length || 0;
    
    let score = 100;
    // Deduct points for slow response times
    if (avgResponseTime > 1000) score -= 20;
    else if (avgResponseTime > 500) score -= 10;
    else if (avgResponseTime > 200) score -= 5;
    
    // Deduct points for error rates
    if (avgErrorRate > 5) score -= 30;
    else if (avgErrorRate > 2) score -= 20;
    else if (avgErrorRate > 1) score -= 10;
    
    return Math.max(0, score);
  };

  const performanceScore = calculatePerformanceScore();

  return (
    <Box>
      {/* Performance Score Alert */}
      <Alert 
        severity={performanceScore >= 80 ? 'success' : performanceScore >= 60 ? 'warning' : 'error'}
        sx={{ mb: 3 }}
      >
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">
            Performance Score: {performanceScore}/100
          </Typography>
          <ToggleButtonGroup
            value={timeRange}
            exclusive
            onChange={(e, value) => value && setTimeRange(value)}
            size="small"
          >
            <ToggleButton value="1h">1H</ToggleButton>
            <ToggleButton value="24h">24H</ToggleButton>
            <ToggleButton value="7d">7D</ToggleButton>
          </ToggleButtonGroup>
        </Box>
      </Alert>

      {/* Summary Cards */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography color="textSecondary" variant="body2" gutterBottom>
                    Avg Response Time
                  </Typography>
                  <Typography variant="h4">
                    {data?.response_times?.reduce((acc: number, rt: any) => acc + rt.value, 0) / data?.response_times?.length || 0}ms
                  </Typography>
                  <Box display="flex" alignItems="center" mt={1}>
                    <TrendingDown sx={{ color: 'success.main', fontSize: 16, mr: 0.5 }} />
                    <Typography variant="body2" color="success.main">
                      -12% from last hour
                    </Typography>
                  </Box>
                </Box>
                <Timer sx={{ fontSize: 40, color: theme.palette.primary.main, opacity: 0.3 }} />
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
                    Throughput
                  </Typography>
                  <Typography variant="h4">
                    {Object.values(data?.throughput || {}).reduce((acc: any, val: any) => acc + val, 0)}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    requests/min
                  </Typography>
                </Box>
                <DataUsage sx={{ fontSize: 40, color: theme.palette.secondary.main, opacity: 0.3 }} />
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
                    Error Rate
                  </Typography>
                  <Typography variant="h4">
                    {Object.values(data?.error_rates || {}).reduce((acc: any, rate: any) => acc + parseFloat(rate), 0) / Object.keys(data?.error_rates || {}).length || 0}%
                  </Typography>
                  <Box display="flex" alignItems="center" mt={1}>
                    <TrendingUp sx={{ color: 'error.main', fontSize: 16, mr: 0.5 }} />
                    <Typography variant="body2" color="error.main">
                      +0.5% from baseline
                    </Typography>
                  </Box>
                </Box>
                <CloudQueue sx={{ fontSize: 40, color: theme.palette.error.main, opacity: 0.3 }} />
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
                    Uptime
                  </Typography>
                  <Typography variant="h4">
                    99.95%
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Last 30 days
                  </Typography>
                </Box>
                <AccessTime sx={{ fontSize: 40, color: theme.palette.success.main, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts */}
      <Grid container spacing={3} mb={3}>
        {/* Response Time Trend */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: 350 }}>
            <Typography variant="h6" gutterBottom>
              Response Time Trend
            </Typography>
            <Box sx={{ height: 280 }}>
              <Line data={responseTimeData} options={chartOptions} />
            </Box>
          </Paper>
        </Grid>

        {/* Throughput */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: 350 }}>
            <Typography variant="h6" gutterBottom>
              Throughput by Service
            </Typography>
            <Box sx={{ height: 280 }}>
              <Bar data={throughputData} options={chartOptions} />
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Service Performance Table */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">
            Service Performance Details
          </Typography>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Service</InputLabel>
            <Select
              value={selectedService}
              label="Service"
              onChange={(e) => setSelectedService(e.target.value)}
            >
              <MenuItem value="all">All Services</MenuItem>
              <MenuItem value="api">API Gateway</MenuItem>
              <MenuItem value="database">Database</MenuItem>
              <MenuItem value="redis">Redis Cache</MenuItem>
              <MenuItem value="ai">AI Service</MenuItem>
            </Select>
          </FormControl>
        </Box>
        
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Service</TableCell>
                <TableCell>Avg Response Time</TableCell>
                <TableCell>P95 Response Time</TableCell>
                <TableCell>P99 Response Time</TableCell>
                <TableCell>Error Rate</TableCell>
                <TableCell>Throughput</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data?.service_specific?.map((service: any) => (
                <TableRow key={service.name}>
                  <TableCell>{service.name}</TableCell>
                  <TableCell>{service.avg_response_time}ms</TableCell>
                  <TableCell>{service.p95_response_time}ms</TableCell>
                  <TableCell>{service.p99_response_time}ms</TableCell>
                  <TableCell>
                    <Chip
                      label={`${service.error_rate}%`}
                      size="small"
                      color={service.error_rate > 5 ? 'error' : service.error_rate > 2 ? 'warning' : 'success'}
                    />
                  </TableCell>
                  <TableCell>{service.throughput} req/min</TableCell>
                  <TableCell>
                    <Chip
                      label={service.status}
                      size="small"
                      color={service.status === 'healthy' ? 'success' : 'error'}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Resource Usage */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Resource Usage
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={3}>
            <Box>
              <Typography variant="body2" color="textSecondary" gutterBottom>
                CPU Usage
              </Typography>
              <Box display="flex" alignItems="center" mb={1}>
                <Typography variant="h5">
                  {data?.resource_usage?.cpu_percent || 0}%
                </Typography>
                <Typography variant="body2" color="textSecondary" ml={1}>
                  / 100%
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={data?.resource_usage?.cpu_percent || 0}
                sx={{
                  height: 10,
                  borderRadius: 5,
                  bgcolor: 'grey.200',
                  '& .MuiLinearProgress-bar': {
                    bgcolor: data?.resource_usage?.cpu_percent > 80 ? 'error.main' : 'primary.main',
                  },
                }}
              />
            </Box>
          </Grid>

          <Grid item xs={12} md={3}>
            <Box>
              <Typography variant="body2" color="textSecondary" gutterBottom>
                Memory Usage
              </Typography>
              <Box display="flex" alignItems="center" mb={1}>
                <Typography variant="h5">
                  {data?.resource_usage?.memory_percent || 0}%
                </Typography>
                <Typography variant="body2" color="textSecondary" ml={1}>
                  / 100%
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={data?.resource_usage?.memory_percent || 0}
                sx={{
                  height: 10,
                  borderRadius: 5,
                  bgcolor: 'grey.200',
                  '& .MuiLinearProgress-bar': {
                    bgcolor: data?.resource_usage?.memory_percent > 85 ? 'error.main' : 'primary.main',
                  },
                }}
              />
            </Box>
          </Grid>

          <Grid item xs={12} md={3}>
            <Box>
              <Typography variant="body2" color="textSecondary" gutterBottom>
                Disk Usage
              </Typography>
              <Box display="flex" alignItems="center" mb={1}>
                <Typography variant="h5">
                  {data?.resource_usage?.disk_percent || 0}%
                </Typography>
                <Typography variant="body2" color="textSecondary" ml={1}>
                  / 100%
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={data?.resource_usage?.disk_percent || 0}
                sx={{
                  height: 10,
                  borderRadius: 5,
                  bgcolor: 'grey.200',
                  '& .MuiLinearProgress-bar': {
                    bgcolor: data?.resource_usage?.disk_percent > 90 ? 'error.main' : 'primary.main',
                  },
                }}
              />
            </Box>
          </Grid>

          <Grid item xs={12} md={3}>
            <Box>
              <Typography variant="body2" color="textSecondary" gutterBottom>
                Network I/O
              </Typography>
              <Box display="flex" gap={1}>
                <Chip
                  label={`↑ ${((data?.resource_usage?.network_io?.bytes_sent || 0) / 1024 / 1024).toFixed(2)} MB/s`}
                  size="small"
                  color="primary"
                />
                <Chip
                  label={`↓ ${((data?.resource_usage?.network_io?.bytes_recv || 0) / 1024 / 1024).toFixed(2)} MB/s`}
                  size="small"
                  color="secondary"
                />
              </Box>
            </Box>
          </Grid>
        </Grid>
      </Paper>
    </Box>
  );
};

export default PerformanceMetrics;