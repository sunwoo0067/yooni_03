import React, { useState, useCallback } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  CardActions,
  IconButton,
  Menu,
  MenuItem,
  Chip,
  Avatar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  Alert,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  ListItemSecondaryAction,
  Switch,
  Tooltip,
  Badge,
  LinearProgress,
  Divider,
} from '@mui/material'
import {
  Add,
  MoreVert,
  Edit,
  Delete,
  Sync,
  CheckCircle,
  Error,
  Warning,
  Settings,
  Key,
  Store,
  Link as LinkIcon,
  CloudSync,
  Refresh,
  Security,
  Schedule,
  TrendingUp,
} from '@mui/icons-material'
import { toast } from 'react-hot-toast'
import { formatDate } from '@utils/format'
import EmptyState, { PlatformsEmptyState } from '@components/ui/EmptyState'
import { PlatformCardSkeleton } from '@components/ui/Skeleton'
import { useNotification, BusinessNotifications } from '@components/ui/NotificationSystem'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { platformAPI } from '@services/api'
import { websocketService } from '@services/websocket'

interface PlatformAccount {
  id: string
  platform: 'coupang' | 'naver' | 'gmarket' | '11st' | 'wemakeprice' | 'tmon'
  name: string
  accountId: string
  status: 'active' | 'inactive' | 'error' | 'suspended'
  isConnected: boolean
  lastSync?: string
  syncStatus?: 'idle' | 'syncing' | 'success' | 'error'
  syncInterval: number // minutes
  autoSync: boolean
  credentials: {
    apiKey?: string
    secretKey?: string
    accessToken?: string
    refreshToken?: string
  }
  statistics?: {
    totalProducts: number
    activeListings: number
    totalOrders: number
    monthlyRevenue: number
  }
  createdAt: string
  updatedAt: string
}

