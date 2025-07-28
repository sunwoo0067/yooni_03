import React, { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Checkbox,
  CircularProgress,
  Alert,
  LinearProgress,
  Chip,
} from '@mui/material'
import { CloudSync, Store, Error, CheckCircle } from '@mui/icons-material'
import { toast } from 'react-hot-toast'

interface PlatformSyncDialogProps {
  open: boolean
  onClose: () => void
}

interface Platform {
  id: string
  name: string
  icon: string
  status: 'idle' | 'syncing' | 'success' | 'error'
  message?: string
}

const PlatformSyncDialog: React.FC<PlatformSyncDialogProps> = ({ open, onClose }) => {
  const [platforms, setPlatforms] = useState<Platform[]>([
    { id: 'coupang', name: '쿠팡', icon: '🛒', status: 'idle' },
    { id: 'naver', name: '네이버 스마트스토어', icon: '🟢', status: 'idle' },
    { id: '11st', name: '11번가', icon: '1️⃣', status: 'idle' },
    { id: 'gmarket', name: 'G마켓', icon: '🅶', status: 'idle' },
  ])
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['coupang', 'naver'])
  const [syncing, setSyncing] = useState(false)

  const handleTogglePlatform = (platformId: string) => {
    setSelectedPlatforms(prev =>
      prev.includes(platformId)
        ? prev.filter(id => id !== platformId)
        : [...prev, platformId]
    )
  }

  const handleSync = async () => {
    setSyncing(true)
    
    // Simulate syncing process
    for (const platform of platforms) {
      if (selectedPlatforms.includes(platform.id)) {
        setPlatforms(prev =>
          prev.map(p =>
            p.id === platform.id ? { ...p, status: 'syncing' } : p
          )
        )
        
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 1500))
        
        // Random success/error
        const isSuccess = Math.random() > 0.2
        setPlatforms(prev =>
          prev.map(p =>
            p.id === platform.id
              ? {
                  ...p,
                  status: isSuccess ? 'success' : 'error',
                  message: isSuccess
                    ? '동기화 완료'
                    : '연결 오류가 발생했습니다',
                }
              : p
          )
        )
      }
    }
    
    setSyncing(false)
    toast.success('플랫폼 동기화가 완료되었습니다.')
  }

  const getStatusIcon = (status: Platform['status']) => {
    switch (status) {
      case 'syncing':
        return <CircularProgress size={20} />
      case 'success':
        return <CheckCircle color="success" />
      case 'error':
        return <Error color="error" />
      default:
        return <CloudSync />
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>플랫폼 동기화</DialogTitle>
      <DialogContent>
        <Alert severity="info" sx={{ mb: 2 }}>
          선택한 플랫폼으로 상품 정보를 동기화합니다.
        </Alert>
        
        <List>
          {platforms.map((platform) => (
            <ListItem key={platform.id}>
              <ListItemIcon>
                <Checkbox
                  checked={selectedPlatforms.includes(platform.id)}
                  onChange={() => handleTogglePlatform(platform.id)}
                  disabled={syncing}
                />
              </ListItemIcon>
              <ListItemText
                primary={
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography>{platform.icon}</Typography>
                    <Typography>{platform.name}</Typography>
                    {platform.status !== 'idle' && (
                      <Chip
                        label={platform.message || platform.status}
                        size="small"
                        color={
                          platform.status === 'success' ? 'success' :
                          platform.status === 'error' ? 'error' : 'default'
                        }
                      />
                    )}
                  </Box>
                }
              />
              <ListItemIcon>
                {getStatusIcon(platform.status)}
              </ListItemIcon>
            </ListItem>
          ))}
        </List>
        
        {syncing && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" gutterBottom>
              동기화 진행 중...
            </Typography>
            <LinearProgress />
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={syncing}>
          닫기
        </Button>
        <Button
          onClick={handleSync}
          variant="contained"
          disabled={syncing || selectedPlatforms.length === 0}
          startIcon={<CloudSync />}
        >
          동기화 시작
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default PlatformSyncDialog