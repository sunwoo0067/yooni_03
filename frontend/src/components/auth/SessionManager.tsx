import React, { useEffect, useState, useCallback } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  LinearProgress,
  Box,
  Alert,
} from '@mui/material'
import { Warning, Timer } from '@mui/icons-material'
import { useAppSelector, useAppDispatch } from '@store/hooks'
import {
  selectSessionTimeRemaining,
  selectIsSessionExpiringSoon,
  selectSessionWarningShown,
  selectIsAuthenticated,
  setSessionWarningShown,
  refreshToken,
  logout,
} from '@store/slices/authSlice'
import toast from 'react-hot-toast'

interface SessionManagerProps {
  /** Warning time in minutes before session expires */
  warningMinutes?: number
  /** Auto-refresh token when expiring soon */
  autoRefresh?: boolean
  /** Show countdown in dialog */
  showCountdown?: boolean
}

export default function SessionManager({
  warningMinutes = 5,
  autoRefresh = true,
  showCountdown = true,
}: SessionManagerProps) {
  const dispatch = useAppDispatch()
  const isAuthenticated = useAppSelector(selectIsAuthenticated)
  const timeRemaining = useAppSelector(selectSessionTimeRemaining)
  const isExpiringSoon = useAppSelector(selectIsSessionExpiringSoon)
  const warningShown = useAppSelector(selectSessionWarningShown)
  
  const [showWarningDialog, setShowWarningDialog] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const [autoRefreshAttempted, setAutoRefreshAttempted] = useState(false)

  // Update countdown every second
  useEffect(() => {
    if (showWarningDialog && timeRemaining > 0) {
      const timer = setInterval(() => {
        setCountdown(Math.floor(timeRemaining / 1000))
      }, 1000)

      return () => clearInterval(timer)
    }
  }, [showWarningDialog, timeRemaining])

  // Handle session expiration warning
  useEffect(() => {
    if (isAuthenticated && isExpiringSoon && !warningShown) {
      // Try auto-refresh first if enabled
      if (autoRefresh && !autoRefreshAttempted) {
        handleRefreshToken()
        setAutoRefreshAttempted(true)
      } else {
        // Show warning dialog
        setShowWarningDialog(true)
        setCountdown(Math.floor(timeRemaining / 1000))
        dispatch(setSessionWarningShown(true))
      }
    }
  }, [isAuthenticated, isExpiringSoon, warningShown, autoRefresh, autoRefreshAttempted, timeRemaining, dispatch])

  // Handle session expiration
  useEffect(() => {
    if (isAuthenticated && timeRemaining <= 0) {
      handleSessionExpired()
    }
  }, [isAuthenticated, timeRemaining])

  // Reset auto-refresh flag when session is refreshed
  useEffect(() => {
    if (!isExpiringSoon) {
      setAutoRefreshAttempted(false)
    }
  }, [isExpiringSoon])

  const handleRefreshToken = useCallback(async () => {
    try {
      await dispatch(refreshToken()).unwrap()
      setShowWarningDialog(false)
      dispatch(setSessionWarningShown(false))
      toast.success('세션이 자동으로 연장되었습니다.')
    } catch (error) {
      console.error('Token refresh failed:', error)
      toast.error('세션 연장에 실패했습니다. 다시 로그인해주세요.')
      handleSessionExpired()
    }
  }, [dispatch])

  const handleSessionExpired = useCallback(() => {
    setShowWarningDialog(false)
    dispatch(logout())
    toast.error('세션이 만료되었습니다. 다시 로그인해주세요.')
  }, [dispatch])

  const handleExtendSession = () => {
    handleRefreshToken()
  }

  const handleLogoutNow = () => {
    setShowWarningDialog(false)
    dispatch(logout())
  }

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}분 ${remainingSeconds}초`
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <Dialog
      open={showWarningDialog}
      onClose={() => {}} // Prevent closing by clicking outside
      maxWidth="sm"
      fullWidth
      disableEscapeKeyDown
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Warning color="warning" />
        세션 만료 경고
      </DialogTitle>
      
      <DialogContent>
        <Alert severity="warning" sx={{ mb: 2 }}>
          보안을 위해 일정 시간 후 자동으로 로그아웃됩니다.
        </Alert>

        <Typography variant="body1" gutterBottom>
          현재 세션이 곧 만료됩니다. 계속 작업하시려면 세션을 연장해주세요.
        </Typography>

        {showCountdown && countdown > 0 && (
          <Box sx={{ mt: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <Timer color="action" />
              <Typography variant="body2" color="text.secondary">
                남은 시간: {formatTime(countdown)}
              </Typography>
            </Box>
            
            <LinearProgress
              variant="determinate"
              value={Math.max(0, (countdown / (warningMinutes * 60)) * 100)}
              sx={{
                height: 8,
                borderRadius: 4,
                bgcolor: 'grey.200',
                '& .MuiLinearProgress-bar': {
                  bgcolor: countdown > 60 ? 'warning.main' : 'error.main',
                },
              }}
            />
          </Box>
        )}

        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          세션을 연장하지 않으면 자동으로 로그아웃되며, 저장하지 않은 작업은 손실될 수 있습니다.
        </Typography>
      </DialogContent>

      <DialogActions sx={{ p: 2, gap: 1 }}>
        <Button
          onClick={handleLogoutNow}
          color="inherit"
          variant="outlined"
        >
          지금 로그아웃
        </Button>
        <Button
          onClick={handleExtendSession}
          color="primary"
          variant="contained"
          autoFocus
        >
          세션 연장
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// Hook for manual session management
export function useSessionManager() {
  const dispatch = useAppDispatch()
  const timeRemaining = useAppSelector(selectSessionTimeRemaining)
  const isExpiringSoon = useAppSelector(selectIsSessionExpiringSoon)

  const refreshSession = useCallback(async () => {
    try {
      await dispatch(refreshToken()).unwrap()
      return { success: true }
    } catch (error) {
      return { success: false, error }
    }
  }, [dispatch])

  const logoutUser = useCallback(() => {
    dispatch(logout())
  }, [dispatch])

  const getTimeRemainingText = useCallback(() => {
    if (timeRemaining <= 0) return '만료됨'
    
    const minutes = Math.floor(timeRemaining / (1000 * 60))
    const seconds = Math.floor((timeRemaining % (1000 * 60)) / 1000)
    
    if (minutes > 0) {
      return `${minutes}분 ${seconds}초`
    } else {
      return `${seconds}초`
    }
  }, [timeRemaining])

  return {
    timeRemaining,
    isExpiringSoon,
    refreshSession,
    logoutUser,
    getTimeRemainingText,
  }
}