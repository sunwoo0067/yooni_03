import React from 'react'
import { usePermissions } from './PermissionGuard'

interface ConditionalRenderProps {
  children: React.ReactNode
  /** Required permission(s) - user must have at least one */
  permissions?: string | string[]
  /** Required role(s) - user must have at least one */
  roles?: string | string[]
  /** Require all permissions instead of just one */
  requireAll?: boolean
  /** Render when condition is NOT met */
  fallback?: React.ReactNode
  /** Invert the condition (render when NOT authorized) */
  invert?: boolean
}

/**
 * ConditionalRender - Renders children based on user permissions/roles
 * 
 * Usage:
 * ```tsx
 * <ConditionalRender permissions="product.create">
 *   <CreateProductButton />
 * </ConditionalRender>
 * 
 * <ConditionalRender roles={['admin', 'manager']}>
 *   <AdminPanel />
 * </ConditionalRender>
 * 
 * <ConditionalRender 
 *   permissions={['product.edit', 'product.delete']} 
 *   requireAll
 * >
 *   <EditActions />
 * </ConditionalRender>
 * ```
 */
export default function ConditionalRender({
  children,
  permissions,
  roles,
  requireAll = false,
  fallback = null,
  invert = false,
}: ConditionalRenderProps) {
  const { hasPermission, hasRole, currentUser } = usePermissions()

  // If no user is logged in, don't render anything (unless inverted)
  if (!currentUser) {
    return invert ? <>{children}</> : <>{fallback}</>
  }

  // Check permissions
  const hasRequiredPermissions = permissions ? hasPermission(permissions, requireAll) : true

  // Check roles
  const hasRequiredRoles = roles ? hasRole(roles) : true

  // Determine if user has access
  const hasAccess = hasRequiredPermissions && hasRequiredRoles

  // Apply invert logic
  const shouldRender = invert ? !hasAccess : hasAccess

  return shouldRender ? <>{children}</> : <>{fallback}</>
}

// Specialized components for common use cases

interface ShowForPermissionProps {
  permission: string | string[]
  children: React.ReactNode
  fallback?: React.ReactNode
  requireAll?: boolean
}

export function ShowForPermission({ 
  permission, 
  children, 
  fallback = null,
  requireAll = false,
}: ShowForPermissionProps) {
  return (
    <ConditionalRender 
      permissions={permission} 
      requireAll={requireAll}
      fallback={fallback}
    >
      {children}
    </ConditionalRender>
  )
}

interface ShowForRoleProps {
  role: string | string[]
  children: React.ReactNode
  fallback?: React.ReactNode
}

export function ShowForRole({ role, children, fallback = null }: ShowForRoleProps) {
  return (
    <ConditionalRender roles={role} fallback={fallback}>
      {children}
    </ConditionalRender>
  )
}

interface HideForRoleProps {
  role: string | string[]
  children: React.ReactNode
  fallback?: React.ReactNode
}

export function HideForRole({ role, children, fallback = null }: HideForRoleProps) {
  return (
    <ConditionalRender roles={role} invert fallback={fallback}>
      {children}
    </ConditionalRender>
  )
}

// Specific role-based components
export function ShowForAdmin({ children, fallback = null }: { children: React.ReactNode; fallback?: React.ReactNode }) {
  return <ShowForRole role="admin" fallback={fallback}>{children}</ShowForRole>
}

export function ShowForManager({ children, fallback = null }: { children: React.ReactNode; fallback?: React.ReactNode }) {
  return <ShowForRole role={['admin', 'manager']} fallback={fallback}>{children}</ShowForRole>
}

export function ShowForUser({ children, fallback = null }: { children: React.ReactNode; fallback?: React.ReactNode }) {
  return <ShowForRole role="user" fallback={fallback}>{children}</ShowForRole>
}

export function HideForUser({ children, fallback = null }: { children: React.ReactNode; fallback?: React.ReactNode }) {
  return <HideForRole role="user" fallback={fallback}>{children}</HideForRole>
}

// Email verification conditional
export function ShowForVerifiedEmail({ children, fallback = null }: { children: React.ReactNode; fallback?: React.ReactNode }) {
  const { currentUser } = usePermissions()
  
  if (!currentUser) {
    return <>{fallback}</>
  }

  return currentUser.emailVerified ? <>{children}</> : <>{fallback}</>
}

export function ShowForUnverifiedEmail({ children, fallback = null }: { children: React.ReactNode; fallback?: React.ReactNode }) {
  const { currentUser } = usePermissions()
  
  if (!currentUser) {
    return <>{fallback}</>
  }

  return !currentUser.emailVerified ? <>{children}</> : <>{fallback}</>
}