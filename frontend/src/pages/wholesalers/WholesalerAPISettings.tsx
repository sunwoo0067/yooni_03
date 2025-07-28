import React, { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  CardActions,
  TextField,
  IconButton,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Switch,
  Chip,
  Tooltip,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider,
} from '@mui/material'
import {
  Add,
  Edit,
  Delete,
  Key,
  Security,
  CheckCircle,
  Error,
  Warning,
  Visibility,
  VisibilityOff,
  ContentCopy,
  Refresh,
  Api,
  Link,
} from '@mui/icons-material'
import { toast } from 'react-hot-toast'
import { useNotification } from '@components/ui/NotificationSystem'

interface WholesalerAPI {
  id: string
  wholesaler: string
  name: string
  apiType: 'api_key' | 'oauth' | 'scraping'
  isActive: boolean
  credentials: {
    apiKey?: string
    apiSecret?: string
    accessToken?: string
    refreshToken?: string
    username?: string
    password?: string
    apiEndpoint?: string
  }
  testStatus?: 'success' | 'failed' | 'pending'
  lastTested?: string
  rateLimit?: {
    requests: number
    period: string // '1h', '1d', etc
    remaining?: number
  }
  permissions?: string[]
}

const WholesalerAPISettings: React.FC = () => {
  const notification = useNotification()
  const [apis, setApis] = useState<WholesalerAPI[]>([])
  const [selectedApi, setSelectedApi] = useState<WholesalerAPI | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({})
  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState({
    wholesaler: '',
    name: '',
    apiType: 'api_key' as 'api_key' | 'oauth' | 'scraping',
    apiKey: '',
    apiSecret: '',
    username: '',
    password: '',
    apiEndpoint: '',
  })

  // 도매처 목록
  const wholesalers = [
    { id: 'ownerclan', name: '오너클랜', hasApi: true },
    { id: 'domeme', name: '도매매', hasApi: true },
    { id: 'gentrade', name: '젠트레이드', hasApi: false },
    { id: 'vvic', name: 'VVIC', hasApi: true },
    { id: 'domeggook', name: '도매꾹', hasApi: true },
    { id: 'b2bclub', name: 'B2B클럽', hasApi: false },
  ]

  // 더미 데이터 로드
  useEffect(() => {
    loadAPIs()
  }, [])

  const loadAPIs = () => {
    // 실제로는 API 호출
    const dummyAPIs: WholesalerAPI[] = [
      {
        id: '1',
        wholesaler: 'ownerclan',
        name: '오너클랜 메인 API',
        apiType: 'api_key',
        isActive: true,
        credentials: {
          apiKey: 'oc_live_key_xxxxxxxxxx',
          apiSecret: 'oc_secret_yyyyyyyyyy',
          apiEndpoint: 'https://api.ownerclan.com/v2',
        },
        testStatus: 'success',
        lastTested: new Date().toISOString(),
        rateLimit: {
          requests: 1000,
          period: '1h',
          remaining: 850,
        },
        permissions: ['read_products', 'read_inventory', 'read_orders'],
      },
      {
        id: '2',
        wholesaler: 'domeme',
        name: '도매매 상품 API',
        apiType: 'oauth',
        isActive: true,
        credentials: {
          accessToken: 'dm_access_token_xxxxxxxxxx',
          refreshToken: 'dm_refresh_token_yyyyyyyyyy',
          apiEndpoint: 'https://openapi.domeme.co.kr/v1',
        },
        testStatus: 'success',
        lastTested: new Date().toISOString(),
        rateLimit: {
          requests: 500,
          period: '1h',
          remaining: 420,
        },
      },
    ]
    setApis(dummyAPIs)
  }

  const handleAddAPI = () => {
    setSelectedApi(null)
    setFormData({
      wholesaler: '',
      name: '',
      apiType: 'api_key',
      apiKey: '',
      apiSecret: '',
      username: '',
      password: '',
      apiEndpoint: '',
    })
    setDialogOpen(true)
  }

  const handleEditAPI = (api: WholesalerAPI) => {
    setSelectedApi(api)
    setFormData({
      wholesaler: api.wholesaler,
      name: api.name,
      apiType: api.apiType,
      apiKey: api.credentials.apiKey || '',
      apiSecret: api.credentials.apiSecret || '',
      username: api.credentials.username || '',
      password: api.credentials.password || '',
      apiEndpoint: api.credentials.apiEndpoint || '',
    })
    setDialogOpen(true)
  }

  const handleSaveAPI = async () => {
    if (!formData.wholesaler || !formData.name) {
      notification.error('도매처와 API 이름을 입력해주세요')
      return
    }

    setIsLoading(true)
    try {
      // 실제로는 API 호출
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      if (selectedApi) {
        notification.success('API 정보가 수정되었습니다')
      } else {
        notification.success('API가 추가되었습니다')
      }
      
      loadAPIs()
      setDialogOpen(false)
    } catch (error) {
      notification.error('API 저장에 실패했습니다')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteAPI = async (api: WholesalerAPI) => {
    if (!window.confirm(`"${api.name}" API를 삭제하시겠습니까?`)) {
      return
    }

    try {
      // 실제로는 API 호출
      await new Promise(resolve => setTimeout(resolve, 500))
      notification.success('API가 삭제되었습니다')
      loadAPIs()
    } catch (error) {
      notification.error('API 삭제에 실패했습니다')
    }
  }

  const handleTestAPI = async (api: WholesalerAPI) => {
    notification.info('API 연결을 테스트하는 중...')
    
    try {
      // 실제로는 API 호출
      await new Promise(resolve => setTimeout(resolve, 2000))
      notification.success('API 연결 테스트 성공!')
      
      // 상태 업데이트
      setApis(prev => prev.map(a => 
        a.id === api.id 
          ? { ...a, testStatus: 'success', lastTested: new Date().toISOString() }
          : a
      ))
    } catch (error) {
      notification.error('API 연결 테스트 실패')
      setApis(prev => prev.map(a => 
        a.id === api.id 
          ? { ...a, testStatus: 'failed', lastTested: new Date().toISOString() }
          : a
      ))
    }
  }

  const toggleShowSecret = (apiId: string) => {
    setShowSecrets(prev => ({
      ...prev,
      [apiId]: !prev[apiId],
    }))
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('클립보드에 복사되었습니다')
  }

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'success':
        return 'success'
      case 'failed':
        return 'error'
      default:
        return 'default'
    }
  }

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4">
          도매처 API 설정
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={handleAddAPI}
        >
          API 추가
        </Button>
      </Box>

      <Alert severity="info" sx={{ mb: 3 }}>
        도매처별 API 키를 설정하여 자동으로 상품 정보를 수집하고 재고를 동기화할 수 있습니다.
        API가 없는 도매처는 웹 스크래핑으로 데이터를 수집합니다.
      </Alert>

      <Grid container spacing={3}>
        {apis.map((api) => (
          <Grid item xs={12} md={6} key={api.id}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Api color="primary" />
                    <Typography variant="h6">
                      {api.name}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Chip
                      label={wholesalers.find(w => w.id === api.wholesaler)?.name}
                      size="small"
                      color="primary"
                    />
                    <Chip
                      label={api.apiType}
                      size="small"
                      variant="outlined"
                    />
                    <Chip
                      icon={api.testStatus === 'success' ? <CheckCircle /> : <Error />}
                      label={api.testStatus === 'success' ? '정상' : '오류'}
                      size="small"
                      color={getStatusColor(api.testStatus)}
                    />
                  </Box>
                </Box>

                <List dense>
                  {api.credentials.apiKey && (
                    <ListItem>
                      <ListItemText
                        primary="API Key"
                        secondary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body2" component="span">
                              {showSecrets[api.id] 
                                ? api.credentials.apiKey 
                                : '••••••••••••••••'}
                            </Typography>
                            <IconButton
                              size="small"
                              onClick={() => toggleShowSecret(api.id)}
                            >
                              {showSecrets[api.id] ? <VisibilityOff /> : <Visibility />}
                            </IconButton>
                            <IconButton
                              size="small"
                              onClick={() => copyToClipboard(api.credentials.apiKey!)}
                            >
                              <ContentCopy />
                            </IconButton>
                          </Box>
                        }
                      />
                    </ListItem>
                  )}

                  {api.credentials.apiEndpoint && (
                    <ListItem>
                      <ListItemText
                        primary="Endpoint"
                        secondary={api.credentials.apiEndpoint}
                      />
                    </ListItem>
                  )}

                  {api.rateLimit && (
                    <ListItem>
                      <ListItemText
                        primary="Rate Limit"
                        secondary={`${api.rateLimit.remaining}/${api.rateLimit.requests} requests per ${api.rateLimit.period}`}
                      />
                    </ListItem>
                  )}

                  {api.lastTested && (
                    <ListItem>
                      <ListItemText
                        primary="마지막 테스트"
                        secondary={new Date(api.lastTested).toLocaleString()}
                      />
                    </ListItem>
                  )}
                </List>

                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 2 }}>
                  <Switch
                    checked={api.isActive}
                    onChange={() => {
                      // Toggle active status
                      setApis(prev => prev.map(a => 
                        a.id === api.id ? { ...a, isActive: !a.isActive } : a
                      ))
                    }}
                  />
                  <Typography variant="body2">
                    {api.isActive ? '활성화' : '비활성화'}
                  </Typography>
                </Box>
              </CardContent>

              <CardActions>
                <Button
                  size="small"
                  startIcon={<Refresh />}
                  onClick={() => handleTestAPI(api)}
                >
                  연결 테스트
                </Button>
                <Button
                  size="small"
                  startIcon={<Edit />}
                  onClick={() => handleEditAPI(api)}
                >
                  수정
                </Button>
                <Button
                  size="small"
                  color="error"
                  startIcon={<Delete />}
                  onClick={() => handleDeleteAPI(api)}
                >
                  삭제
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* API 추가/수정 다이얼로그 */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {selectedApi ? 'API 수정' : 'API 추가'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>도매처</InputLabel>
                <Select
                  value={formData.wholesaler}
                  onChange={(e) => setFormData({ ...formData, wholesaler: e.target.value })}
                  label="도매처"
                >
                  {wholesalers.filter(w => w.hasApi).map((w) => (
                    <MenuItem key={w.id} value={w.id}>
                      {w.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="API 이름"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="예: 오너클랜 상품 API"
              />
            </Grid>

            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>인증 방식</InputLabel>
                <Select
                  value={formData.apiType}
                  onChange={(e) => setFormData({ ...formData, apiType: e.target.value as any })}
                  label="인증 방식"
                >
                  <MenuItem value="api_key">API Key</MenuItem>
                  <MenuItem value="oauth">OAuth 2.0</MenuItem>
                  <MenuItem value="scraping">웹 스크래핑</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            {formData.apiType === 'api_key' && (
              <>
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
                    label="API Secret (선택)"
                    value={formData.apiSecret}
                    onChange={(e) => setFormData({ ...formData, apiSecret: e.target.value })}
                    type="password"
                  />
                </Grid>
              </>
            )}

            {formData.apiType === 'scraping' && (
              <>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="사용자명"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="비밀번호"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    type="password"
                  />
                </Grid>
              </>
            )}

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="API Endpoint (선택)"
                value={formData.apiEndpoint}
                onChange={(e) => setFormData({ ...formData, apiEndpoint: e.target.value })}
                placeholder="https://api.example.com/v1"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>
            취소
          </Button>
          <Button
            variant="contained"
            onClick={handleSaveAPI}
            disabled={isLoading}
          >
            {isLoading ? '저장 중...' : '저장'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default WholesalerAPISettings