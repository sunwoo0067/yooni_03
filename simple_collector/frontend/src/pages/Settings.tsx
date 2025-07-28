import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Grid,
  Switch,
  FormControlLabel,
  Divider,
  Alert,
  Tabs,
  Tab,
  CircularProgress,
  Chip,
} from '@mui/material'
import {
  Save as SaveIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  WifiTethering as TestIcon,
} from '@mui/icons-material'
import { api } from '../api/client'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  )
}

export default function Settings() {
  const [tabValue, setTabValue] = useState(0)
  const [alert, setAlert] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [testResults, setTestResults] = useState<Record<string, 'success' | 'failed' | 'error' | null>>({})

  // 공급사 설정 상태
  const [zentradeSettings, setZentradeSettings] = useState({
    api_id: '',
    api_key: '',
    enabled: true,
  })

  const [ownerclanSettings, setOwnerclanSettings] = useState({
    username: '',
    password: '',
    enabled: true,
  })

  const [domeggookSettings, setDomeggookSettings] = useState({
    api_key: '',
    enabled: true,
  })

  // 마켓플레이스 설정
  const [coupangSettings, setCoupangSettings] = useState({
    access_key: '',
    secret_key: '',
    vendor_id: '',
    enabled: true,
  })

  const [naverSettings, setNaverSettings] = useState({
    client_id: '',
    client_secret: '',
    enabled: true,
  })

  const [elevenSettings, setElevenSettings] = useState({
    api_key: '',
    enabled: true,
  })

  // 설정 조회
  const { data: zentradeData } = useQuery({
    queryKey: ['settings', 'zentrade'],
    queryFn: async () => {
      const response = await api.getSupplierSettings('zentrade')
      return response.data
    },
  })

  const { data: ownerclanData } = useQuery({
    queryKey: ['settings', 'ownerclan'],
    queryFn: async () => {
      const response = await api.getSupplierSettings('ownerclan')
      return response.data
    },
  })

  const { data: domeggookData } = useQuery({
    queryKey: ['settings', 'domeggook'],
    queryFn: async () => {
      const response = await api.getSupplierSettings('domeggook')
      return response.data
    },
  })

  // 설정 데이터 로드
  useEffect(() => {
    if (zentradeData?.has_credentials) {
      setZentradeSettings({
        api_id: zentradeData.api_config?.api_id || '',
        api_key: zentradeData.api_config?.api_key || '',
        enabled: zentradeData.is_active,
      })
    }
  }, [zentradeData])

  useEffect(() => {
    if (ownerclanData?.has_credentials) {
      setOwnerclanSettings({
        username: ownerclanData.api_config?.username || '',
        password: ownerclanData.api_config?.password || '',
        enabled: ownerclanData.is_active,
      })
    }
  }, [ownerclanData])

  useEffect(() => {
    if (domeggookData?.has_credentials) {
      setDomeggookSettings({
        api_key: domeggookData.api_config?.api_key || '',
        enabled: domeggookData.is_active,
      })
    }
  }, [domeggookData])

  // 설정 저장 mutations
  const saveZentradeMutation = useMutation({
    mutationFn: () => api.updateZentradeSettings(zentradeSettings),
    onSuccess: () => {
      setAlert({ type: 'success', message: '젠트레이드 설정이 저장되었습니다.' })
    },
    onError: (error: any) => {
      setAlert({ type: 'error', message: `저장 실패: ${error.response?.data?.detail || error.message}` })
    },
  })

  const saveOwnerClanMutation = useMutation({
    mutationFn: () => api.updateOwnerClanSettings(ownerclanSettings),
    onSuccess: () => {
      setAlert({ type: 'success', message: '오너클랜 설정이 저장되었습니다.' })
    },
    onError: (error: any) => {
      setAlert({ type: 'error', message: `저장 실패: ${error.response?.data?.detail || error.message}` })
    },
  })

  const saveDomeggookMutation = useMutation({
    mutationFn: () => api.updateDomeggookSettings(domeggookSettings),
    onSuccess: () => {
      setAlert({ type: 'success', message: '도매꾹 설정이 저장되었습니다.' })
    },
    onError: (error: any) => {
      setAlert({ type: 'error', message: `저장 실패: ${error.response?.data?.detail || error.message}` })
    },
  })

  // 마켓플레이스 설정 저장 mutations
  const saveCoupangMutation = useMutation({
    mutationFn: () => api.updateMarketplaceSettings('coupang', coupangSettings),
    onSuccess: () => {
      setAlert({ type: 'success', message: '쿠팡 설정이 저장되었습니다.' })
    },
    onError: (error: any) => {
      setAlert({ type: 'error', message: `저장 실패: ${error.response?.data?.detail || error.message}` })
    },
  })

  const saveNaverMutation = useMutation({
    mutationFn: () => api.updateMarketplaceSettings('naver', naverSettings),
    onSuccess: () => {
      setAlert({ type: 'success', message: '네이버 설정이 저장되었습니다.' })
    },
    onError: (error: any) => {
      setAlert({ type: 'error', message: `저장 실패: ${error.response?.data?.detail || error.message}` })
    },
  })

  const saveElevenMutation = useMutation({
    mutationFn: () => api.updateMarketplaceSettings('11st', elevenSettings),
    onSuccess: () => {
      setAlert({ type: 'success', message: '11번가 설정이 저장되었습니다.' })
    },
    onError: (error: any) => {
      setAlert({ type: 'error', message: `저장 실패: ${error.response?.data?.detail || error.message}` })
    },
  })

  // 연결 테스트
  const testConnectionMutation = useMutation({
    mutationFn: (supplier: string) => api.testSupplierConnection(supplier),
    onSuccess: (data, supplier) => {
      const result = data.data
      setTestResults({ ...testResults, [supplier]: result.status })
      if (result.status === 'success') {
        setAlert({ type: 'success', message: `${supplier} 연결 테스트 성공!` })
      } else {
        setAlert({ type: 'error', message: `${supplier} 연결 실패: ${result.message}` })
      }
    },
    onError: (error: any, supplier) => {
      setTestResults({ ...testResults, [supplier]: 'error' })
      setAlert({ type: 'error', message: `테스트 실패: ${error.response?.data?.detail || error.message}` })
    },
  })

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
  }

  const getTestStatusIcon = (supplier: string) => {
    const status = testResults[supplier]
    if (!status) return null
    
    switch (status) {
      case 'success':
        return <Chip icon={<CheckIcon />} label="연결 성공" size="small" color="success" />
      case 'failed':
        return <Chip icon={<ErrorIcon />} label="연결 실패" size="small" color="error" />
      case 'error':
        return <Chip icon={<ErrorIcon />} label="오류" size="small" color="error" />
      default:
        return null
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        설정
      </Typography>

      {alert && (
        <Alert severity={alert.type} onClose={() => setAlert(null)} sx={{ mb: 2 }}>
          {alert.message}
        </Alert>
      )}

      <Card>
        <CardContent>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label="젠트레이드" />
            <Tab label="오너클랜" />
            <Tab label="도매꾹" />
            <Tab label="쿠팡" />
            <Tab label="네이버" />
            <Tab label="11번가" />
          </Tabs>

          {/* 젠트레이드 설정 */}
          <TabPanel value={tabValue} index={0}>
            <Box display="flex" alignItems="center" mb={2}>
              <Typography variant="h6">젠트레이드 API 설정</Typography>
              {getTestStatusIcon('zentrade')}
            </Box>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={zentradeSettings.enabled}
                      onChange={(e) =>
                        setZentradeSettings({ ...zentradeSettings, enabled: e.target.checked })
                      }
                    />
                  }
                  label="활성화"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="API ID"
                  value={zentradeSettings.api_id}
                  onChange={(e) =>
                    setZentradeSettings({ ...zentradeSettings, api_id: e.target.value })
                  }
                  disabled={!zentradeSettings.enabled}
                  placeholder="젠트레이드에서 발급받은 API ID"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="API Key"
                  type="password"
                  value={zentradeSettings.api_key}
                  onChange={(e) =>
                    setZentradeSettings({ ...zentradeSettings, api_key: e.target.value })
                  }
                  disabled={!zentradeSettings.enabled}
                  placeholder="젠트레이드에서 발급받은 API Key"
                />
              </Grid>
              <Grid item xs={12}>
                <Box display="flex" gap={2}>
                  <Button
                    variant="contained"
                    startIcon={<SaveIcon />}
                    onClick={() => saveZentradeMutation.mutate()}
                    disabled={!zentradeSettings.enabled || saveZentradeMutation.isPending}
                  >
                    저장
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<TestIcon />}
                    onClick={() => testConnectionMutation.mutate('zentrade')}
                    disabled={!zentradeSettings.enabled || testConnectionMutation.isPending}
                  >
                    연결 테스트
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </TabPanel>

          {/* 오너클랜 설정 */}
          <TabPanel value={tabValue} index={1}>
            <Box display="flex" alignItems="center" mb={2}>
              <Typography variant="h6">오너클랜 API 설정</Typography>
              {getTestStatusIcon('ownerclan')}
            </Box>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={ownerclanSettings.enabled}
                      onChange={(e) =>
                        setOwnerclanSettings({ ...ownerclanSettings, enabled: e.target.checked })
                      }
                    />
                  }
                  label="활성화"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Username"
                  value={ownerclanSettings.username}
                  onChange={(e) =>
                    setOwnerclanSettings({ ...ownerclanSettings, username: e.target.value })
                  }
                  disabled={!ownerclanSettings.enabled}
                  placeholder="오너클랜 계정 아이디"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Password"
                  type="password"
                  value={ownerclanSettings.password}
                  onChange={(e) =>
                    setOwnerclanSettings({ ...ownerclanSettings, password: e.target.value })
                  }
                  disabled={!ownerclanSettings.enabled}
                  placeholder="오너클랜 계정 비밀번호"
                />
              </Grid>
              <Grid item xs={12}>
                <Box display="flex" gap={2}>
                  <Button
                    variant="contained"
                    startIcon={<SaveIcon />}
                    onClick={() => saveOwnerClanMutation.mutate()}
                    disabled={!ownerclanSettings.enabled || saveOwnerClanMutation.isPending}
                  >
                    저장
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<TestIcon />}
                    onClick={() => testConnectionMutation.mutate('ownerclan')}
                    disabled={!ownerclanSettings.enabled || testConnectionMutation.isPending}
                  >
                    연결 테스트
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </TabPanel>

          {/* 도매꾹 설정 */}
          <TabPanel value={tabValue} index={2}>
            <Box display="flex" alignItems="center" mb={2}>
              <Typography variant="h6">도매꾹 API 설정</Typography>
              {getTestStatusIcon('domeggook')}
            </Box>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={domeggookSettings.enabled}
                      onChange={(e) =>
                        setDomeggookSettings({ ...domeggookSettings, enabled: e.target.checked })
                      }
                    />
                  }
                  label="활성화"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="API Key"
                  type="password"
                  value={domeggookSettings.api_key}
                  onChange={(e) =>
                    setDomeggookSettings({ ...domeggookSettings, api_key: e.target.value })
                  }
                  disabled={!domeggookSettings.enabled}
                  placeholder="도매꾹에서 발급받은 API Key"
                />
              </Grid>
              <Grid item xs={12}>
                <Box display="flex" gap={2}>
                  <Button
                    variant="contained"
                    startIcon={<SaveIcon />}
                    onClick={() => saveDomeggookMutation.mutate()}
                    disabled={!domeggookSettings.enabled || saveDomeggookMutation.isPending}
                  >
                    저장
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<TestIcon />}
                    onClick={() => testConnectionMutation.mutate('domeggook')}
                    disabled={!domeggookSettings.enabled || testConnectionMutation.isPending}
                  >
                    연결 테스트
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </TabPanel>

          {/* 쿠팡 설정 */}
          <TabPanel value={tabValue} index={3}>
            <Box display="flex" alignItems="center" mb={2}>
              <Typography variant="h6">쿠팡 오픈 API 설정</Typography>
              {getTestStatusIcon('coupang')}
            </Box>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={coupangSettings.enabled}
                      onChange={(e) =>
                        setCoupangSettings({ ...coupangSettings, enabled: e.target.checked })
                      }
                    />
                  }
                  label="활성화"
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Access Key"
                  value={coupangSettings.access_key}
                  onChange={(e) =>
                    setCoupangSettings({ ...coupangSettings, access_key: e.target.value })
                  }
                  disabled={!coupangSettings.enabled}
                  placeholder="쿠팡 Access Key"
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Secret Key"
                  type="password"
                  value={coupangSettings.secret_key}
                  onChange={(e) =>
                    setCoupangSettings({ ...coupangSettings, secret_key: e.target.value })
                  }
                  disabled={!coupangSettings.enabled}
                  placeholder="쿠팡 Secret Key"
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Vendor ID"
                  value={coupangSettings.vendor_id}
                  onChange={(e) =>
                    setCoupangSettings({ ...coupangSettings, vendor_id: e.target.value })
                  }
                  disabled={!coupangSettings.enabled}
                  placeholder="쿠팡 Vendor ID"
                />
              </Grid>
              <Grid item xs={12}>
                <Box display="flex" gap={2}>
                  <Button
                    variant="contained"
                    startIcon={<SaveIcon />}
                    onClick={() => saveCoupangMutation.mutate()}
                    disabled={!coupangSettings.enabled}
                  >
                    저장
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<TestIcon />}
                    onClick={() => testConnectionMutation.mutate('coupang')}
                    disabled={!coupangSettings.enabled}
                  >
                    연결 테스트
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </TabPanel>

          {/* 네이버 설정 */}
          <TabPanel value={tabValue} index={4}>
            <Box display="flex" alignItems="center" mb={2}>
              <Typography variant="h6">네이버 스마트스토어 API 설정</Typography>
              {getTestStatusIcon('naver')}
            </Box>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={naverSettings.enabled}
                      onChange={(e) =>
                        setNaverSettings({ ...naverSettings, enabled: e.target.checked })
                      }
                    />
                  }
                  label="활성화"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Client ID"
                  value={naverSettings.client_id}
                  onChange={(e) =>
                    setNaverSettings({ ...naverSettings, client_id: e.target.value })
                  }
                  disabled={!naverSettings.enabled}
                  placeholder="네이버 Client ID"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Client Secret"
                  type="password"
                  value={naverSettings.client_secret}
                  onChange={(e) =>
                    setNaverSettings({ ...naverSettings, client_secret: e.target.value })
                  }
                  disabled={!naverSettings.enabled}
                  placeholder="네이버 Client Secret"
                />
              </Grid>
              <Grid item xs={12}>
                <Box display="flex" gap={2}>
                  <Button
                    variant="contained"
                    startIcon={<SaveIcon />}
                    onClick={() => saveNaverMutation.mutate()}
                    disabled={!naverSettings.enabled}
                  >
                    저장
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<TestIcon />}
                    onClick={() => testConnectionMutation.mutate('naver')}
                    disabled={!naverSettings.enabled}
                  >
                    연결 테스트
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </TabPanel>

          {/* 11번가 설정 */}
          <TabPanel value={tabValue} index={5}>
            <Box display="flex" alignItems="center" mb={2}>
              <Typography variant="h6">11번가 오픈 API 설정</Typography>
              {getTestStatusIcon('11st')}
            </Box>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={elevenSettings.enabled}
                      onChange={(e) =>
                        setElevenSettings({ ...elevenSettings, enabled: e.target.checked })
                      }
                    />
                  }
                  label="활성화"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="API Key"
                  type="password"
                  value={elevenSettings.api_key}
                  onChange={(e) =>
                    setElevenSettings({ ...elevenSettings, api_key: e.target.value })
                  }
                  disabled={!elevenSettings.enabled}
                  placeholder="11번가 API Key"
                />
              </Grid>
              <Grid item xs={12}>
                <Box display="flex" gap={2}>
                  <Button
                    variant="contained"
                    startIcon={<SaveIcon />}
                    onClick={() => saveElevenMutation.mutate()}
                    disabled={!elevenSettings.enabled}
                  >
                    저장
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<TestIcon />}
                    onClick={() => testConnectionMutation.mutate('11st')}
                    disabled={!elevenSettings.enabled}
                  >
                    연결 테스트
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </TabPanel>
        </CardContent>
      </Card>

      {/* API 키 발급 안내 */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            API 키 발급 안내
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <Typography variant="subtitle1" fontWeight="bold">젠트레이드</Typography>
              <Typography variant="body2" color="textSecondary">
                1. zentrade.co.kr 로그인<br />
                2. 마이페이지 → API 관리<br />
                3. API ID/Key 발급
              </Typography>
            </Grid>
            <Grid item xs={12} md={4}>
              <Typography variant="subtitle1" fontWeight="bold">오너클랜</Typography>
              <Typography variant="body2" color="textSecondary">
                1. ownerclan.com 셀러 가입<br />
                2. 판매자 승인 후<br />
                3. 계정 정보로 연동
              </Typography>
            </Grid>
            <Grid item xs={12} md={4}>
              <Typography variant="subtitle1" fontWeight="bold">도매꾹</Typography>
              <Typography variant="body2" color="textSecondary">
                1. domeggook.com 로그인<br />
                2. API 서비스 신청<br />
                3. API Key 발급
              </Typography>
            </Grid>
          </Grid>
          <Divider sx={{ my: 2 }} />
          <Typography variant="h6" gutterBottom>
            마켓플레이스 API 키 발급 안내
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <Typography variant="subtitle1" fontWeight="bold">쿠팡</Typography>
              <Typography variant="body2" color="textSecondary">
                1. partners.coupang.com 로그인<br />
                2. Open API → API 키 관리<br />
                3. Access Key/Secret Key 발급<br />
                4. Vendor ID 확인
              </Typography>
            </Grid>
            <Grid item xs={12} md={4}>
              <Typography variant="subtitle1" fontWeight="bold">네이버</Typography>
              <Typography variant="body2" color="textSecondary">
                1. commerce.naver.com/developer<br />
                2. 애플리케이션 등록<br />
                3. Client ID/Secret 발급<br />
                4. 스마트스토어 API 권한 설정
              </Typography>
            </Grid>
            <Grid item xs={12} md={4}>
              <Typography variant="subtitle1" fontWeight="bold">11번가</Typography>
              <Typography variant="body2" color="textSecondary">
                1. openapi.11st.co.kr 가입<br />
                2. 판매자 인증<br />
                3. Open API Key 발급<br />
                4. API 사용 승인 대기
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Box>
  )
}