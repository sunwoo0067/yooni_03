import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowBack as ArrowLeft, Inventory as Package } from '@mui/icons-material';
import { Box, Typography, Paper, Button, List, ListItem, ListItemIcon, ListItemText } from '@mui/material';
import { blue } from '@mui/material/colors';

const ProductDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  
  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ mb: 3 }}>
        <Button
          component={Link}
          to="/products"
          startIcon={<ArrowLeft />}
          sx={{ mb: 2, color: 'text.secondary' }}
        >
          Back to Products
        </Button>
        <Typography variant="h4" component="h1" sx={{ mb: 1 }}>
          Product Detail
        </Typography>
        <Typography color="text.secondary">Product ID: {id}</Typography>
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
              bgcolor: blue[100],
              borderRadius: '50%',
              mb: 2
            }}
          >
            <Package style={{ width: 32, height: 32, color: blue[600] }} />
          </Box>
          <Typography variant="h5" sx={{ mb: 2 }}>Coming Soon</Typography>
          <Typography color="text.secondary" sx={{ mb: 3 }}>
            Product detail view is currently under development. You'll be able to:
          </Typography>
          <List sx={{ textAlign: 'left' }}>
            <ListItem disableGutters>
              <ListItemIcon sx={{ minWidth: 32 }}>
                <Typography color="primary.main">•</Typography>
              </ListItemIcon>
              <ListItemText primary="View detailed product information" />
            </ListItem>
            <ListItem disableGutters>
              <ListItemIcon sx={{ minWidth: 32 }}>
                <Typography color="primary.main">•</Typography>
              </ListItemIcon>
              <ListItemText primary="Edit product details and pricing" />
            </ListItem>
            <ListItem disableGutters>
              <ListItemIcon sx={{ minWidth: 32 }}>
                <Typography color="primary.main">•</Typography>
              </ListItemIcon>
              <ListItemText primary="Manage product images" />
            </ListItem>
            <ListItem disableGutters>
              <ListItemIcon sx={{ minWidth: 32 }}>
                <Typography color="primary.main">•</Typography>
              </ListItemIcon>
              <ListItemText primary="Track inventory and sales history" />
            </ListItem>
          </List>
        </Box>
      </Paper>
    </Box>
  );
};

export default ProductDetail;