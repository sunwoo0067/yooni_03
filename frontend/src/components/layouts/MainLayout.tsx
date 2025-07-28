import React, { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Collapse,
  Avatar,
  Menu,
  MenuItem,
  Badge,
  useTheme,
  useMediaQuery,
  Tooltip,
  Switch,
  FormControlLabel,
} from '@mui/material'
import {
  Menu as MenuIcon,
  Dashboard,
  Inventory,
  ShoppingCart,
  AccountBalance,
  Store,
  Analytics,
  Campaign,
  People,
  Settings,
  ExpandLess,
  ExpandMore,
  Notifications,
  Brightness4,
  Brightness7,
  DarkMode,
  LightMode,
  Logout,
  Person,
  Search,
  LocalShipping,
  TrendingUp,
  AutoAwesome,
  Engineering,
  Sync,
  PriceCheck,
  Category,
  SupportAgent,
  Reviews,
  Speed,
  Rule,
} from '@mui/icons-material'
import { useAppDispatch, useAppSelector } from '@store/index'
import { toggleSidebar, toggleTheme } from '@store/slices/uiSlice'
// import { logout } from '@store/slices/authSlice' // 로그인 기능 제거

const drawerWidth = 260

interface MenuItem {
  title: string
  path?: string
  icon: React.ReactNode
  children?: MenuItem[]
}

const menuItems: MenuItem[] = [
  {
    title: '🏠 대시보드',
    path: '/dashboard',
    icon: <Dashboard />,
  },
  {
    title: '📥 상품 수집',
    icon: <Sync />,
    children: [
      { title: '도매처 상품 수집', path: '/products/sync', icon: null },
      { title: '수집 상품 목록', path: '/products/collected', icon: null },
      { title: '수집 일정 관리', path: '/products/collection-schedule', icon: null },
    ],
  },
  {
    title: '🔍 소싱 & 리서치',
    icon: <Search />,
    children: [
      { title: '트렌드 분석', path: '/research/trends', icon: null },
      { title: '상품 소싱', path: '/products/sourcing', icon: null },
      { title: '경쟁사 분석', path: '/research/competitors', icon: null },
      { title: 'AI 추천', path: '/ai-insights/recommendations', icon: null },
    ],
  },
  {
    title: '📦 상품 등록 & 관리',
    icon: <Inventory />,
    children: [
      { title: '상품 목록', path: '/products', icon: null },
      { title: '상품 등록', path: '/products/new', icon: null },
      { title: '카테고리 관리', path: '/products/categories', icon: null },
      { title: '가격 최적화', path: '/ai-insights/price-optimization', icon: null },
    ],
  },
  {
    title: '🏪 판매 채널 관리',
    icon: <Store />,
    children: [
      { title: '플랫폼 계정', path: '/platforms', icon: null },
      { title: '도매처 관리', path: '/wholesalers', icon: null },
      { title: '도매처 API 설정', path: '/wholesalers/api-settings', icon: null },
      { title: '상품 동기화', path: '/products/sync', icon: null },
      { title: '재고 연동', path: '/inventory/sync', icon: null },
    ],
  },
  {
    title: '📊 주문 & 배송',
    icon: <LocalShipping />,
    children: [
      { title: '주문 목록', path: '/orders', icon: null },
      { title: '주문 처리', path: '/orders/processing', icon: null },
      { title: '배송 관리', path: '/orders/shipping', icon: null },
      { title: '반품/교환', path: '/orders/returns', icon: null },
    ],
  },
  {
    title: '👥 고객 관리',
    icon: <People />,
    children: [
      { title: '고객 목록', path: '/customers', icon: null },
      { title: '문의 응대', path: '/customers/support', icon: null },
      { title: '리뷰 관리', path: '/customers/reviews', icon: null },
      { title: '마케팅 캠페인', path: '/marketing', icon: null },
    ],
  },
  {
    title: '💰 수익 & 최적화',
    icon: <TrendingUp />,
    children: [
      { title: '매출 분석', path: '/analytics', icon: null },
      { title: '수요 예측', path: '/ai-insights/demand-forecast', icon: null },
      { title: 'AI 인사이트', path: '/ai-insights/dashboard', icon: null },
      { title: '성과 리포트', path: '/analytics/reports', icon: null },
    ],
  },
  {
    title: '⚙️ 설정 & 도구',
    icon: <Settings />,
    children: [
      { title: '일반 설정', path: '/settings', icon: null },
      { title: '자동화 규칙', path: '/settings/automation', icon: null },
      { title: '연동 관리', path: '/settings/integrations', icon: null },
      { title: '시스템 모니터링', path: '/monitoring', icon: null },
    ],
  },
]

