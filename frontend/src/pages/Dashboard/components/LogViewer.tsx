import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Chip,
  InputAdornment,
  List,
  ListItem,
  ListItemText,
  Skeleton,
  Tooltip,
  Button,
  useTheme,
} from '@mui/material';
import {
  Search,
  FilterList,
  Refresh,
  Download,
  Clear,
  Error,
  Warning,
  Info,
  BugReport,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { useDashboardData } from '../../../hooks/useDashboardData';

interface LogEntry {
  id: string;
  timestamp: string;
  service: string;
  level: string;
  message: string;
  metadata?: any;
}

const LogViewer: React.FC = () => {
  const theme = useTheme();
  const { data, loading, refetch } = useDashboardData();
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [levelFilter, setLevelFilter] = useState('all');
  const [serviceFilter, setServiceFilter] = useState('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const logContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (data?.logs) {
      setLogs(data.logs);
    }
  }, [data?.logs]);

  useEffect(() => {
    // Apply filters
    let filtered = logs;

    if (searchTerm) {
      filtered = filtered.filter(log =>
        log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.service.toLowerCase().includes(searchTerm.toLowerCase()) ||
        JSON.stringify(log.metadata).toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (levelFilter !== 'all') {
      filtered = filtered.filter(log => log.level === levelFilter);
    }

    if (serviceFilter !== 'all') {
      filtered = filtered.filter(log => log.service === serviceFilter);
    }

    setFilteredLogs(filtered);
  }, [logs, searchTerm, levelFilter, serviceFilter]);

  useEffect(() => {
    // Auto-scroll to bottom when new logs arrive
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [filteredLogs, autoScroll]);

  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'ERROR':
        return <Error sx={{ color: 'error.main' }} />;
      case 'WARNING':
        return <Warning sx={{ color: 'warning.main' }} />;
      case 'INFO':
        return <Info sx={{ color: 'info.main' }} />;
      case 'DEBUG':
        return <BugReport sx={{ color: 'text.secondary' }} />;
      default:
        return null;
    }
  };

  const getLevelColor = (level: string): any => {
    switch (level) {
      case 'ERROR':
        return 'error';
      case 'WARNING':
        return 'warning';
      case 'INFO':
        return 'info';
      case 'DEBUG':
        return 'default';
      default:
        return 'default';
    }
  };

  const exportLogs = () => {
    const content = filteredLogs.map(log => 
      `[${log.timestamp}] [${log.level}] [${log.service}] ${log.message} ${log.metadata ? JSON.stringify(log.metadata) : ''}`
    ).join('\n');
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs_${format(new Date(), 'yyyy-MM-dd_HH-mm-ss')}.txt`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const getUniqueServices = () => {
    const services = new Set(logs.map(log => log.service));
    return Array.from(services);
  };

  if (loading) {
    return (
      <Box>
        <Skeleton variant="rectangular" height={60} sx={{ mb: 2 }} />
        {[1, 2, 3, 4, 5].map(i => (
          <Skeleton key={i} variant="text" height={40} sx={{ mb: 1 }} />
        ))}
      </Box>
    );
  }

  return (
    <Box>
      {/* Header and Filters */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">System Logs</Typography>
          <Box display="flex" gap={1}>
            <Tooltip title="Toggle auto-scroll">
              <Button
                size="small"
                variant={autoScroll ? 'contained' : 'outlined'}
                onClick={() => setAutoScroll(!autoScroll)}
              >
                Auto-scroll
              </Button>
            </Tooltip>
            <Tooltip title="Export logs">
              <IconButton onClick={exportLogs}>
                <Download />
              </IconButton>
            </Tooltip>
            <Tooltip title="Refresh logs">
              <IconButton onClick={() => refetch()}>
                <Refresh />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        <Box display="flex" gap={2} alignItems="center">
          {/* Search */}
          <TextField
            size="small"
            placeholder="Search logs..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            sx={{ flex: 1 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
              endAdornment: searchTerm && (
                <InputAdornment position="end">
                  <IconButton size="small" onClick={() => setSearchTerm('')}>
                    <Clear />
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          {/* Level Filter */}
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Level</InputLabel>
            <Select
              value={levelFilter}
              label="Level"
              onChange={(e) => setLevelFilter(e.target.value)}
            >
              <MenuItem value="all">All Levels</MenuItem>
              <MenuItem value="ERROR">Error</MenuItem>
              <MenuItem value="WARNING">Warning</MenuItem>
              <MenuItem value="INFO">Info</MenuItem>
              <MenuItem value="DEBUG">Debug</MenuItem>
            </Select>
          </FormControl>

          {/* Service Filter */}
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Service</InputLabel>
            <Select
              value={serviceFilter}
              label="Service"
              onChange={(e) => setServiceFilter(e.target.value)}
            >
              <MenuItem value="all">All Services</MenuItem>
              {getUniqueServices().map(service => (
                <MenuItem key={service} value={service}>
                  {service}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        {/* Log counts */}
        <Box display="flex" gap={1} mt={2}>
          <Chip
            label={`Total: ${filteredLogs.length}`}
            size="small"
            variant="outlined"
          />
          <Chip
            label={`Errors: ${filteredLogs.filter(l => l.level === 'ERROR').length}`}
            size="small"
            color="error"
            variant="outlined"
          />
          <Chip
            label={`Warnings: ${filteredLogs.filter(l => l.level === 'WARNING').length}`}
            size="small"
            color="warning"
            variant="outlined"
          />
        </Box>
      </Paper>

      {/* Log List */}
      <Paper
        ref={logContainerRef}
        sx={{
          height: 600,
          overflow: 'auto',
          bgcolor: theme.palette.mode === 'dark' ? 'grey.900' : 'grey.50',
        }}
      >
        {filteredLogs.length === 0 ? (
          <Box p={4} textAlign="center">
            <Typography color="textSecondary">
              No logs match the current filters
            </Typography>
          </Box>
        ) : (
          <List dense>
            {filteredLogs.map((log, index) => (
              <ListItem
                key={log.id}
                sx={{
                  borderBottom: 1,
                  borderColor: 'divider',
                  '&:hover': { bgcolor: 'action.hover' },
                  fontFamily: 'monospace',
                }}
              >
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography
                        variant="caption"
                        sx={{
                          color: 'text.secondary',
                          minWidth: 180,
                        }}
                      >
                        {format(new Date(log.timestamp), 'yyyy-MM-dd HH:mm:ss.SSS')}
                      </Typography>
                      {getLevelIcon(log.level)}
                      <Chip
                        label={log.level}
                        size="small"
                        color={getLevelColor(log.level)}
                        sx={{ minWidth: 70 }}
                      />
                      <Chip
                        label={log.service}
                        size="small"
                        variant="outlined"
                        sx={{ minWidth: 100 }}
                      />
                      <Typography
                        variant="body2"
                        sx={{
                          wordBreak: 'break-all',
                          flex: 1,
                        }}
                      >
                        {log.message}
                      </Typography>
                    </Box>
                  }
                  secondary={
                    log.metadata && (
                      <Box mt={0.5}>
                        <Typography
                          variant="caption"
                          component="pre"
                          sx={{
                            color: 'text.secondary',
                            bgcolor: 'background.paper',
                            p: 0.5,
                            borderRadius: 1,
                            overflow: 'auto',
                            maxHeight: 100,
                          }}
                        >
                          {JSON.stringify(log.metadata, null, 2)}
                        </Typography>
                      </Box>
                    )
                  }
                />
              </ListItem>
            ))}
          </List>
        )}
      </Paper>
    </Box>
  );
};

export default LogViewer;