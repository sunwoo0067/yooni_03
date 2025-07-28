import React, { useState } from 'react'
import {
  SpeedDial,
  SpeedDialAction,
  SpeedDialIcon,
  Box,
  Fab,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Typography,
  Badge,
  useTheme,
  useMediaQuery,
} from '@mui/material'
import {
  Add,
  Edit,
  Close,
  ShoppingCart,
  Inventory,
  People,
  Analytics,
  Settings,
  Sync,
  Upload,
  Download,
  Notifications,
} from '@mui/icons-material'
import { motion, AnimatePresence } from 'framer-motion'
import { useHotkeys } from 'react-hotkeys-hook'

export interface QuickAction {
  id: string
  icon: React.ReactNode
  name: string
  action: () => void
  color?: 'primary' | 'secondary' | 'error' | 'warning' | 'info' | 'success'
  badge?: number | string
  disabled?: boolean
  shortcut?: string
}

interface QuickActionsProps {
  actions: QuickAction[]
  position?: {
    vertical: 'top' | 'bottom'
    horizontal: 'left' | 'center' | 'right'
  }
  variant?: 'speedDial' | 'fab' | 'menu'
  size?: 'small' | 'medium' | 'large'
  alwaysVisible?: boolean
}

export const QuickActions: React.FC<QuickActionsProps> = ({
  actions,
  position = { vertical: 'bottom', horizontal: 'right' },
  variant = 'speedDial',
  size = 'medium',
  alwaysVisible = false,
}) => {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
  const [open, setOpen] = useState(false)
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null)

  // 키보드 단축키 등록
  actions.forEach((action) => {
    if (action.shortcut) {
      useHotkeys(action.shortcut, (e) => {
        e.preventDefault()
        action.action()
      })
    }
  })

  // 빠른 액션 토글 단축키
  useHotkeys('cmd+shift+a, ctrl+shift+a', (e) => {
    e.preventDefault()
    if (variant === 'speedDial') {
      setOpen(!open)
    } else if (variant === 'menu') {
      if (menuAnchor) {
        setMenuAnchor(null)
      } else {
        // FAB 찾아서 열기
        const fabElement = document.querySelector('[data-quick-actions-fab]') as HTMLElement
        if (fabElement) {
          setMenuAnchor(fabElement)
        }
      }
    }
  })

  const handleAction = (action: QuickAction) => {
    action.action()
    setOpen(false)
    setMenuAnchor(null)
  }

  const getPositionStyles = () => {
    const styles: React.CSSProperties = {
      position: 'fixed',
      zIndex: 1200,
    }

    // Vertical position
    if (position.vertical === 'top') {
      styles.top = 16
    } else {
      styles.bottom = 16
    }

    // Horizontal position
    if (position.horizontal === 'left') {
      styles.left = 16
    } else if (position.horizontal === 'center') {
      styles.left = '50%'
      styles.transform = 'translateX(-50%)'
    } else {
      styles.right = 16
    }

    return styles
  }

  // SpeedDial 모드
  if (variant === 'speedDial') {
    return (
      <SpeedDial
        ariaLabel="빠른 작업"
        sx={getPositionStyles()}
        icon={<SpeedDialIcon openIcon={<Close />} />}
        open={open}
        onOpen={() => setOpen(true)}
        onClose={() => setOpen(false)}
        FabProps={{
          size: size as any,
          color: 'primary',
        }}
      >
        {actions.map((action, index) => (
          <SpeedDialAction
            key={action.id}
            icon={
              action.badge ? (
                <Badge badgeContent={action.badge} color="error">
                  {action.icon}
                </Badge>
              ) : (
                action.icon
              )
            }
            tooltipTitle={
              <Box>
                <Typography variant="body2">{action.name}</Typography>
                {action.shortcut && (
                  <Typography variant="caption" color="text.secondary">
                    {action.shortcut}
                  </Typography>
                )}
              </Box>
            }
            onClick={() => handleAction(action)}
            FabProps={{
              disabled: action.disabled,
              color: action.color || 'default',
            }}
            sx={{
              // 애니메이션 효과
              '& .MuiSpeedDialAction-fab': {
                animation: open ? 'bounce 0.3s ease-out' : 'none',
                animationDelay: `${index * 0.05}s`,
                '@keyframes bounce': {
                  '0%': { transform: 'scale(0)' },
                  '50%': { transform: 'scale(1.1)' },
                  '100%': { transform: 'scale(1)' },
                },
              },
            }}
          />
        ))}
      </SpeedDial>
    )
  }

  // Menu 모드
  if (variant === 'menu') {
    return (
      <>
        <Fab
          color="primary"
          size={size}
          onClick={(e) => setMenuAnchor(e.currentTarget)}
          sx={getPositionStyles()}
          data-quick-actions-fab
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={menuAnchor ? 'close' : 'add'}
              initial={{ rotate: 0 }}
              animate={{ rotate: menuAnchor ? 45 : 0 }}
              exit={{ rotate: 0 }}
              transition={{ duration: 0.2 }}
            >
              {menuAnchor ? <Close /> : <Add />}
            </motion.div>
          </AnimatePresence>
        </Fab>

        <Menu
          anchorEl={menuAnchor}
          open={Boolean(menuAnchor)}
          onClose={() => setMenuAnchor(null)}
          anchorOrigin={{
            vertical: position.vertical === 'top' ? 'bottom' : 'top',
            horizontal: position.horizontal === 'left' ? 'right' : 'left',
          }}
          transformOrigin={{
            vertical: position.vertical === 'top' ? 'top' : 'bottom',
            horizontal: position.horizontal === 'left' ? 'left' : 'right',
          }}
          PaperProps={{
            sx: {
              minWidth: 200,
              maxHeight: 400,
            },
          }}
        >
          <Box sx={{ px: 2, py: 1 }}>
            <Typography variant="caption" color="text.secondary">
              빠른 작업
            </Typography>
          </Box>
          <Divider />
          {actions.map((action, index) => (
            <React.Fragment key={action.id}>
              {index > 0 && index % 4 === 0 && <Divider />}
              <MenuItem
                onClick={() => handleAction(action)}
                disabled={action.disabled}
              >
                <ListItemIcon>
                  {action.badge ? (
                    <Badge badgeContent={action.badge} color="error">
                      {action.icon}
                    </Badge>
                  ) : (
                    action.icon
                  )}
                </ListItemIcon>
                <ListItemText
                  primary={action.name}
                  secondary={action.shortcut}
                />
              </MenuItem>
            </React.Fragment>
          ))}
        </Menu>
      </>
    )
  }

  // FAB 모드 (단일 버튼)
  return (
    <Fab
      color="primary"
      size={size}
      onClick={() => actions[0]?.action()}
      sx={getPositionStyles()}
      disabled={actions[0]?.disabled}
    >
      {actions[0]?.badge ? (
        <Badge badgeContent={actions[0].badge} color="error">
          {actions[0]?.icon || <Add />}
        </Badge>
      ) : (
        actions[0]?.icon || <Add />
      )}
    </Fab>
  )
}

// 미리 정의된 액션 세트
export const defaultQuickActions: QuickAction[] = [
  {
    id: 'add-product',
    icon: <Inventory />,
    name: '상품 추가',
    action: () => console.log('상품 추가'),
    color: 'primary',
    shortcut: 'cmd+shift+p',
  },
  {
    id: 'add-order',
    icon: <ShoppingCart />,
    name: '주문 추가',
    action: () => console.log('주문 추가'),
    color: 'secondary',
    shortcut: 'cmd+shift+o',
  },
  {
    id: 'add-customer',
    icon: <People />,
    name: '고객 추가',
    action: () => console.log('고객 추가'),
    color: 'info',
    shortcut: 'cmd+shift+c',
  },
  {
    id: 'sync',
    icon: <Sync />,
    name: '동기화',
    action: () => console.log('동기화'),
    badge: 3,
  },
  {
    id: 'analytics',
    icon: <Analytics />,
    name: '분석',
    action: () => console.log('분석'),
  },
]

export default QuickActions