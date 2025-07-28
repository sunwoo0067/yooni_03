import React from 'react'
import {
  Card as MuiCard,
  CardProps as MuiCardProps,
  CardContent,
  CardActions,
  Typography,
  Box,
  IconButton,
  Skeleton,
  useTheme,
} from '@mui/material'
import { MoreVert, Refresh } from '@mui/icons-material'
import { motion, AnimatePresence } from 'framer-motion'

interface CardProps {
  title?: React.ReactNode
  subtitle?: string
  icon?: React.ReactNode
  actions?: React.ReactNode
  children: React.ReactNode
  loading?: boolean
  onRefresh?: () => void
  onMenuClick?: (event: React.MouseEvent<HTMLElement>) => void
  onClick?: () => void
  draggable?: boolean
  dragHandleProps?: any
  animate?: boolean
  variant?: 'default' | 'gradient' | 'outlined' | 'glass'
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info'
  sx?: any
  elevation?: number
  className?: string
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(({
  title,
  subtitle,
  icon,
  actions,
  children,
  loading = false,
  onRefresh,
  onMenuClick,
  onClick,
  draggable = false,
  dragHandleProps,
  animate = true,
  variant = 'default',
  color = 'primary',
  sx,
  elevation,
  className,
}, ref) => {
  const theme = useTheme()

  const getVariantStyles = () => {
    switch (variant) {
      case 'gradient':
        return {
          background: `linear-gradient(135deg, ${theme.palette[color].light} 0%, ${theme.palette[color].main} 100%)`,
          color: theme.palette.common.white,
          '& .MuiTypography-root': {
            color: theme.palette.common.white,
          },
        }
      case 'outlined':
        return {
          border: `2px solid ${theme.palette[color].main}`,
          background: 'transparent',
        }
      case 'glass':
        return {
          background: 'rgba(255, 255, 255, 0.1)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255, 255, 255, 0.2)',
        }
      default:
        return {}
    }
  }

  const cardContent = (
    <MuiCard
      ref={ref}
      elevation={elevation}
      className={className}
      variant={variant === 'outlined' ? 'outlined' : 'elevation'}
      onClick={onClick}
      sx={{
        position: 'relative',
        overflow: 'visible',
        transition: 'all 0.3s ease',
        cursor: draggable ? 'move' : onClick ? 'pointer' : 'default',
        '&:hover': {
          transform: animate ? 'translateY(-4px)' : 'none',
          boxShadow: animate ? theme.shadows[8] : theme.shadows[2],
        },
        ...getVariantStyles(),
        ...sx,
      }}
      {...(draggable ? dragHandleProps : {})}
    >
      {(title || icon || onRefresh || onMenuClick) && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            p: 2,
            pb: 0,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {icon && (
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: 40,
                  height: 40,
                  borderRadius: 2,
                  backgroundColor: variant === 'gradient' ? 'rgba(255,255,255,0.2)' : `${color}.100`,
                  color: variant === 'gradient' ? 'inherit' : `${color}.main`,
                }}
              >
                {icon}
              </Box>
            )}
            {title && (
              <Box>
                <Typography variant="h6" fontWeight="bold">
                  {title}
                </Typography>
                {subtitle && (
                  <Typography variant="body2" color="text.secondary">
                    {subtitle}
                  </Typography>
                )}
              </Box>
            )}
          </Box>
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            {onRefresh && (
              <IconButton size="small" onClick={onRefresh}>
                <Refresh fontSize="small" />
              </IconButton>
            )}
            {onMenuClick && (
              <IconButton size="small" onClick={onMenuClick}>
                <MoreVert fontSize="small" />
              </IconButton>
            )}
          </Box>
        </Box>
      )}
      <CardContent sx={{ p: 2 }}>
        {loading ? (
          <Box>
            <Skeleton variant="text" width="60%" />
            <Skeleton variant="text" width="80%" />
            <Skeleton variant="rectangular" height={100} sx={{ mt: 2 }} />
          </Box>
        ) : (
          children
        )}
      </CardContent>
      {actions && (
        <CardActions sx={{ p: 2, pt: 0, justifyContent: 'flex-end' }}>
          {actions}
        </CardActions>
      )}
    </MuiCard>
  )

  if (animate) {
    return (
      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
        >
          {cardContent}
        </motion.div>
      </AnimatePresence>
    )
  }

  return cardContent
})

// 통계 카드 컴포넌트
interface StatCardProps {
  title: string
  value: string | number
  change?: number
  icon?: React.ReactNode
  color?: CardProps['color']
  loading?: boolean
  onClick?: () => void
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  change,
  icon,
  color = 'primary',
  loading = false,
  onClick,
}) => {
  const theme = useTheme()

  return (
    <Card
      sx={{
        cursor: onClick ? 'pointer' : 'default',
        '&:hover': onClick ? {
          transform: 'translateY(-4px)',
          boxShadow: theme.shadows[8],
        } : {},
      }}
      onClick={onClick}
      loading={loading}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box sx={{ flex: 1 }}>
          <Typography color="text.secondary" variant="body2" gutterBottom>
            {title}
          </Typography>
          <Typography variant="h4" fontWeight="bold" sx={{ mb: 1 }}>
            {value}
          </Typography>
          {change !== undefined && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Box
                component="span"
                sx={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  px: 1,
                  py: 0.5,
                  borderRadius: 1,
                  fontSize: '0.75rem',
                  fontWeight: 'bold',
                  backgroundColor: change >= 0 ? 'success.100' : 'error.100',
                  color: change >= 0 ? 'success.dark' : 'error.dark',
                }}
              >
                {change >= 0 ? '+' : ''}{change}%
              </Box>
              <Typography variant="caption" color="text.secondary">
                지난주 대비
              </Typography>
            </Box>
          )}
        </Box>
        {icon && (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 56,
              height: 56,
              borderRadius: 2,
              backgroundColor: `${color}.100`,
              color: `${color}.main`,
            }}
          >
            {icon}
          </Box>
        )}
      </Box>
    </Card>
  )
}

export default Card