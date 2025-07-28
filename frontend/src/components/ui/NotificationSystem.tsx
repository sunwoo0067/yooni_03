/**
 * 강화된 알림 시스템
 * 사용자 중심의 피드백과 액션 가능한 알림 제공
 */

import React, { useState, useEffect, createContext, useContext } from 'react'
import {
  Alert,
  AlertTitle,
  Snackbar,
  Button,
  IconButton,
  Box,
  Typography,
  LinearProgress,
  Fab,
  Badge,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Stack,
  Chip,
  Avatar,
  useTheme,
} from '@mui/material'
import {
  CheckCircle,
  Error as ErrorIcon,
  Warning,
  Info,
  Close,
  Undo,
  Refresh,
  Notifications,
  NotificationsActive,
  Delete,
  CheckCircleOutline,
  AccessTime,
  TrendingUp,
  ShoppingCart,
  Inventory,
  CloudSync,
} from '@mui/icons-material'
import { motion, AnimatePresence } from 'framer-motion'
import { formatDate } from '@utils/format'

// 알림 타입 정의
export interface NotificationData {
  id: string
  type: 'success' | 'error' | 'warning' | 'info' | 'loading' | 'progress'
  title: string
  message: string
  duration?: number // 0이면 수동 닫기
  icon?: React.ReactNode
  actions?: NotificationAction[]
  progress?: number // 0-100 for progress notifications
  category?: 'system' | 'business' | 'user' | 'security'
  timestamp: Date
  read?: boolean
  persistent?: boolean
}

export interface NotificationAction {
  label: string
  action: () => void
  variant?: 'text' | 'outlined' | 'contained'
  color?: 'primary' | 'secondary' | 'error' | 'warning' | 'info' | 'success'
}

// 컨텍스트 정의
interface NotificationContextType {
  notifications: NotificationData[]
  addNotification: (notification: Omit<NotificationData, 'id' | 'timestamp'>) => string
  removeNotification: (id: string) => void
  markAsRead: (id: string) => void
  clearAll: () => void
  showSuccess: (title: string, message: string, actions?: NotificationAction[]) => string
  showError: (title: string, message: string, actions?: NotificationAction[]) => string
  showWarning: (title: string, message: string, actions?: NotificationAction[]) => string
  showInfo: (title: string, message: string, actions?: NotificationAction[]) => string
  showProgress: (title: string, message: string, progress: number) => string
  updateProgress: (id: string, progress: number, message?: string) => void
  // 간편 메서드 (하위 호환성)
  success: (message: string, title?: string) => string
  error: (message: string, title?: string) => string
  warning: (message: string, title?: string) => string
  info: (message: string, title?: string) => string
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined)

// 알림 프로바이더
export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [notifications, setNotifications] = useState<NotificationData[]>([])
  const [currentSnackbar, setCurrentSnackbar] = useState<NotificationData | null>(null)

  // 알림 추가
  const addNotification = (notification: Omit<NotificationData, 'id' | 'timestamp'>): string => {
    const id = Date.now().toString() + Math.random().toString(36).substr(2, 9)
    const newNotification: NotificationData = {
      id,
      timestamp: new Date(),
      duration: notification.duration ?? (notification.type === 'error' ? 6000 : 4000),
      read: false,
      ...notification,
    }

    setNotifications(prev => [newNotification, ...prev])

    // 스낵바 표시 (로딩/진행 타입이 아닌 경우)
    if (notification.type !== 'loading' && notification.type !== 'progress') {
      setCurrentSnackbar(newNotification)
    }

    return id
  }

  // 알림 제거
  const removeNotification = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
    if (currentSnackbar?.id === id) {
      setCurrentSnackbar(null)
    }
  }

  // 읽음 표시
  const markAsRead = (id: string) => {
    setNotifications(prev => 
      prev.map(n => n.id === id ? { ...n, read: true } : n)
    )
  }

  // 전체 삭제
  const clearAll = () => {
    setNotifications([])
    setCurrentSnackbar(null)
  }

  // 편의 메서드들
  const showSuccess = (title: string, message: string, actions?: NotificationAction[]) => 
    addNotification({ type: 'success', title, message, actions, icon: <CheckCircle /> })

  const showError = (title: string, message: string, actions?: NotificationAction[]) => 
    addNotification({ type: 'error', title, message, actions, icon: <ErrorIcon />, duration: 8000 })

  const showWarning = (title: string, message: string, actions?: NotificationAction[]) => 
    addNotification({ type: 'warning', title, message, actions, icon: <Warning /> })

  const showInfo = (title: string, message: string, actions?: NotificationAction[]) => 
    addNotification({ type: 'info', title, message, actions, icon: <Info /> })

  const showProgress = (title: string, message: string, progress: number) => 
    addNotification({ type: 'progress', title, message, progress, duration: 0, persistent: true })

  // 진행상황 업데이트
  const updateProgress = (id: string, progress: number, message?: string) => {
    setNotifications(prev => 
      prev.map(n => n.id === id ? { 
        ...n, 
        progress, 
        message: message || n.message,
        ...(progress >= 100 && { type: 'success' as const, icon: <CheckCircle /> })
      } : n)
    )
  }

  // 자동 제거 타이머
  useEffect(() => {
    if (currentSnackbar && currentSnackbar.duration && currentSnackbar.duration > 0) {
      const timer = setTimeout(() => {
        setCurrentSnackbar(null)
      }, currentSnackbar.duration)

      return () => clearTimeout(timer)
    }
  }, [currentSnackbar])

  const contextValue: NotificationContextType = {
    notifications,
    addNotification,
    removeNotification,
    markAsRead,
    clearAll,
    showSuccess,
    showError,
    showWarning,
    showInfo,
    showProgress,
    updateProgress,
    // 간편 메서드 (하위 호환성)
    success: (message: string, title?: string) => showSuccess(title || '성공', message),
    error: (message: string, title?: string) => showError(title || '오류', message),
    warning: (message: string, title?: string) => showWarning(title || '경고', message),
    info: (message: string, title?: string) => showInfo(title || '정보', message),
  }

  return (
    <NotificationContext.Provider value={contextValue}>
      {children}
      <NotificationSnackbar 
        notification={currentSnackbar}
        onClose={() => setCurrentSnackbar(null)}
      />
    </NotificationContext.Provider>
  )
}