const PlatformAccounts: React.FC = () => {
  const queryClient = useQueryClient()
  const notification = useNotification()
  const [syncingPlatforms, setSyncingPlatforms] = useState<Set<string>>(new Set())
  const [selectedAccount, setSelectedAccount] = useState<PlatformAccount | null>(null)
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [formData, setFormData] = useState({
    platform: '',
    name: '',
    accountId: '',
    apiKey: '',
    secretKey: '',
    syncInterval: 60,
    autoSync: true,
  })

  // Platform configurations
  const platformConfig = {
    coupang: {
      name: '쿠팡',
      color: '#D73502',
      logo: '/images/platforms/coupang.png',
      fields: ['apiKey', 'secretKey'],
    },
    naver: {
      name: '네이버 스마트스토어',
      color: '#03C75A',
      logo: '/images/platforms/naver.png',
      fields: ['apiKey', 'secretKey', 'accountId'],
    },
    gmarket: {
      name: 'G마켓',
      color: '#6FC043',
      logo: '/images/platforms/gmarket.png',
      fields: ['apiKey', 'secretKey'],
    },
    '11st': {
      name: '11번가',
      color: '#E5352C',
      logo: '/images/platforms/11st.png',
      fields: ['apiKey', 'accessToken'],
    },
    wemakeprice: {
      name: '위메프',
      color: '#FF5000',
      logo: '/images/platforms/wemakeprice.png',
      fields: ['apiKey', 'secretKey'],
    },
    tmon: {
      name: '티몬',
      color: '#F54F3D',
      logo: '/images/platforms/tmon.png',
      fields: ['apiKey', 'secretKey'],
    },
  }

  // 실제 API에서 플랫폼 계정 목록 조회
  const { data: accounts = [], isLoading } = useQuery({
    queryKey: ['platforms'],
    queryFn: async () => {
      const response = await platformAPI.getAccounts()
      // API 응답 형식을 컴포넌트 형식으로 변환
      return response.data.map((account: any) => ({
        id: account.id,
        platform: account.platform,
        name: account.name,
        accountId: account.account_id,
        status: account.status,
        isConnected: account.is_connected,
        lastSync: account.last_sync,
        syncStatus: account.sync_status,
        syncInterval: account.sync_interval,
        autoSync: account.auto_sync,
        credentials: {
          apiKey: '••••••••',
          secretKey: '••••••••',
        },
        statistics: {
          totalProducts: 0,
          activeListings: 0,
          totalOrders: 0,
          monthlyRevenue: 0,
        },
        createdAt: account.created_at,
        updatedAt: account.updated_at,
      }))
    },
  })

  // 플랫폼 동기화 mutation
  const syncMutation = useMutation({
    mutationFn: async (platformId: string) => {
      const response = await platformAPI.syncAccount(platformId)
      return response.data
    },
    onSuccess: (data, platformId) => {
      setSyncingPlatforms(prev => new Set(prev).add(platformId))
      notification.showInfo('동기화 시작', data.message)
    },
    onError: (error: any) => {
      notification.showError('동기화 실패', error.response?.data?.message || '동기화를 시작할 수 없습니다.')
    },
  })

  // WebSocket 메시지 처리
  React.useEffect(() => {
    const unsubscribe = websocketService.on('data_change', (message) => {
      if (message.changeType === 'platform_sync') {
        const { platform_id, status } = message.data
        
        if (status === 'completed' || status === 'failed') {
          setSyncingPlatforms(prev => {
            const newSet = new Set(prev)
            newSet.delete(platform_id)
            return newSet
          })
          
          // 플랫폼 목록 새로고침
          queryClient.invalidateQueries({ queryKey: ['platforms'] })
          
          if (status === 'completed') {
            notification.showSuccess('동기화 완료', `${message.data.platform} 동기화가 완료되었습니다.`)
          } else {
            notification.showError('동기화 실패', `${message.data.platform} 동기화가 실패했습니다.`)
          }
        }
      } else if (message.changeType === 'inventory_updated') {
        notification.showInfo(
          '재고 업데이트',
          `${message.data.platform}에서 ${message.data.updated_count}개 상품의 재고가 업데이트되었습니다.`
        )
      }
    })

    return () => {
      unsubscribe()
    }
  }, [notification, queryClient])

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, account: PlatformAccount) => {
    setAnchorEl(event.currentTarget)
    setSelectedAccount(account)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
  }

  const handleAddAccount = () => {
    setEditMode(false)
    setFormData({
      platform: '',
      name: '',
      accountId: '',
      apiKey: '',
      secretKey: '',
      syncInterval: 60,
      autoSync: true,
    })
    setDialogOpen(true)
  }

  const handleEditAccount = () => {
    if (selectedAccount) {
      setEditMode(true)
      setFormData({
        platform: selectedAccount.platform,
        name: selectedAccount.name,
        accountId: selectedAccount.accountId,
        apiKey: '',
        secretKey: '',
        syncInterval: selectedAccount.syncInterval,
        autoSync: selectedAccount.autoSync,
      })
      setDialogOpen(true)
      handleMenuClose()
    }
  }

  const handleDeleteAccount = () => {
    if (selectedAccount) {
      if (window.confirm(`${selectedAccount.name} 계정을 삭제하시겠습니까?`)) {
        // TODO: 실제 API 호출로 변경 필요
        toast.success('계정이 삭제되었습니다.')
        queryClient.invalidateQueries({ queryKey: ['platforms'] })
      }
      handleMenuClose()
    }
  }

  const handleSaveAccount = () => {
    if (!formData.platform || !formData.name) {
      toast.error('필수 정보를 입력해주세요.')
      return
    }

    if (editMode && selectedAccount) {
      // TODO: 실제 API 호출로 변경 필요
      toast.success('계정 정보가 업데이트되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['platforms'] })
    } else {
      // TODO: 실제 API 호출로 변경 필요
      toast.success('새 계정이 추가되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['platforms'] })
    }

    setDialogOpen(false)
  }

  const handleSyncAccount = async (account: PlatformAccount) => {
    if (!syncingPlatforms.has(account.id) && account.syncStatus !== 'syncing') {
      syncMutation.mutate(account.id)
    }
  }

  const handleToggleAutoSync = (account: PlatformAccount) => {
    // 실제 API 호출로 변경 필요
    toast.success(`자동 동기화가 ${account.autoSync ? '비활성화' : '활성화'}되었습니다.`)
    queryClient.invalidateQueries({ queryKey: ['platforms'] })
  }

  const getStatusIcon = (status: PlatformAccount['status']) => {
    switch (status) {
      case 'active':
        return <CheckCircle color="success" />
      case 'error':
        return <Error color="error" />
      case 'inactive':
        return <Warning color="warning" />
      case 'suspended':
        return <Error color="error" />
      default:
        return null
    }
  }

  const getStatusLabel = (status: PlatformAccount['status']) => {
    switch (status) {
      case 'active':
        return '활성'
      case 'error':
        return '오류'
      case 'inactive':
        return '비활성'
      case 'suspended':
        return '일시중지'
      default:
        return status
    }
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" gutterBottom>
            플랫폼 계정 관리
          </Typography>
          <Typography variant="body1" color="text.secondary">
            판매 플랫폼 계정을 연결하고 관리하세요
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={handleAddAccount}
        >
          계정 추가
        </Button>
      </Box>

      {/* Account Summary */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" variant="body2">
                    전체 계정
                  </Typography>
                  <Typography variant="h4">
                    {accounts.length}
                  </Typography>
                </Box>
                <Store color="primary" sx={{ fontSize: 40, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" variant="body2">
                    활성 계정
                  </Typography>
                  <Typography variant="h4" color="success.main">
                    {accounts.filter((acc: PlatformAccount) => acc.status === 'active').length}
                  </Typography>
                </Box>
                <CheckCircle color="success" sx={{ fontSize: 40, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" variant="body2">
                    동기화 중
                  </Typography>
                  <Typography variant="h4" color="primary.main">
                    {accounts.filter((acc: PlatformAccount) => acc.syncStatus === 'syncing').length}
                  </Typography>
                </Box>
                <CloudSync color="primary" sx={{ fontSize: 40, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" variant="body2">
                    오류 발생
                  </Typography>
                  <Typography variant="h4" color="error.main">
                    {accounts.filter((acc: PlatformAccount) => acc.status === 'error').length}
                  </Typography>
                </Box>
                <Error color="error" sx={{ fontSize: 40, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Platform Accounts, Loading 또는 Empty State */}
      {isLoading ? (
        // 로딩 중 스켈레톤 표시 (사용자 중심 개선)
        <Grid container spacing={3}>
          {Array.from({ length: 6 }).map((_, index) => (
            <Grid item xs={12} md={6} lg={4} key={index}>
              <PlatformCardSkeleton />
            </Grid>
          ))}
        </Grid>
      ) : accounts.length === 0 ? (
        <PlatformsEmptyState onAddPlatform={handleAddAccount} />
      ) : (
        <Grid container spacing={3}>
          {accounts.map((account: PlatformAccount) => {
          const config = platformConfig[account.platform as keyof typeof platformConfig]
          return (
            <Grid item xs={12} md={6} lg={4} key={account.id}>
              <Card sx={{ height: '100%', position: 'relative' }}>
                {account.syncStatus === 'syncing' && (
                  <LinearProgress sx={{ position: 'absolute', top: 0, left: 0, right: 0 }} />
                )}
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Avatar
                        sx={{
                          bgcolor: config.color,
                          width: 48,
                          height: 48,
                        }}
                      >
                        {config.name[0]}
                      </Avatar>
                      <Box>
                        <Typography variant="h6">
                          {account.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {config.name}
                        </Typography>
                      </Box>
                    </Box>
                    <IconButton
                      size="small"
                      onClick={(e) => handleMenuOpen(e, account)}
                    >
                      <MoreVert />
                    </IconButton>
                  </Box>

                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                    {getStatusIcon(account.status)}
                    <Chip
                      label={getStatusLabel(account.status)}
                      size="small"
                      color={
                        account.status === 'active' ? 'success' :
                        account.status === 'error' ? 'error' : 'warning'
                      }
                    />
                    {account.isConnected && (
                      <Chip
                        icon={<LinkIcon />}
                        label="연결됨"
                        size="small"
                        variant="outlined"
                      />
                    )}
                  </Box>

                  {account.statistics && (
                    <Grid container spacing={2} sx={{ mb: 2 }}>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">
                          상품 수
                        </Typography>
                        <Typography variant="body2" fontWeight={500}>
                          {account.statistics.totalProducts}개
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">
                          활성 리스팅
                        </Typography>
                        <Typography variant="body2" fontWeight={500}>
                          {account.statistics.activeListings}개
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">
                          이번 달 주문
                        </Typography>
                        <Typography variant="body2" fontWeight={500}>
                          {account.statistics.totalOrders}건
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">
                          이번 달 매출
                        </Typography>
                        <Typography variant="body2" fontWeight={500}>
                          ₩{(account.statistics.monthlyRevenue / 1000000).toFixed(1)}M
                        </Typography>
                      </Grid>
                    </Grid>
                  )}

                  <Divider sx={{ my: 2 }} />

                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        마지막 동기화
                      </Typography>
                      <Typography variant="body2">
                        {account.lastSync ? formatDate(account.lastSync) : '동기화 전'}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Tooltip title="자동 동기화">
                        <Switch
                          size="small"
                          checked={account.autoSync}
                          onChange={() => handleToggleAutoSync(account)}
                        />
                      </Tooltip>
                      <Tooltip title="지금 동기화">
                        <IconButton
                          size="small"
                          onClick={() => handleSyncAccount(account)}
                          disabled={account.syncStatus === 'syncing' || syncingPlatforms.has(account.id)}
                        >
                          {syncingPlatforms.has(account.id) || account.syncStatus === 'syncing' ? (
                            <Sync />
                          ) : (
                            <Sync />
                          )}
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          )
        })}
        </Grid>
      )}

      {/* Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleEditAccount}>
          <Edit sx={{ mr: 1 }} /> 계정 수정
        </MenuItem>
        <MenuItem onClick={() => handleSyncAccount(selectedAccount!)}>
          <Sync sx={{ mr: 1 }} /> 동기화
        </MenuItem>
        <MenuItem>
          <Settings sx={{ mr: 1 }} /> 설정
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleDeleteAccount} sx={{ color: 'error.main' }}>
          <Delete sx={{ mr: 1 }} /> 삭제
        </MenuItem>
      </Menu>

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editMode ? '계정 수정' : '새 계정 추가'}
        </DialogTitle>
        <DialogContent dividers>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControl fullWidth required disabled={editMode}>
                <InputLabel>플랫폼</InputLabel>
                <Select
                  value={formData.platform}
                  onChange={(e) => setFormData({ ...formData, platform: e.target.value })}
                  label="플랫폼"
                >
                  {Object.entries(platformConfig).map(([key, config]) => (
                    <MenuItem key={key} value={key}>
                      {config.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                required
                label="계정 이름"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="예: 쿠팡 메인 스토어"
              />
            </Grid>
            {!editMode && (
              <>
                <Grid item xs={12}>
                  <Alert severity="info">
                    API 인증 정보는 각 플랫폼의 판매자 센터에서 발급받을 수 있습니다.
                  </Alert>
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="API Key"
                    value={formData.apiKey}
                    onChange={(e) => setFormData({ ...formData, apiKey: e.target.value })}
                    type="password"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Secret Key"
                    value={formData.secretKey}
                    onChange={(e) => setFormData({ ...formData, secretKey: e.target.value })}
                    type="password"
                  />
                </Grid>
              </>
            )}
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="동기화 주기 (분)"
                type="number"
                value={formData.syncInterval}
                onChange={(e) => setFormData({ ...formData, syncInterval: parseInt(e.target.value) })}
                InputProps={{ inputProps: { min: 5 } }}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>취소</Button>
          <Button variant="contained" onClick={handleSaveAccount}>
            {editMode ? '수정' : '추가'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default PlatformAccounts