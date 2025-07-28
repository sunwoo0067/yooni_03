import React, { useEffect } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { Box, CircularProgress, Typography } from '@mui/material'
import { useAppSelector, useAppDispatch } from '@store/hooks'
import { 
  selectIsAuthenticated, 
  selectAuthLoading, 
  selectCurrentUser,
  selectAuthToken,
  fetchCurrentUser,
} from '@store/slices/authSlice'
import PermissionGuard from './PermissionGuard'

interface ProtectedRouteProps {
  children: React.ReactNode
  /** Required permission(s) - user must have at least one */
  permissions?: string | string[]
  /** Required role(s) - user must have at least one */
  roles?: string | string[]
  /** Require all permissions instead of just one */
  requireAll?: boolean
  /** Redirect to this path if not authenticated */
  redirectTo?: string
  /** Require email verification */
  requireEmailVerification?: boolean
}

const LoadingScreen: React.FC = () => (
  <Box
    sx={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      gap: 2,
    }}
  >
    <CircularProgress size={60} />
    <Typography variant="h6" color="text.secondary">
      인증 확인 중...
    </Typography>
  </Box>
)

export default function ProtectedRoute({
  children,
  permissions,
  roles,
  requireAll = false,
  redirectTo = '/auth/login',
  requireEmailVerification = false,
}: ProtectedRouteProps) {
  const dispatch = useAppDispatch()
  const location = useLocation()
  
  const isAuthenticated = useAppSelector(selectIsAuthenticated)
  const isLoading = useAppSelector(selectAuthLoading)
  const currentUser = useAppSelector(selectCurrentUser)
  const token = useAppSelector(selectAuthToken)

  // Fetch current user if we have a token but no user data
  useEffect(() => {
    if (token && !currentUser && !isLoading) {
      dispatch(fetchCurrentUser())
    }
  }, [token, currentUser, isLoading, dispatch])

  // Show loading screen while checking authentication
  if (isLoading) {
    return <LoadingScreen />
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated || !currentUser) {
    return (
      <Navigate
        to={redirectTo}
        state={{ from: location.pathname }}
        replace
      />
    )
  }

  // Check email verification if required
  if (requireEmailVerification && !currentUser.emailVerified) {
    return (
      <Navigate
        to="/auth/verify-email"
        state={{ from: location.pathname }}
        replace
      />
    )
  }

  // If no specific permissions or roles required, render children
  if (!permissions && !roles) {
    return <>{children}</>
  }

  // Wrap with permission guard for role/permission checking
  return (
    <PermissionGuard
      permissions={permissions}
      roles={roles}
      requireAll={requireAll}
      showUnauthorized
    >
      {children}
    </PermissionGuard>
  )
}

// Utility component for admin-only routes
export function AdminRoute({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute roles="admin" requireEmailVerification>
      {children}
    </ProtectedRoute>
  )
}

// Utility component for manager+ routes
export function ManagerRoute({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute roles={['admin', 'manager']} requireEmailVerification>
      {children}
    </ProtectedRoute>
  )
}

// Utility component for authenticated routes with email verification
export function AuthenticatedRoute({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute requireEmailVerification>
      {children}
    </ProtectedRoute>
  )
}