// 훅
export const useNotification = () => {
  const context = useContext(NotificationContext)
  if (!context) {
    throw new Error('useNotification must be used within NotificationProvider')
  }
  return context
}

// 스낵바 컴포넌트
const NotificationSnackbar: React.FC<{
  notification: NotificationData | null
  onClose: () => void
}> = ({ notification, onClose }) => {
  if (!notification) return null

  const getSeverity = (type: NotificationData['type']) => {
    switch (type) {
      case 'success': return 'success'
      case 'error': return 'error'
      case 'warning': return 'warning'
      case 'info': return 'info'
      default: return 'info'
    }
  }

  return (
    <Snackbar
      open={Boolean(notification)}
      anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
      onClose={onClose}
    >
      <Alert
        severity={getSeverity(notification.type)}
        onClose={onClose}
        sx={{ 
          minWidth: 350, 
          maxWidth: 500,
          '& .MuiAlert-message': { width: '100%' }
        }}
        icon={notification.icon || undefined}
      >
        <AlertTitle sx={{ fontWeight: 600 }}>
          {notification.title}
        </AlertTitle>
        <Typography variant="body2" sx={{ mb: notification.actions ? 2 : 0 }}>
          {notification.message}
        </Typography>
        
        {/* 진행 표시 */}
        {notification.type === 'progress' && notification.progress !== undefined && (
          <Box sx={{ mt: 1 }}>
            <LinearProgress 
              variant="determinate" 
              value={notification.progress} 
              sx={{ mb: 1 }}
            />
            <Typography variant="caption" color="text.secondary">
              {notification.progress.toFixed(0)}% 완료
            </Typography>
          </Box>
        )}

        {/* 액션 버튼들 */}
        {notification.actions && notification.actions.length > 0 && (
          <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {notification.actions.map((action, index) => (
              <Button
                key={index}
                size="small"
                variant={action.variant || 'outlined'}
                color={action.color || 'primary'}
                onClick={() => {
                  action.action()
                  onClose()
                }}
              >
                {action.label}
              </Button>
            ))}
          </Box>
        )}
      </Alert>
    </Snackbar>
  )
}

