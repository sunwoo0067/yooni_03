import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Grid,
  Paper,
  Typography,
  IconButton,
  Tabs,
  Tab,
  Alert,
  Snackbar,
  useTheme,
  useMediaQuery,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  AppBar,
  Toolbar,
  Badge,
  Menu,
  MenuItem,
  Divider,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Analytics as AnalyticsIcon,
  MonitorHeart as HealthIcon,
  Warning as AlertIcon,
  Article as LogIcon,
  Download as ExportIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  Menu as MenuIcon,
  Notifications as NotificationsIcon,
  Speed as PerformanceIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

// Import dashboard components
import MetricsOverview from './components/MetricsOverview';
import SystemHealthMonitor from './components/SystemHealthMonitor';
import BusinessMetrics from './components/BusinessMetrics';
import PerformanceMetrics from './components/PerformanceMetrics';
import AlertsPanel from './components/AlertsPanel';
import LogViewer from './components/LogViewer';
import RealtimeChart from './components/RealtimeChart';
import ExportDialog from './components/ExportDialog';

// WebSocket hook
import { useWebSocket } from '../../hooks/useWebSocket';
import { useDashboardData } from '../../hooks/useDashboardData';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`dashboard-tabpanel-${index}`}
      aria-labelledby={`dashboard-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const OperationsDashboard: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const isTablet = useMediaQuery(theme.breakpoints.down('md'));

  // State
  const [tabValue, setTabValue] = useState(0);
  const [drawerOpen, setDrawerOpen] = useState(!isMobile);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [alertsMenuAnchor, setAlertsMenuAnchor] = useState<null | HTMLElement>(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' as any });

  // Custom hooks
  const { data, loading, error, refetch } = useDashboardData();
  const { connected, metrics, alerts, subscribe, unsubscribe } = useWebSocket();

  // Subscribe to real-time updates
  useEffect(() => {
    if (connected) {
      subscribe(['dashboard', 'alerts', 'metrics']);
    }
    return () => {
      if (connected) {
        unsubscribe(['dashboard', 'alerts', 'metrics']);
      }
    };
  }, [connected, subscribe, unsubscribe]);

  // Handle tab change
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  // Handle drawer toggle
  const handleDrawerToggle = () => {
    setDrawerOpen(!drawerOpen);
  };

  // Handle export
  const handleExport = (type: string, format: string, dateRange: any) => {
    // Export logic here
    setSnackbar({ open: true, message: 'Export started...', severity: 'info' });
  };

  // Navigation items
  const navigationItems = [
    { text: 'Overview', icon: <DashboardIcon />, index: 0 },
    { text: 'System Health', icon: <HealthIcon />, index: 1 },
    { text: 'Business Metrics', icon: <AnalyticsIcon />, index: 2 },
    { text: 'Performance', icon: <PerformanceIcon />, index: 3 },
    { text: 'Alerts', icon: <AlertIcon />, index: 4 },
    { text: 'Logs', icon: <LogIcon />, index: 5 },
  ];

  const drawer = (
    <Box sx={{ width: 240 }}>
      <Toolbar>
        <Typography variant="h6" noWrap>
          Operations
        </Typography>
      </Toolbar>
      <Divider />
      <List>
        {navigationItems.map((item) => (
          <ListItem
            button
            key={item.text}
            selected={tabValue === item.index}
            onClick={() => setTabValue(item.index)}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.text} />
          </ListItem>
        ))}
      </List>
      <Divider />
      <List>
        <ListItem button onClick={() => setExportDialogOpen(true)}>
          <ListItemIcon>
            <ExportIcon />
          </ListItemIcon>
          <ListItemText primary="Export Data" />
        </ListItem>
        <ListItem button>
          <ListItemIcon>
            <SettingsIcon />
          </ListItemIcon>
          <ListItemText primary="Settings" />
        </ListItem>
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          width: { md: `calc(100% - ${drawerOpen ? 240 : 0}px)` },
          ml: { md: `${drawerOpen ? 240 : 0}px` },
          transition: theme.transitions.create(['margin', 'width'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, ...(drawerOpen && !isMobile && { display: 'none' }) }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            Dropshipping Operations Dashboard
          </Typography>
          
          {/* Connection Status */}
          <Box sx={{ display: 'flex', alignItems: 'center', mr: 2 }}>
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                bgcolor: connected ? 'success.main' : 'error.main',
                mr: 1,
              }}
            />
            <Typography variant="body2">
              {connected ? 'Connected' : 'Disconnected'}
            </Typography>
          </Box>

          {/* Refresh Button */}
          <IconButton color="inherit" onClick={() => refetch()}>
            <RefreshIcon />
          </IconButton>

          {/* Alerts */}
          <IconButton
            color="inherit"
            onClick={(e) => setAlertsMenuAnchor(e.currentTarget)}
          >
            <Badge badgeContent={alerts.length} color="error">
              <NotificationsIcon />
            </Badge>
          </IconButton>
        </Toolbar>
      </AppBar>

      {/* Side Drawer */}
      <Box
        component="nav"
        sx={{ width: { md: drawerOpen ? 240 : 0 }, flexShrink: { md: 0 } }}
      >
        {isMobile ? (
          <Drawer
            variant="temporary"
            open={drawerOpen}
            onClose={handleDrawerToggle}
            ModalProps={{ keepMounted: true }}
            sx={{
              '& .MuiDrawer-paper': { boxSizing: 'border-box', width: 240 },
            }}
          >
            {drawer}
          </Drawer>
        ) : (
          <Drawer
            variant="persistent"
            open={drawerOpen}
            sx={{
              '& .MuiDrawer-paper': { boxSizing: 'border-box', width: 240 },
            }}
          >
            {drawer}
          </Drawer>
        )}
      </Box>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { md: `calc(100% - ${drawerOpen ? 240 : 0}px)` },
          ml: { md: `${drawerOpen ? 240 : 0}px` },
          transition: theme.transitions.create(['margin', 'width'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
          mt: 8,
        }}
      >
        {/* Tab Panels */}
        <TabPanel value={tabValue} index={0}>
          <MetricsOverview data={data} loading={loading} realtime={metrics} />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <SystemHealthMonitor data={data?.health} loading={loading} />
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <BusinessMetrics data={data?.businessMetrics} loading={loading} />
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          <PerformanceMetrics data={data?.performance} loading={loading} />
        </TabPanel>

        <TabPanel value={tabValue} index={4}>
          <AlertsPanel alerts={alerts} />
        </TabPanel>

        <TabPanel value={tabValue} index={5}>
          <LogViewer />
        </TabPanel>
      </Box>

      {/* Alerts Menu */}
      <Menu
        anchorEl={alertsMenuAnchor}
        open={Boolean(alertsMenuAnchor)}
        onClose={() => setAlertsMenuAnchor(null)}
        PaperProps={{
          sx: { maxHeight: 400, width: 320 },
        }}
      >
        {alerts.length === 0 ? (
          <MenuItem disabled>No active alerts</MenuItem>
        ) : (
          alerts.slice(0, 5).map((alert: any) => (
            <MenuItem key={alert.id} onClick={() => {
              setTabValue(4);
              setAlertsMenuAnchor(null);
            }}>
              <Box>
                <Typography variant="body2" color={alert.severity === 'critical' ? 'error' : 'warning'}>
                  {alert.message}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {new Date(alert.created_at).toLocaleString()}
                </Typography>
              </Box>
            </MenuItem>
          ))
        )}
        {alerts.length > 5 && (
          <>
            <Divider />
            <MenuItem onClick={() => {
              setTabValue(4);
              setAlertsMenuAnchor(null);
            }}>
              View all alerts ({alerts.length})
            </MenuItem>
          </>
        )}
      </Menu>

      {/* Export Dialog */}
      <ExportDialog
        open={exportDialogOpen}
        onClose={() => setExportDialogOpen(false)}
        onExport={handleExport}
      />

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default OperationsDashboard;