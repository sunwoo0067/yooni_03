import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowBack as ArrowLeft, ShoppingCart } from '@mui/icons-material';
import { Box, Typography, Paper, Button, List, ListItem, ListItemIcon, ListItemText } from '@mui/material';
import { green } from '@mui/material/colors';

const OrderDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  
  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ mb: 3 }}>
        <Button
          component={Link}
          to="/orders"
          startIcon={<ArrowLeft />}
          sx={{ mb: 2, color: 'text.secondary' }}
        >
          Back to Orders
        </Button>
        <Typography variant="h4" component="h1" sx={{ mb: 1 }}>
          Order Detail
        </Typography>
        <Typography color="text.secondary">Order ID: {id}</Typography>
      </Box>
      
      <Paper sx={{ p: 4 }}>
        <Box sx={{ textAlign: 'center', maxWidth: 'sm', mx: 'auto' }}>
          <Box
            sx={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 64,
              height: 64,
              bgcolor: green[100],
              borderRadius: '50%',
              mb: 2
            }}
          >
            <ShoppingCart style={{ width: 32, height: 32, color: green[600] }} />
          </Box>
          <Typography variant="h5" sx={{ mb: 2 }}>Coming Soon</Typography>
          <Typography color="text.secondary" sx={{ mb: 3 }}>
            Order detail view is currently under development. You'll be able to:
          </Typography>
          <List sx={{ textAlign: 'left' }}>
            <ListItem disableGutters>
              <ListItemIcon sx={{ minWidth: 32 }}>
                <Typography color="success.main">•</Typography>
              </ListItemIcon>
              <ListItemText primary="View complete order information" />
            </ListItem>
            <ListItem disableGutters>
              <ListItemIcon sx={{ minWidth: 32 }}>
                <Typography color="success.main">•</Typography>
              </ListItemIcon>
              <ListItemText primary="Update order and shipping status" />
            </ListItem>
            <ListItem disableGutters>
              <ListItemIcon sx={{ minWidth: 32 }}>
                <Typography color="success.main">•</Typography>
              </ListItemIcon>
              <ListItemText primary="Communicate with customers" />
            </ListItem>
            <ListItem disableGutters>
              <ListItemIcon sx={{ minWidth: 32 }}>
                <Typography color="success.main">•</Typography>
              </ListItemIcon>
              <ListItemText primary="Process refunds and returns" />
            </ListItem>
          </List>
        </Box>
      </Paper>
    </Box>
  );
};

export default OrderDetail;