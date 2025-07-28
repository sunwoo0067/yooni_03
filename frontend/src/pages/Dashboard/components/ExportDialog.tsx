import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  RadioGroup,
  FormControlLabel,
  Radio,
  Typography,
  Box,
  Chip,
  Alert,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import {
  Download,
  Description,
  TableChart,
  Code,
} from '@mui/icons-material';

interface ExportDialogProps {
  open: boolean;
  onClose: () => void;
  onExport: (dataType: string, format: string, dateRange: any) => void;
}

const ExportDialog: React.FC<ExportDialogProps> = ({ open, onClose, onExport }) => {
  const [dataType, setDataType] = useState('orders');
  const [format, setFormat] = useState('csv');
  const [startDate, setStartDate] = useState<Date | null>(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000));
  const [endDate, setEndDate] = useState<Date | null>(new Date());

  const dataTypes = [
    { value: 'orders', label: 'Orders', description: 'Order history with customer details' },
    { value: 'products', label: 'Products', description: 'Product catalog with inventory' },
    { value: 'revenue', label: 'Revenue', description: 'Revenue breakdown by date and platform' },
    { value: 'metrics', label: 'All Metrics', description: 'Comprehensive dashboard metrics' },
  ];

  const formats = [
    { value: 'csv', label: 'CSV', icon: <Description />, description: 'Comma-separated values' },
    { value: 'excel', label: 'Excel', icon: <TableChart />, description: 'Microsoft Excel format' },
    { value: 'json', label: 'JSON', icon: <Code />, description: 'JavaScript Object Notation' },
  ];

  const handleExport = () => {
    if (startDate && endDate) {
      onExport(dataType, format, { startDate, endDate });
      onClose();
    }
  };

  const getEstimatedSize = () => {
    // Mock estimation based on data type and date range
    const days = endDate && startDate ? Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)) : 0;
    const sizeMap: { [key: string]: number } = {
      orders: days * 50,
      products: 200,
      revenue: days * 10,
      metrics: days * 100,
    };
    const size = sizeMap[dataType] || 100;
    
    if (size < 1000) {
      return `~${size} KB`;
    } else {
      return `~${(size / 1000).toFixed(1)} MB`;
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <Download />
          Export Dashboard Data
        </Box>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2 }}>
          {/* Data Type Selection */}
          <FormControl fullWidth sx={{ mb: 3 }}>
            <InputLabel>Data Type</InputLabel>
            <Select
              value={dataType}
              label="Data Type"
              onChange={(e) => setDataType(e.target.value)}
            >
              {dataTypes.map((type) => (
                <MenuItem key={type.value} value={type.value}>
                  <Box>
                    <Typography variant="body1">{type.label}</Typography>
                    <Typography variant="caption" color="textSecondary">
                      {type.description}
                    </Typography>
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Format Selection */}
          <Typography variant="subtitle2" gutterBottom>
            Export Format
          </Typography>
          <RadioGroup
            value={format}
            onChange={(e) => setFormat(e.target.value)}
            sx={{ mb: 3 }}
          >
            {formats.map((fmt) => (
              <FormControlLabel
                key={fmt.value}
                value={fmt.value}
                control={<Radio />}
                label={
                  <Box display="flex" alignItems="center" gap={1}>
                    {fmt.icon}
                    <Box>
                      <Typography variant="body1">{fmt.label}</Typography>
                      <Typography variant="caption" color="textSecondary">
                        {fmt.description}
                      </Typography>
                    </Box>
                  </Box>
                }
              />
            ))}
          </RadioGroup>

          {/* Date Range */}
          <Typography variant="subtitle2" gutterBottom>
            Date Range
          </Typography>
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <Box display="flex" gap={2} mb={3}>
              <DatePicker
                label="Start Date"
                value={startDate}
                onChange={setStartDate}
                sx={{ flex: 1 }}
              />
              <DatePicker
                label="End Date"
                value={endDate}
                onChange={setEndDate}
                sx={{ flex: 1 }}
              />
            </Box>
          </LocalizationProvider>

          {/* Export Info */}
          <Alert severity="info" icon={false}>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Box>
                <Typography variant="body2">
                  Estimated file size: <strong>{getEstimatedSize()}</strong>
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  Download link will expire in 1 hour
                </Typography>
              </Box>
              <Chip
                label={`${format.toUpperCase()}`}
                size="small"
                color="primary"
              />
            </Box>
          </Alert>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          startIcon={<Download />}
          onClick={handleExport}
          disabled={!startDate || !endDate || endDate < startDate}
        >
          Export Data
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ExportDialog;