// 알림 센터 FAB
export const NotificationCenter: React.FC = () => {
  const { notifications, markAsRead, removeNotification, clearAll } = useNotification()
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const theme = useTheme()

  const unreadCount = notifications.filter(n => !n.read).length
  const recentNotifications = notifications.slice(0, 10)

  const handleOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
    // 열었을 때 읽지 않은 알림들 읽음 처리
    notifications.filter(n => !n.read).forEach(n => markAsRead(n.id))
  }

  const handleClose = () => {
    setAnchorEl(null)
  }

  const getCategoryIcon = (category?: string) => {
    switch (category) {
      case 'business': return <TrendingUp fontSize="small" />
      case 'user': return <ShoppingCart fontSize="small" />
      case 'system': return <Inventory fontSize="small" />
      case 'security': return <CloudSync fontSize="small" />
      default: return <Notifications fontSize="small" />
    }
  }

  const getTypeColor = (type: NotificationData['type']) => {
    switch (type) {
      case 'success': return theme.palette.success.main
      case 'error': return theme.palette.error.main
      case 'warning': return theme.palette.warning.main
      case 'info': return theme.palette.info.main
      default: return theme.palette.grey[500]
    }
  }

  return (
    <>
      {/* 알림 센터 FAB */}
      <Fab
        color="primary"
        onClick={handleOpen}
        sx={{
          position: 'fixed',
          bottom: 80,
          right: 16,
          zIndex: 1000,
        }}
      >
        <Badge badgeContent={unreadCount} color="error" max={99}>
          {unreadCount > 0 ? <NotificationsActive /> : <Notifications />}
        </Badge>
      </Fab>

      {/* 알림 메뉴 */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleClose}
        PaperProps={{
          sx: { 
            width: 400, 
            maxHeight: 500,
            mt: -1,
          }
        }}
        anchorOrigin={{ vertical: 'top', horizontal: 'left' }}
        transformOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        {/* 헤더 */}
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6" fontWeight={600}>
              알림 센터
            </Typography>
            {notifications.length > 0 && (
              <Button size="small" onClick={clearAll}>
                전체 삭제
              </Button>
            )}
          </Box>
          {unreadCount > 0 && (
            <Typography variant="body2" color="text.secondary">
              {unreadCount}개의 새 알림
            </Typography>
          )}
        </Box>

        {/* 알림 목록 */}
        {recentNotifications.length === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <Notifications sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
            <Typography variant="body2" color="text.secondary">
              새로운 알림이 없습니다
            </Typography>
          </Box>
        ) : (
          <Box sx={{ maxHeight: 350, overflow: 'auto' }}>
            {recentNotifications.map((notification, index) => (
              <MenuItem
                key={notification.id}
                sx={{ 
                  p: 2, 
                  borderBottom: index < recentNotifications.length - 1 ? 1 : 0,
                  borderColor: 'divider',
                  alignItems: 'flex-start',
                  whiteSpace: 'normal',
                  height: 'auto',
                }}
                onClick={() => {
                  markAsRead(notification.id)
                  handleClose()
                }}
              >
                <ListItemIcon sx={{ mt: 0.5 }}>
                  <Avatar 
                    sx={{ 
                      width: 32, 
                      height: 32, 
                      bgcolor: getTypeColor(notification.type),
                      color: 'white'
                    }}
                  >
                    {getCategoryIcon(notification.category)}
                  </Avatar>
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <Typography variant="body2" fontWeight={notification.read ? 400 : 600}>
                        {notification.title}
                      </Typography>
                      <IconButton 
                        size="small" 
                        onClick={(e) => {
                          e.stopPropagation()
                          removeNotification(notification.id)
                        }}
                      >
                        <Close fontSize="small" />
                      </IconButton>
                    </Box>
                  }
                  secondary={
                    <Box>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                        {notification.message}
                      </Typography>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="caption" color="text.disabled">
                          {formatDate(notification.timestamp.toISOString())}
                        </Typography>
                        <Chip 
                          label={notification.type} 
                          size="small" 
                          variant="outlined"
                          sx={{ 
                            height: 20, 
                            fontSize: '0.7rem',
                            borderColor: getTypeColor(notification.type),
                            color: getTypeColor(notification.type)
                          }}
                        />
                      </Box>
                    </Box>
                  }
                />
              </MenuItem>
            ))}
          </Box>
        )}

        {/* 푸터 */}
        {notifications.length > 10 && (
          <>
            <Divider />
            <MenuItem onClick={handleClose} sx={{ justifyContent: 'center', py: 1 }}>
              <Typography variant="body2" color="primary">
                모든 알림 보기 ({notifications.length}개)
              </Typography>
            </MenuItem>
          </>
        )}
      </Menu>
    </>
  )
}

// 비즈니스 로직용 프리셋 알림들
export const BusinessNotifications = {
  // 상품 관련
  productAdded: (productName: string, onView: () => void) => ({
    type: 'success' as const,
    title: '상품 등록 완료',
    message: `"${productName}" 상품이 성공적으로 등록되었습니다.`,
    category: 'business' as const,
    actions: [
      { label: '상품 보기', action: onView, variant: 'contained' as const }
    ]
  }),

  productSyncStarted: (platformName: string) => ({
    type: 'loading' as const,
    title: '플랫폼 동기화 시작',
    message: `${platformName}와 상품 동기화를 시작합니다.`,
    category: 'business' as const,
    duration: 0,
    persistent: true
  }),

  // 주문 관련
  newOrder: (orderNumber: string, amount: number, onView: () => void) => ({
    type: 'info' as const,
    title: '새 주문 접수',
    message: `주문 ${orderNumber} (₩${amount.toLocaleString()})이 접수되었습니다.`,
    category: 'user' as const,
    actions: [
      { label: '주문 확인', action: onView, variant: 'contained' as const }
    ]
  }),

  // 시스템 관련
  backupCompleted: () => ({
    type: 'success' as const,
    title: '백업 완료',
    message: '데이터 백업이 성공적으로 완료되었습니다.',
    category: 'system' as const
  }),

  // 에러 관련
  apiError: (errorMessage: string, onRetry: () => void) => ({
    type: 'error' as const,
    title: 'API 연결 오류',
    message: errorMessage,
    category: 'system' as const,
    actions: [
      { label: '다시 시도', action: onRetry, variant: 'contained' as const, color: 'error' as const }
    ]
  })
}

export default NotificationCenter