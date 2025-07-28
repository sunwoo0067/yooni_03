import React from 'react'
import { Box, Typography, Paper, Button } from '@mui/material'
import { LockOutlined, ArrowBack } from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { useAppSelector } from '@store/hooks'
import { 
  selectCurrentUser, 
  selectUserPermissions, 
  selectUserRole 
} from '@store/slices/authSlice'

interface PermissionGuardProps {
  children: React.ReactNode
  /** Required permission(s) - user must have at least one */
  permissions?: string | string[]
  /** Required role(s) - user must have at least one */
  roles?: string | string[]
  /** Require all permissions instead of just one */
  requireAll?: boolean
  /** Custom fallback component */
  fallback?: React.ReactNode
  /** Show default unauthorized message */
  showUnauthorized?: boolean
}

const DefaultUnauthorizedMessage: React.FC<{ onGoBack?: () => void }> = ({ onGoBack }) => (
  <Box
    sx={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '400px',
      textAlign: 'center',
    }}
  >
    <Paper
      elevation={2}
      sx={{
        p: 4,
        maxWidth: 400,
        backgroundColor: 'grey.50',
        border: 1,
        borderColor: 'grey.200',
      }}
    >
      <LockOutlined 
        sx={{ 
          fontSize: 64, 
          color: 'text.secondary', 
          mb: 2 
        }} 
      />
      
      <Typography variant="h5" gutterBottom sx={{ fontWeight: 'bold' }}>
        접근 권한이 없습니다
      </Typography>
      
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        이 페이지에 접근할 권한이 없습니다.
        <br />
        관리자에게 문의하시거나 이전 페이지로 돌아가세요.
      </Typography>
      
      {onGoBack && (
        <Button 
          variant="contained" 
          startIcon={<ArrowBack />}
          onClick={onGoBack}
        >
          이전 페이지로
        </Button>
      )}
    </Paper>
  </Box>
)

export default function PermissionGuard({
  children,
  permissions,
  roles,
  requireAll = false,
  fallback,
  showUnauthorized = true,
}: PermissionGuardProps) {
  const navigate = useNavigate()
  const currentUser = useAppSelector(selectCurrentUser)
  const userPermissions = useAppSelector(selectUserPermissions)
  const userRole = useAppSelector(selectUserRole)

  // If no user is logged in, don't render anything
  if (!currentUser) {
    return null
  }

  // Check permissions
  const hasPermission = () => {
    if (!permissions) return true

    const requiredPermissions = Array.isArray(permissions) ? permissions : [permissions]
    
    if (requireAll) {
      return requiredPermissions.every(permission => 
        userPermissions.includes(permission)
      )
    } else {
      return requiredPermissions.some(permission => 
        userPermissions.includes(permission)
      )
    }
  }

  // Check roles
  const hasRole = () => {
    if (!roles) return true
    if (!userRole) return false

    const requiredRoles = Array.isArray(roles) ? roles : [roles]
    return requiredRoles.includes(userRole)
  }

  // Check if user has access
  const hasAccess = hasPermission() && hasRole()

  if (hasAccess) {
    return <>{children}</>
  }

  // Show fallback or default unauthorized message
  if (fallback) {
    return <>{fallback}</>
  }

  if (showUnauthorized) {
    return <DefaultUnauthorizedMessage onGoBack={() => navigate(-1)} />
  }

  return null
}

// Higher-order component version
export function withPermissionGuard<T extends object>(
  Component: React.ComponentType<T>,
  guardProps: Omit<PermissionGuardProps, 'children'>
) {
  return function PermissionGuardedComponent(props: T) {
    return (
      <PermissionGuard {...guardProps}>
        <Component {...props} />
      </PermissionGuard>
    )
  }
}

// Utility hook for checking permissions in components
export function usePermissions() {
  const currentUser = useAppSelector(selectCurrentUser)
  const userPermissions = useAppSelector(selectUserPermissions)
  const userRole = useAppSelector(selectUserRole)

  const hasPermission = (permission: string | string[], requireAll = false) => {
    if (!currentUser) return false
    
    const permissions = Array.isArray(permission) ? permission : [permission]
    
    if (requireAll) {
      return permissions.every(p => userPermissions.includes(p))
    } else {
      return permissions.some(p => userPermissions.includes(p))
    }
  }

  const hasRole = (role: string | string[]) => {
    if (!currentUser || !userRole) return false
    
    const roles = Array.isArray(role) ? role : [role]
    return roles.includes(userRole)
  }

  const hasAnyRole = (roles: string[]) => {
    if (!currentUser || !userRole) return false
    return roles.includes(userRole)
  }

  const isAdmin = () => hasRole('admin')
  const isManager = () => hasRole(['admin', 'manager'])
  const isUser = () => hasRole('user')

  return {
    hasPermission,
    hasRole,
    hasAnyRole,
    isAdmin,
    isManager,
    isUser,
    currentUser,
    userPermissions,
    userRole,
  }
}