export default function MainLayout() {
  const theme = useTheme()
  const navigate = useNavigate()
  const location = useLocation()
  const dispatch = useAppDispatch()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
  
  const { sidebarOpen, theme: currentTheme } = useAppSelector((state) => state.ui)
  // 로그인 기능 제거 - 로컬 사용자로 고정
  const user = { name: 'Admin User', email: 'admin@yooni.com' }
  
  const [openMenus, setOpenMenus] = useState<{ [key: string]: boolean }>({})
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [notificationAnchor, setNotificationAnchor] = useState<null | HTMLElement>(null)

  const handleDrawerToggle = () => {
    dispatch(toggleSidebar())
  }

  const handleMenuClick = (title: string) => {
    setOpenMenus((prev) => ({
      ...prev,
      [title]: !prev[title],
    }))
  }

  const handleNavigate = (path: string) => {
    navigate(path)
    if (isMobile) {
      dispatch(toggleSidebar())
    }
  }

  const handleProfileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleProfileMenuClose = () => {
    setAnchorEl(null)
  }

  const handleNotificationOpen = (event: React.MouseEvent<HTMLElement>) => {
    setNotificationAnchor(event.currentTarget)
  }

  const handleNotificationClose = () => {
    setNotificationAnchor(null)
  }

  // const handleLogout = () => {
  //   dispatch(logout())
  //   navigate('/login')
  // } // 로그인 기능 제거

  const isMenuActive = (menuItem: MenuItem): boolean => {
    if (menuItem.path) {
      return location.pathname === menuItem.path
    }
    if (menuItem.children) {
      return menuItem.children.some((child) => child.path === location.pathname)
    }
    return false
  }

  const drawer = (
    <Box>
      <Toolbar>
        <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          Yooni Dropshipping
        </Typography>
      </Toolbar>
      <Divider />
      <List>
        {menuItems.map((item) => (
          <React.Fragment key={item.title}>
            <ListItem disablePadding>
              <ListItemButton
                onClick={() => {
                  if (item.path) {
                    handleNavigate(item.path)
                  } else if (item.children) {
                    handleMenuClick(item.title)
                  }
                }}
                selected={isMenuActive(item)}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.title} />
                {item.children && (
                  openMenus[item.title] ? <ExpandLess /> : <ExpandMore />
                )}
              </ListItemButton>
            </ListItem>
            {item.children && (
              <Collapse in={openMenus[item.title]} timeout="auto" unmountOnExit>
                <List component="div" disablePadding>
                  {item.children.map((child) => (
                    <ListItemButton
                      key={child.title}
                      sx={{ pl: 4 }}
                      onClick={() => child.path && handleNavigate(child.path)}
                      selected={child.path === location.pathname}
                    >
                      <ListItemText primary={child.title} />
                    </ListItemButton>
                  ))}
                </List>
              </Collapse>
            )}
          </React.Fragment>
        ))}
      </List>
    </Box>
  )

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${sidebarOpen ? drawerWidth : 0}px)` },
          ml: { sm: `${sidebarOpen ? drawerWidth : 0}px` },
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
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {/* Page title can be dynamically set here */}
          </Typography>
          
          {/* Theme toggle */}
          <IconButton color="inherit" onClick={() => dispatch(toggleTheme())}>
            {currentTheme === 'dark' ? <Brightness7 /> : <Brightness4 />}
          </IconButton>
          
          {/* Notifications */}
          <IconButton color="inherit" onClick={handleNotificationOpen}>
            <Badge badgeContent={4} color="error">
              <Notifications />
            </Badge>
          </IconButton>
          
          {/* Profile */}
          <IconButton onClick={handleProfileMenuOpen} sx={{ ml: 2 }}>
            <Avatar sx={{ width: 32, height: 32 }}>
              {user?.name?.charAt(0) || 'U'}
            </Avatar>
          </IconButton>
        </Toolbar>
      </AppBar>
      
      {/* Profile Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleProfileMenuClose}
      >
        <MenuItem onClick={() => { handleProfileMenuClose(); navigate('/profile') }}>
          <ListItemIcon>
            <Person fontSize="small" />
          </ListItemIcon>
          프로필
        </MenuItem>
        <MenuItem onClick={() => { handleProfileMenuClose(); navigate('/settings') }}>
          <ListItemIcon>
            <Settings fontSize="small" />
          </ListItemIcon>
          설정
        </MenuItem>
        {/* 로그인 기능 제거
        <Divider />
        <MenuItem onClick={handleLogout}>
          <ListItemIcon>
            <Logout fontSize="small" />
          </ListItemIcon>
          로그아웃
        </MenuItem>
        */}
      </Menu>
      
      {/* Notification Menu */}
      <Menu
        anchorEl={notificationAnchor}
        open={Boolean(notificationAnchor)}
        onClose={handleNotificationClose}
        PaperProps={{
          sx: { width: 360, maxHeight: 400 }
        }}
      >
        <Box sx={{ p: 2 }}>
          <Typography variant="h6">알림</Typography>
        </Box>
        <Divider />
        <MenuItem onClick={handleNotificationClose}>
          <Typography variant="body2">
            새로운 주문이 5건 접수되었습니다.
          </Typography>
        </MenuItem>
        <MenuItem onClick={handleNotificationClose}>
          <Typography variant="body2">
            상품 '무선 이어폰'의 재고가 부족합니다.
          </Typography>
        </MenuItem>
      </Menu>
      
      {/* Sidebar Drawer */}
      <Box
        component="nav"
        sx={{ width: { sm: sidebarOpen ? drawerWidth : 0 }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant={isMobile ? 'temporary' : 'persistent'}
          open={sidebarOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true, // Better open performance on mobile.
          }}
          sx={{
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
            },
          }}
        >
          {drawer}
        </Drawer>
      </Box>
      
      {/* Main content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${sidebarOpen ? drawerWidth : 0}px)` },
          transition: theme.transitions.create('margin', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
          ml: { sm: sidebarOpen ? 0 : `-${drawerWidth}px` },
          mt: 8, // Toolbar height
        }}
      >
        <Outlet />
      </Box>
    </Box>
  )
}