import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Badge,
  Menu,
  MenuItem,
  Divider,
  Box,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Notifications,
  AccountCircle,
  Logout,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

// 개인 사용자용 헤더
const PersonalHeader = () => {
  const navigate = useNavigate();
  const [anchorEl, setAnchorEl] = React.useState(null);
  const [notificationAnchorEl, setNotificationAnchorEl] = React.useState(null);

  const handleMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleNotificationOpen = (event) => {
    setNotificationAnchorEl(event.currentTarget);
  };

  const handleNotificationClose = () => {
    setNotificationAnchorEl(null);
  };

  const handleLogout = () => {
    // 로그아웃 로직 구현
    handleMenuClose();
    navigate('/login'); // 로그인 페이지로 이동 (실제 구현시)
  };

  const handleSettings = () => {
    navigate('/settings');
    handleMenuClose();
  };

  return (
    <AppBar 
      position="static" 
      sx={{ 
        zIndex: (theme) => theme.zIndex.drawer + 1,
        boxShadow: 'none',
        borderBottom: 1,
        borderColor: 'divider',
        bgcolor: 'background.paper',
        color: 'text.primary',
      }}
    >
      <Toolbar sx={{ display: 'flex', justifyContent: 'space-between' }}>
        {/* 왼쪽 영역 - 메뉴 버튼 */}
        <IconButton
          color="inherit"
          edge="start"
          onClick={() => {}}
          sx={{ mr: 2, display: { lg: 'none' } }}
        >
          <MenuIcon />
        </IconButton>
        
        {/* 중앙 영역 - 페이지 제목 */}
        <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 'bold' }}>
          Yooni 드롭시핑 - 개인 사용자용
        </Typography>
        
        {/* 오른쪽 영역 - 알림 및 사용자 메뉴 */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {/* 알림 아이콘 */}
          <IconButton 
            color="inherit" 
            onClick={handleNotificationOpen}
          >
            <Badge badgeContent={3} color="error">
              <Notifications />
            </Badge>
          </IconButton>
          
          {/* 사용자 프로필 아이콘 */}
          <IconButton
            color="inherit"
            onClick={handleMenuOpen}
          >
            <AccountCircle />
          </IconButton>
        </Box>
      </Toolbar>

      {/* 사용자 메뉴 */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
      >
        <MenuItem disabled>
          <Typography variant="subtitle2">개인 사용자</Typography>
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleSettings}>
          <SettingsIcon sx={{ mr: 1 }} />
          설정
        </MenuItem>
        <MenuItem onClick={handleLogout}>
          <Logout sx={{ mr: 1 }} />
          로그아웃
        </MenuItem>
      </Menu>

      {/* 알림 메뉴 */}
      <Menu
        anchorEl={notificationAnchorEl}
        open={Boolean(notificationAnchorEl)}
        onClose={handleNotificationClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
      >
        <MenuItem>
          <Typography variant="subtitle2">알림</Typography>
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleNotificationClose}>
          재고 부족: 3개 상품
        </MenuItem>
        <MenuItem onClick={handleNotificationClose}>
          새 주문 접수: 2건
        </MenuItem>
        <MenuItem onClick={handleNotificationClose}>
          수집 완료: 50개 상품
        </MenuItem>
      </Menu>
    </AppBar>
  );
};

export default PersonalHeader;