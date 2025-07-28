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
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Alert,
  LinearProgress,
  Tooltip,
  IconButton,
  useTheme,
} from '@mui/material';
import {
  CheckCircle,
  Error,
  Warning,
  Info,
  Storage,
  Memory,
  Speed,
  NetworkCheck,
  Cloud,
  Refresh,
} from '@mui/icons-material';
import { Radar, Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip as ChartTooltip,
  Legend,
} from 'chart.js';

// Register ChartJS components
ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  ChartTooltip,
  Legend
);

interface ServiceHealthProps {
  service: {
    name: string;
    status: string;
    response_time?: number;
    error_rate?: number;
    last_check: string;
  };
}

const ServiceHealth: React.FC<ServiceHealthProps> = ({ service }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle sx={{ color: 'success.main' }} />;
      case 'degraded':
        return <Warning sx={{ color: 'warning.main' }} />;
      case 'unhealthy':
        return <Error sx={{ color: 'error.main' }} />;
      default:
        return <Info sx={{ color: 'info.main' }} />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'degraded':
        return 'warning';
      case 'unhealthy':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <ListItem
      sx={{
        borderRadius: 1,
        mb: 1,
        bgcolor: 'background.paper',
        '&:hover': { bgcolor: 'action.hover' },
      }}
    >
      <ListItemIcon>{getStatusIcon(service.status)}</ListItemIcon>
      <ListItemText
        primary={service.name}
        secondary={
          <Box display="flex" gap={1} mt={0.5}>
            {service.response_time && (
              <Chip
                label={`${service.response_time}ms`}
                size="small"
                variant="outlined"
              />
            )}
            <Typography variant="caption" color="textSecondary">
              Last check: {new Date(service.last_check).toLocaleTimeString()}
            </Typography>
          </Box>
        }
      />
      <Chip
        label={service.status}
        color={getStatusColor(service.status) as any}
        size="small"
      />
    </ListItem>
  );
};

interface SystemHealthMonitorProps {
  data: any;
  loading: boolean;
}

