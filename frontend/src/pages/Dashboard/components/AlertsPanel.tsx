import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tooltip,
  Alert,
  Collapse,
  useTheme,
  Divider,
  Badge,
} from '@mui/material';
import {
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  CheckCircle,
  Cancel,
  ExpandMore,
  ExpandLess,
  FilterList,
  Refresh,
  NotificationsActive,
  NotificationsOff,
} from '@mui/icons-material';
import { format } from 'date-fns';

interface Alert {
  id: string;
  type: string;
  severity: 'critical' | 'warning' | 'info';
  message: string;
  source: string;
  status: 'active' | 'acknowledged' | 'resolved';
  created_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
  metadata?: any;
}

interface AlertsPanelProps {
  alerts: Alert[];
}

const AlertsPanel: React.FC<AlertsPanelProps> = ({ alerts: initialAlerts }) => {
  const theme = useTheme();
  const [alerts, setAlerts] = useState<Alert[]>(initialAlerts);
  const [filter, setFilter] = useState({ severity: 'all', status: 'all' });
  const [expandedAlert, setExpandedAlert] = useState<string | null>(null);
  const [acknowledgeDialog, setAcknowledgeDialog] = useState<{ open: boolean; alert: Alert | null }>({
    open: false,
    alert: null,
  });
  const [resolveDialog, setResolveDialog] = useState<{ open: boolean; alert: Alert | null; resolution: string }>({
    open: false,
    alert: null,
    resolution: '',
  });
  const [muteNotifications, setMuteNotifications] = useState(false);

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <ErrorIcon sx={{ color: 'error.main' }} />;
      case 'warning':
        return <WarningIcon sx={{ color: 'warning.main' }} />;
      case 'info':
        return <InfoIcon sx={{ color: 'info.main' }} />;
      default:
        return <InfoIcon />;
    }
  };

  const getSeverityColor = (severity: string): any => {
    switch (severity) {
      case 'critical':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
        return 'info';
      default:
        return 'default';
    }
  };

  const getStatusColor = (status: string): any => {
    switch (status) {
      case 'active':
        return 'error';
      case 'acknowledged':
        return 'warning';
      case 'resolved':
        return 'success';
      default:
        return 'default';
    }
  };

  const handleAcknowledge = async (alert: Alert) => {
    // API call would go here
    setAlerts(alerts.map(a => 
      a.id === alert.id 
        ? { ...a, status: 'acknowledged', acknowledged_at: new Date().toISOString() }
        : a
    ));
    setAcknowledgeDialog({ open: false, alert: null });
  };

  const handleResolve = async (alert: Alert, resolution: string) => {
    // API call would go here
    setAlerts(alerts.map(a => 
      a.id === alert.id 
        ? { ...a, status: 'resolved', resolved_at: new Date().toISOString(), metadata: { ...a.metadata, resolution } }
        : a
    ));
    setResolveDialog({ open: false, alert: null, resolution: '' });
  };

  const filteredAlerts = alerts.filter(alert => {
    const severityMatch = filter.severity === 'all' || alert.severity === filter.severity;
    const statusMatch = filter.status === 'all' || alert.status === filter.status;
    return severityMatch && statusMatch;
  });

  const alertCounts = {
    total: alerts.length,
    critical: alerts.filter(a => a.severity === 'critical').length,
    warning: alerts.filter(a => a.severity === 'warning').length,
    info: alerts.filter(a => a.severity === 'info').length,
    active: alerts.filter(a => a.status === 'active').length,
    acknowledged: alerts.filter(a => a.status === 'acknowledged').length,
    resolved: alerts.filter(a => a.status === 'resolved').length,
  };

  return (
    <Box>
      {/* Header with stats */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">Alert Management</Typography>
          <Box display="flex" gap={1}>
            <Tooltip title={muteNotifications ? "Enable notifications" : "Mute notifications"}>
              <IconButton onClick={() => setMuteNotifications(!muteNotifications)}>
                {muteNotifications ? <NotificationsOff /> : <NotificationsActive />}
              </IconButton>
            </Tooltip>
            <Tooltip title="Refresh alerts">
              <IconButton>
                <Refresh />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Summary chips */}
        <Box display="flex" gap={1} flexWrap="wrap">
          <Chip
            label={`Total: ${alertCounts.total}`}
            variant="outlined"
          />
          <Chip
            label={`Critical: ${alertCounts.critical}`}
            color="error"
            variant={alertCounts.critical > 0 ? "filled" : "outlined"}
          />
          <Chip
            label={`Warning: ${alertCounts.warning}`}
            color="warning"
            variant={alertCounts.warning > 0 ? "filled" : "outlined"}
          />
          <Chip
            label={`Info: ${alertCounts.info}`}
            color="info"
            variant={alertCounts.info > 0 ? "filled" : "outlined"}
          />
          <Divider orientation="vertical" flexItem sx={{ mx: 1 }} />
          <Chip
            label={`Active: ${alertCounts.active}`}
            color={alertCounts.active > 0 ? "error" : "default"}
            variant="outlined"
          />
          <Chip
            label={`Acknowledged: ${alertCounts.acknowledged}`}
            color="warning"
            variant="outlined"
          />
          <Chip
            label={`Resolved: ${alertCounts.resolved}`}
            color="success"
            variant="outlined"
          />
        </Box>
      </Paper>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box display="flex" gap={2} alignItems="center">
          <FilterList />
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Severity</InputLabel>
            <Select
              value={filter.severity}
              label="Severity"
              onChange={(e) => setFilter({ ...filter, severity: e.target.value })}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="critical">Critical</MenuItem>
              <MenuItem value="warning">Warning</MenuItem>
              <MenuItem value="info">Info</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={filter.status}
              label="Status"
              onChange={(e) => setFilter({ ...filter, status: e.target.value })}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="acknowledged">Acknowledged</MenuItem>
              <MenuItem value="resolved">Resolved</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Paper>

      {/* Alerts List */}
      <Paper>
        {filteredAlerts.length === 0 ? (
          <Box p={4} textAlign="center">
            <Typography color="textSecondary">
              No alerts match the current filters
            </Typography>
          </Box>
        ) : (
          <List>
            {filteredAlerts.map((alert, index) => (
              <React.Fragment key={alert.id}>
                {index > 0 && <Divider />}
                <ListItem
                  sx={{
                    bgcolor: alert.status === 'active' && alert.severity === 'critical' 
                      ? 'error.main' + '10' 
                      : 'transparent',
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                >
                  <ListItemIcon>
                    <Badge
                      badgeContent={alert.status === 'active' ? '!' : null}
                      color="error"
                    >
                      {getSeverityIcon(alert.severity)}
                    </Badge>
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="body1">{alert.message}</Typography>
                        <Chip
                          label={alert.severity}
                          size="small"
                          color={getSeverityColor(alert.severity)}
                        />
                        <Chip
                          label={alert.status}
                          size="small"
                          color={getStatusColor(alert.status)}
                          variant="outlined"
                        />
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="caption" color="textSecondary">
                          Source: {alert.source} | Created: {format(new Date(alert.created_at), 'PPpp')}
                        </Typography>
                        {alert.acknowledged_at && (
                          <Typography variant="caption" color="textSecondary" display="block">
                            Acknowledged: {format(new Date(alert.acknowledged_at), 'PPpp')}
                          </Typography>
                        )}
                        {alert.resolved_at && (
                          <Typography variant="caption" color="textSecondary" display="block">
                            Resolved: {format(new Date(alert.resolved_at), 'PPpp')}
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                  <ListItemSecondaryAction>
                    <Box display="flex" gap={1}>
                      {alert.status === 'active' && (
                        <Tooltip title="Acknowledge">
                          <IconButton
                            size="small"
                            onClick={() => setAcknowledgeDialog({ open: true, alert })}
                          >
                            <CheckCircle />
                          </IconButton>
                        </Tooltip>
                      )}
                      {alert.status !== 'resolved' && (
                        <Tooltip title="Resolve">
                          <IconButton
                            size="small"
                            onClick={() => setResolveDialog({ open: true, alert, resolution: '' })}
                          >
                            <Cancel />
                          </IconButton>
                        </Tooltip>
                      )}
                      <IconButton
                        size="small"
                        onClick={() => setExpandedAlert(expandedAlert === alert.id ? null : alert.id)}
                      >
                        {expandedAlert === alert.id ? <ExpandLess /> : <ExpandMore />}
                      </IconButton>
                    </Box>
                  </ListItemSecondaryAction>
                </ListItem>
                <Collapse in={expandedAlert === alert.id}>
                  <Box px={7} py={2} bgcolor="background.default">
                    <Typography variant="subtitle2" gutterBottom>
                      Alert Details
                    </Typography>
                    <Typography variant="body2" paragraph>
                      Type: {alert.type}
                    </Typography>
                    {alert.metadata && (
                      <Box>
                        <Typography variant="subtitle2" gutterBottom>
                          Metadata
                        </Typography>
                        <pre style={{ 
                          background: theme.palette.grey[100], 
                          padding: theme.spacing(1),
                          borderRadius: theme.shape.borderRadius,
                          overflow: 'auto',
                          fontSize: '0.875rem',
                        }}>
                          {JSON.stringify(alert.metadata, null, 2)}
                        </pre>
                      </Box>
                    )}
                  </Box>
                </Collapse>
              </React.Fragment>
            ))}
          </List>
        )}
      </Paper>

      {/* Acknowledge Dialog */}
      <Dialog
        open={acknowledgeDialog.open}
        onClose={() => setAcknowledgeDialog({ open: false, alert: null })}
      >
        <DialogTitle>Acknowledge Alert</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to acknowledge this alert?
          </Typography>
          {acknowledgeDialog.alert && (
            <Alert severity={getSeverityColor(acknowledgeDialog.alert.severity)} sx={{ mt: 2 }}>
              {acknowledgeDialog.alert.message}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAcknowledgeDialog({ open: false, alert: null })}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={() => acknowledgeDialog.alert && handleAcknowledge(acknowledgeDialog.alert)}
          >
            Acknowledge
          </Button>
        </DialogActions>
      </Dialog>

      {/* Resolve Dialog */}
      <Dialog
        open={resolveDialog.open}
        onClose={() => setResolveDialog({ open: false, alert: null, resolution: '' })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Resolve Alert</DialogTitle>
        <DialogContent>
          {resolveDialog.alert && (
            <Alert severity={getSeverityColor(resolveDialog.alert.severity)} sx={{ mb: 2 }}>
              {resolveDialog.alert.message}
            </Alert>
          )}
          <TextField
            autoFocus
            margin="dense"
            label="Resolution Notes"
            fullWidth
            multiline
            rows={4}
            value={resolveDialog.resolution}
            onChange={(e) => setResolveDialog({ ...resolveDialog, resolution: e.target.value })}
            placeholder="Describe how this alert was resolved..."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResolveDialog({ open: false, alert: null, resolution: '' })}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={() => resolveDialog.alert && handleResolve(resolveDialog.alert, resolveDialog.resolution)}
            disabled={!resolveDialog.resolution.trim()}
          >
            Resolve
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AlertsPanel;