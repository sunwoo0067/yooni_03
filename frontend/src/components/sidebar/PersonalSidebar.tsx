import React from 'react';
import { 
  Box, 
  Drawer, 
  List, 
  ListItem, 
  ListItemIcon, 
  ListItemText, 
  Divider,
  Typography,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Dashboard,
  Settings,
  Inventory,
  Download,
  ShoppingCart,
  SmartToy,
  Menu,
  Close,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';

// 개인 사용자용 사이드바
const PersonalSidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = React.useState(false);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const menuItems = [
    { text: '대시보드', icon: <Dashboard />, path: '/dashboard' },
    { text: '상품 관리', icon: <Inventory />, path: '/products' },
    { text: '상품 수집', icon: <Download />, path: '/collection' },
    { text: '주문 관리', icon: <ShoppingCart />, path: '/orders' },
    { text: 'AI 소싱', icon: <SmartToy />, path: '/ai-sourcing' },
    { text: '설정', icon: <Settings />, path: '/settings' },
  ];

  const drawer = (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: 'background.paper',
      }}
    >
      {/* 헤더 */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          p: 2,
          borderBottom: 1,
          borderColor: 'divider',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <SmartToy sx={{ color: 'primary.main' }} />
          <Typography variant="h6" fontWeight="bold">
            Yooni 개인용
          </Typography>
        </Box>
        <IconButton onClick={handleDrawerToggle} sx={{ display: { lg: 'none' } }}>
          <Close />
        </IconButton>
      </Box>

      {/* 메뉴 */}
      <List sx={{ flex: 1, py: 2 }}>
        {menuItems.map((item) => (
          <ListItem
            button
            key={item.text}
            onClick={() => navigate(item.path)}
            sx={{
              borderRadius: 2,
              mx: 1,
              mb: 0.5,
              bgcolor: location.pathname === item.path ? 'primary.light' : 'transparent',
              color: location.pathname === item.path ? 'primary.contrastText' : 'text.primary',
              '&:hover': {
                bgcolor: location.pathname === item.path ? 'primary.main' : 'action.hover',
              },
            }}
          >
            <Tooltip title={item.text} placement="right">
              <ListItemIcon
                sx={{
                  minWidth: 40,
                  color: location.pathname === item.path ? 'primary.contrastText' : 'inherit',
                }}
              >
                {item.icon}
              </ListItemIcon>
            </Tooltip>
            <ListItemText 
              primary={item.text} 
              sx={{ 
                display: { xs: 'none', sm: 'block' },
                '& .MuiListItemText-primary': {
                  fontWeight: location.pathname === item.path ? 'bold' : 'normal',
                },
              }} 
            />
          </ListItem>
        ))}
      </List>

      {/* 하단 정보 */}
      <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
        <Typography variant="caption" color="text.secondary">
          Yooni Dropshipping v1.0
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block">
          개인 사용자용
        </Typography>
      </Box>
    </Box>
  );

  return (
    <Box
      component="nav"
      sx={{
        width: { sm: 240 },
        flexShrink: { sm: 0 },
      }}
      aria-label="navigation"
    >
      {/* 모바일용 드로어 */}
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={handleDrawerToggle}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile.
        }}
        sx={{
          display: { xs: 'block', lg: 'none' },
          '& .MuiDrawer-paper': { 
            boxSizing: 'border-box', 
            width: 240,
            borderRight: 0,
          },
        }}
      >
        {drawer}
      </Drawer>

      {/* 데스크톱용 드로어 */}
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: 'none', lg: 'block' },
          '& .MuiDrawer-paper': { 
            boxSizing: 'border-box', 
            width: 240,
            borderRight: 0,
          },
        }}
        open
      >
        {drawer}
      </Drawer>
    </Box>
  );
};

export default PersonalSidebar;