const SystemHealthMonitor: React.FC<SystemHealthMonitorProps> = ({ data, loading }) => {
  const theme = useTheme();

  // Prepare resource usage chart data
  const resourceRadarData = {
    labels: ['CPU', 'Memory', 'Disk', 'Network'],
    datasets: [
      {
        label: 'Current Usage',
        data: [
          data?.system_resources?.cpu?.percent || 0,
          data?.system_resources?.memory?.percent || 0,
          data?.system_resources?.disk?.percent || 0,
          Math.min((data?.system_resources?.network?.bytes_sent || 0) / 1000000, 100), // Normalize to percentage
        ],
        backgroundColor: theme.palette.primary.main + '40',
        borderColor: theme.palette.primary.main,
        pointBackgroundColor: theme.palette.primary.main,
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: theme.palette.primary.main,
      },
    ],
  };

  const resourceChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        angleLines: {
          display: false,
        },
        suggestedMin: 0,
        suggestedMax: 100,
      },
    },
  };

  if (loading) {
    return (
      <Box>
        <Grid container spacing={3}>
          {[1, 2, 3, 4].map((i) => (
            <Grid item xs={12} md={6} key={i}>
              <Card>
                <CardContent>
                  <Skeleton variant="text" width="60%" />
                  <Skeleton variant="rectangular" height={200} sx={{ mt: 2 }} />
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  }

  const overallHealthColor = data?.status === 'healthy' ? 'success' : 'error';

  return (
    <Box>
      {/* Overall Health Status */}
      <Alert
        severity={data?.status === 'healthy' ? 'success' : 'error'}
        sx={{ mb: 3 }}
        action={
          <Tooltip title="Refresh health check">
            <IconButton size="small">
              <Refresh />
            </IconButton>
          </Tooltip>
        }
      >
        System Status: <strong>{data?.status?.toUpperCase()}</strong> - Last checked:{' '}
        {new Date(data?.last_check).toLocaleString()}
      </Alert>

      <Grid container spacing={3}>
        {/* Database Health */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Box display="flex" alignItems="center" mb={2}>
              <Storage sx={{ mr: 1 }} />
              <Typography variant="h6">Database Health</Typography>
            </Box>
            
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Box>
                  <Typography variant="body2" color="textSecondary">
                    Status
                  </Typography>
                  <Chip
                    label={data?.database?.status || 'Unknown'}
                    color={data?.database?.status === 'healthy' ? 'success' : 'error'}
                    size="small"
                  />
                </Box>
              </Grid>
              <Grid item xs={6}>
                <Box>
                  <Typography variant="body2" color="textSecondary">
                    Response Time
                  </Typography>
                  <Typography variant="h6">
                    {data?.database?.response_time || 0}ms
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12}>
                <Box>
                  <Typography variant="body2" color="textSecondary" gutterBottom>
                    Connection Pool
                  </Typography>
                  <Box display="flex" justifyContent="space-between" mb={1}>
                    <Typography variant="caption">
                      {data?.database?.connections || 0} / {data?.database?.max_connections || 100}
                    </Typography>
                    <Typography variant="caption">
                      {Math.round((data?.database?.connections / data?.database?.max_connections) * 100)}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={(data?.database?.connections / data?.database?.max_connections) * 100}
                    sx={{ height: 8, borderRadius: 4 }}
                  />
                </Box>
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Redis Health */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Box display="flex" alignItems="center" mb={2}>
              <Memory sx={{ mr: 1 }} />
              <Typography variant="h6">Redis Health</Typography>
            </Box>
            
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Box>
                  <Typography variant="body2" color="textSecondary">
                    Status
                  </Typography>
                  <Chip
                    label={data?.redis?.status || 'Unknown'}
                    color={data?.redis?.status === 'healthy' ? 'success' : 'error'}
                    size="small"
                  />
                </Box>
              </Grid>
              <Grid item xs={6}>
                <Box>
                  <Typography variant="body2" color="textSecondary">
                    Response Time
                  </Typography>
                  <Typography variant="h6">
                    {data?.redis?.response_time || 0}ms
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={6}>
                <Box>
                  <Typography variant="body2" color="textSecondary">
                    Memory Usage
                  </Typography>
                  <Typography variant="body1">
                    {data?.redis?.memory_usage || 'N/A'}
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={6}>
                <Box>
                  <Typography variant="body2" color="textSecondary">
                    Connected Clients
                  </Typography>
                  <Typography variant="body1">
                    {data?.redis?.connected_clients || 0}
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Internal Services */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Box display="flex" alignItems="center" mb={2}>
              <NetworkCheck sx={{ mr: 1 }} />
              <Typography variant="h6">Internal Services</Typography>
            </Box>
            <List dense>
              {data?.services?.map((service: any, index: number) => (
                <ServiceHealth key={index} service={service} />
              ))}
            </List>
          </Paper>
        </Grid>

        {/* External APIs */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Box display="flex" alignItems="center" mb={2}>
              <Cloud sx={{ mr: 1 }} />
              <Typography variant="h6">External APIs</Typography>
            </Box>
            <List dense>
              {data?.external_apis?.map((api: any, index: number) => (
                <ServiceHealth key={index} service={api} />
              ))}
            </List>
          </Paper>
        </Grid>

        {/* System Resources */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              System Resources
            </Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Box sx={{ height: 300 }}>
                  <Radar data={resourceRadarData} options={resourceChartOptions} />
                </Box>
              </Grid>
              <Grid item xs={12} md={6}>
                <Grid container spacing={2}>
                  {/* CPU Usage */}
                  <Grid item xs={12}>
                    <Box>
                      <Box display="flex" justifyContent="space-between" mb={1}>
                        <Typography variant="body2">
                          CPU Usage ({data?.system_resources?.cpu?.cores} cores)
                        </Typography>
                        <Typography variant="body2">
                          {data?.system_resources?.cpu?.percent}%
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={data?.system_resources?.cpu?.percent || 0}
                        sx={{
                          height: 8,
                          borderRadius: 4,
                          bgcolor: 'grey.200',
                          '& .MuiLinearProgress-bar': {
                            bgcolor: data?.system_resources?.cpu?.percent > 80 ? 'error.main' : 'primary.main',
                          },
                        }}
                      />
                    </Box>
                  </Grid>

                  {/* Memory Usage */}
                  <Grid item xs={12}>
                    <Box>
                      <Box display="flex" justifyContent="space-between" mb={1}>
                        <Typography variant="body2">
                          Memory Usage
                        </Typography>
                        <Typography variant="body2">
                          {data?.system_resources?.memory?.percent}% ({data?.system_resources?.memory?.available_gb}GB free)
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={data?.system_resources?.memory?.percent || 0}
                        sx={{
                          height: 8,
                          borderRadius: 4,
                          bgcolor: 'grey.200',
                          '& .MuiLinearProgress-bar': {
                            bgcolor: data?.system_resources?.memory?.percent > 85 ? 'error.main' : 'primary.main',
                          },
                        }}
                      />
                    </Box>
                  </Grid>

                  {/* Disk Usage */}
                  <Grid item xs={12}>
                    <Box>
                      <Box display="flex" justifyContent="space-between" mb={1}>
                        <Typography variant="body2">
                          Disk Usage
                        </Typography>
                        <Typography variant="body2">
                          {data?.system_resources?.disk?.percent}% ({data?.system_resources?.disk?.free_gb}GB free)
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={data?.system_resources?.disk?.percent || 0}
                        sx={{
                          height: 8,
                          borderRadius: 4,
                          bgcolor: 'grey.200',
                          '& .MuiLinearProgress-bar': {
                            bgcolor: data?.system_resources?.disk?.percent > 90 ? 'error.main' : 'primary.main',
                          },
                        }}
                      />
                    </Box>
                  </Grid>

                  {/* Network I/O */}
                  <Grid item xs={12}>
                    <Box>
                      <Typography variant="body2" color="textSecondary" gutterBottom>
                        Network I/O
                      </Typography>
                      <Box display="flex" gap={2}>
                        <Chip
                          label={`↑ ${(data?.system_resources?.network?.bytes_sent / 1024 / 1024).toFixed(2)} MB`}
                          size="small"
                          color="primary"
                        />
                        <Chip
                          label={`↓ ${(data?.system_resources?.network?.bytes_recv / 1024 / 1024).toFixed(2)} MB`}
                          size="small"
                          color="secondary"
                        />
                      </Box>
                    </Box>
                  </Grid>
                </Grid>
              </Grid>
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default SystemHealthMonitor;