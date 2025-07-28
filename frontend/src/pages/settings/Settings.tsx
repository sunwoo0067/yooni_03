import React, { useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  Grid,
  TextField,
  Button,
  Switch,
  FormControl,
  FormControlLabel,
  InputLabel,
  Select,
  MenuItem,
  Card,
  CardContent,
  CardHeader,
  CardActions,
  Divider,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Slider,
  Chip,
  Avatar,
  FormGroup,
  Checkbox,
  InputAdornment,
  Radio,
  RadioGroup,
} from '@mui/material'
import {
  Person,
  Business,
  Notifications,
  Security,
  Language,
  Palette,
  Storage,
  Email,
  Phone,
  LocationOn,
  Save,
  Cancel,
  Edit,
  Delete,
  Add,
  CloudUpload,
  Download,
  Sync,
  CheckCircle,
  Warning,
  Info,
  Schedule,
  AttachMoney,
  LocalShipping,
  Inventory,
  DarkMode,
  LightMode,
  Computer,
  VolumeUp,
  VolumeOff,
  ShoppingCart,
} from '@mui/icons-material'
import { toast } from 'react-hot-toast'
import { useAppDispatch, useAppSelector } from '@store/hooks'
import { toggleTheme } from '@store/slices/uiSlice'

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
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  )
}

const Settings: React.FC = () => {
  const dispatch = useAppDispatch()
  const theme = useAppSelector((state) => state.ui.theme)
  const [tabValue, setTabValue] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [saveLoading, setSaveLoading] = useState(false)

  // Form states
  const [profileData, setProfileData] = useState({
    name: 'Admin User',
    email: 'admin@yooni.com',
    phone: '010-1234-5678',
    company: 'Yooni Dropshipping',
  })

  const [businessData, setBusinessData] = useState({
    companyName: 'Yooni Dropshipping',
    businessNumber: '123-45-67890',
    ceoName: '홍길동',
    businessType: '전자상거래업',
    businessCategory: '도소매',
    address: '서울특별시 강남구 테헤란로 123',
    phone: '02-1234-5678',
    fax: '02-1234-5679',
    email: 'business@yooni.com',
  })

  const [notificationSettings, setNotificationSettings] = useState({
    orderNotifications: true,
    lowStockAlerts: true,
    priceChangeAlerts: true,
    systemUpdates: true,
    marketingEmails: false,
    notificationMethod: 'email',
    alertThreshold: 10,
  })

  const [systemSettings, setSystemSettings] = useState({
    language: 'ko',
    timezone: 'Asia/Seoul',
    currency: 'KRW',
    dateFormat: 'YYYY-MM-DD',
    numberFormat: 'comma',
    theme: theme,
    soundEnabled: true,
    autoSave: true,
    autoSaveInterval: 5,
  })

  const [integrationSettings, setIntegrationSettings] = useState({
    googleAnalytics: '',
    naverAnalytics: '',
    kakaoPixel: '',
    facebookPixel: '',
    autoSync: true,
    syncInterval: 30,
  })

  const [shippingSettings, setShippingSettings] = useState({
    defaultCarrier: 'cj',
    returnAddress: '서울특별시 강남구 테헤란로 123',
    freeShippingThreshold: 50000,
    shippingFee: 3000,
    returnPeriod: 7,
    exchangePeriod: 7,
  })

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
  }

  const handleSaveProfile = async () => {
    setSaveLoading(true)
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    setSaveLoading(false)
    toast.success('프로필이 업데이트되었습니다.')
  }

  const handleSaveBusiness = async () => {
    setSaveLoading(true)
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    setSaveLoading(false)
    toast.success('사업자 정보가 업데이트되었습니다.')
  }

  const handleSaveNotifications = async () => {
    setSaveLoading(true)
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    setSaveLoading(false)
    toast.success('알림 설정이 업데이트되었습니다.')
  }

  const handleSaveSystem = async () => {
    setSaveLoading(true)
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    setSaveLoading(false)
    toast.success('시스템 설정이 업데이트되었습니다.')
  }

  const handleThemeChange = (newTheme: 'light' | 'dark' | 'system') => {
    setSystemSettings({ ...systemSettings, theme: newTheme })
    if (newTheme !== 'system') {
      dispatch(toggleTheme())
    }
  }

  const handleExportData = () => {
    toast.success('데이터를 내보냈습니다.')
  }

  const handleImportData = () => {
    setDialogOpen(true)
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          설정
        </Typography>
        <Typography variant="body1" color="text.secondary">
          애플리케이션 설정을 관리하고 환경을 구성하세요
        </Typography>
      </Box>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab icon={<Person />} label="프로필" />
          <Tab icon={<Business />} label="사업자 정보" />
          <Tab icon={<Notifications />} label="알림 설정" />
          <Tab icon={<Computer />} label="시스템 설정" />
          <Tab icon={<Sync />} label="연동 설정" />
          <Tab icon={<LocalShipping />} label="배송 설정" />
          <Tab icon={<Storage />} label="데이터 관리" />
        </Tabs>
      </Paper>

      {/* Tab Panels */}
      <TabPanel value={tabValue} index={0}>
        {/* Profile Settings */}
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Card>
              <CardHeader title="프로필 정보" />
              <CardContent>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="이름"
                      value={profileData.name}
                      onChange={(e) => setProfileData({ ...profileData, name: e.target.value })}
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="이메일"
                      type="email"
                      value={profileData.email}
                      onChange={(e) => setProfileData({ ...profileData, email: e.target.value })}
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="연락처"
                      value={profileData.phone}
                      onChange={(e) => setProfileData({ ...profileData, phone: e.target.value })}
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="회사명"
                      value={profileData.company}
                      onChange={(e) => setProfileData({ ...profileData, company: e.target.value })}
                    />
                  </Grid>
                </Grid>
              </CardContent>
              <CardActions>
                <Button
                  variant="contained"
                  startIcon={<Save />}
                  onClick={handleSaveProfile}
                  disabled={saveLoading}
                >
                  저장
                </Button>
                <Button startIcon={<Cancel />}>취소</Button>
              </CardActions>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardHeader title="프로필 사진" />
              <CardContent sx={{ textAlign: 'center' }}>
                <Avatar sx={{ width: 120, height: 120, mx: 'auto', mb: 2 }}>
                  {profileData.name[0]}
                </Avatar>
                <Button variant="outlined" startIcon={<CloudUpload />}>
                  사진 업로드
                </Button>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        {/* Business Information */}
        <Card>
          <CardHeader title="사업자 정보" />
          <CardContent>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="회사명"
                  value={businessData.companyName}
                  onChange={(e) => setBusinessData({ ...businessData, companyName: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="사업자등록번호"
                  value={businessData.businessNumber}
                  onChange={(e) => setBusinessData({ ...businessData, businessNumber: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="대표자명"
                  value={businessData.ceoName}
                  onChange={(e) => setBusinessData({ ...businessData, ceoName: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="업태"
                  value={businessData.businessType}
                  onChange={(e) => setBusinessData({ ...businessData, businessType: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="종목"
                  value={businessData.businessCategory}
                  onChange={(e) => setBusinessData({ ...businessData, businessCategory: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="사업장 주소"
                  value={businessData.address}
                  onChange={(e) => setBusinessData({ ...businessData, address: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="대표전화"
                  value={businessData.phone}
                  onChange={(e) => setBusinessData({ ...businessData, phone: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="팩스"
                  value={businessData.fax}
                  onChange={(e) => setBusinessData({ ...businessData, fax: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="대표 이메일"
                  type="email"
                  value={businessData.email}
                  onChange={(e) => setBusinessData({ ...businessData, email: e.target.value })}
                />
              </Grid>
            </Grid>
          </CardContent>
          <CardActions>
            <Button
              variant="contained"
              startIcon={<Save />}
              onClick={handleSaveBusiness}
              disabled={saveLoading}
            >
              저장
            </Button>
            <Button startIcon={<Cancel />}>취소</Button>
          </CardActions>
        </Card>
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        {/* Notification Settings */}
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader title="알림 유형" />
              <CardContent>
                <List>
                  <ListItem>
                    <ListItemIcon>
                      <ShoppingCart />
                    </ListItemIcon>
                    <ListItemText
                      primary="주문 알림"
                      secondary="새 주문이 들어올 때 알림을 받습니다"
                    />
                    <ListItemSecondaryAction>
                      <Switch
                        checked={notificationSettings.orderNotifications}
                        onChange={(e) => setNotificationSettings({
                          ...notificationSettings,
                          orderNotifications: e.target.checked
                        })}
                      />
                    </ListItemSecondaryAction>
                  </ListItem>
                  <ListItem>
                    <ListItemIcon>
                      <Inventory />
                    </ListItemIcon>
                    <ListItemText
                      primary="재고 부족 알림"
                      secondary="재고가 설정값 이하로 떨어질 때 알림을 받습니다"
                    />
                    <ListItemSecondaryAction>
                      <Switch
                        checked={notificationSettings.lowStockAlerts}
                        onChange={(e) => setNotificationSettings({
                          ...notificationSettings,
                          lowStockAlerts: e.target.checked
                        })}
                      />
                    </ListItemSecondaryAction>
                  </ListItem>
                  <ListItem>
                    <ListItemIcon>
                      <AttachMoney />
                    </ListItemIcon>
                    <ListItemText
                      primary="가격 변동 알림"
                      secondary="경쟁사 가격 변동 시 알림을 받습니다"
                    />
                    <ListItemSecondaryAction>
                      <Switch
                        checked={notificationSettings.priceChangeAlerts}
                        onChange={(e) => setNotificationSettings({
                          ...notificationSettings,
                          priceChangeAlerts: e.target.checked
                        })}
                      />
                    </ListItemSecondaryAction>
                  </ListItem>
                  <ListItem>
                    <ListItemIcon>
                      <Info />
                    </ListItemIcon>
                    <ListItemText
                      primary="시스템 업데이트"
                      secondary="중요한 시스템 업데이트 알림을 받습니다"
                    />
                    <ListItemSecondaryAction>
                      <Switch
                        checked={notificationSettings.systemUpdates}
                        onChange={(e) => setNotificationSettings({
                          ...notificationSettings,
                          systemUpdates: e.target.checked
                        })}
                      />
                    </ListItemSecondaryAction>
                  </ListItem>
                  <ListItem>
                    <ListItemIcon>
                      <Email />
                    </ListItemIcon>
                    <ListItemText
                      primary="마케팅 이메일"
                      secondary="프로모션 및 마케팅 정보를 받습니다"
                    />
                    <ListItemSecondaryAction>
                      <Switch
                        checked={notificationSettings.marketingEmails}
                        onChange={(e) => setNotificationSettings({
                          ...notificationSettings,
                          marketingEmails: e.target.checked
                        })}
                      />
                    </ListItemSecondaryAction>
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader title="알림 설정" />
              <CardContent>
                <Grid container spacing={3}>
                  <Grid item xs={12}>
                    <FormControl fullWidth>
                      <Typography variant="subtitle2" gutterBottom>
                        알림 방법
                      </Typography>
                      <RadioGroup
                        value={notificationSettings.notificationMethod}
                        onChange={(e) => setNotificationSettings({
                          ...notificationSettings,
                          notificationMethod: e.target.value
                        })}
                      >
                        <FormControlLabel value="email" control={<Radio />} label="이메일" />
                        <FormControlLabel value="sms" control={<Radio />} label="SMS" />
                        <FormControlLabel value="push" control={<Radio />} label="푸시 알림" />
                        <FormControlLabel value="all" control={<Radio />} label="모든 방법" />
                      </RadioGroup>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="subtitle2" gutterBottom>
                      재고 부족 알림 기준
                    </Typography>
                    <Slider
                      value={notificationSettings.alertThreshold}
                      onChange={(e, value) => setNotificationSettings({
                        ...notificationSettings,
                        alertThreshold: value as number
                      })}
                      valueLabelDisplay="on"
                      step={5}
                      marks
                      min={0}
                      max={50}
                    />
                    <Typography variant="caption" color="text.secondary">
                      재고가 {notificationSettings.alertThreshold}개 이하일 때 알림
                    </Typography>
                  </Grid>
                </Grid>
              </CardContent>
              <CardActions>
                <Button
                  variant="contained"
                  startIcon={<Save />}
                  onClick={handleSaveNotifications}
                  disabled={saveLoading}
                >
                  저장
                </Button>
              </CardActions>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      <TabPanel value={tabValue} index={3}>
        {/* System Settings */}
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader title="언어 및 지역" />
              <CardContent>
                <Grid container spacing={3}>
                  <Grid item xs={12}>
                    <FormControl fullWidth>
                      <InputLabel>언어</InputLabel>
                      <Select
                        value={systemSettings.language}
                        onChange={(e) => setSystemSettings({ ...systemSettings, language: e.target.value })}
                        label="언어"
                      >
                        <MenuItem value="ko">한국어</MenuItem>
                        <MenuItem value="en">English</MenuItem>
                        <MenuItem value="ja">日本語</MenuItem>
                        <MenuItem value="zh">中文</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12}>
                    <FormControl fullWidth>
                      <InputLabel>시간대</InputLabel>
                      <Select
                        value={systemSettings.timezone}
                        onChange={(e) => setSystemSettings({ ...systemSettings, timezone: e.target.value })}
                        label="시간대"
                      >
                        <MenuItem value="Asia/Seoul">서울 (GMT+9)</MenuItem>
                        <MenuItem value="Asia/Tokyo">도쿄 (GMT+9)</MenuItem>
                        <MenuItem value="America/New_York">뉴욕 (GMT-5)</MenuItem>
                        <MenuItem value="Europe/London">런던 (GMT+0)</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12}>
                    <FormControl fullWidth>
                      <InputLabel>통화</InputLabel>
                      <Select
                        value={systemSettings.currency}
                        onChange={(e) => setSystemSettings({ ...systemSettings, currency: e.target.value })}
                        label="통화"
                      >
                        <MenuItem value="KRW">한국 원 (₩)</MenuItem>
                        <MenuItem value="USD">미국 달러 ($)</MenuItem>
                        <MenuItem value="JPY">일본 엔 (¥)</MenuItem>
                        <MenuItem value="EUR">유로 (€)</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader title="화면 및 소리" />
              <CardContent>
                <Grid container spacing={3}>
                  <Grid item xs={12}>
                    <Typography variant="subtitle2" gutterBottom>
                      테마 설정
                    </Typography>
                    <RadioGroup
                      row
                      value={systemSettings.theme}
                      onChange={(e) => handleThemeChange(e.target.value as 'light' | 'dark' | 'system')}
                    >
                      <FormControlLabel
                        value="light"
                        control={<Radio />}
                        label={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <LightMode fontSize="small" />
                            라이트
                          </Box>
                        }
                      />
                      <FormControlLabel
                        value="dark"
                        control={<Radio />}
                        label={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <DarkMode fontSize="small" />
                            다크
                          </Box>
                        }
                      />
                      <FormControlLabel
                        value="system"
                        control={<Radio />}
                        label={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <Computer fontSize="small" />
                            시스템
                          </Box>
                        }
                      />
                    </RadioGroup>
                  </Grid>
                  <Grid item xs={12}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={systemSettings.soundEnabled}
                          onChange={(e) => setSystemSettings({
                            ...systemSettings,
                            soundEnabled: e.target.checked
                          })}
                        />
                      }
                      label={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {systemSettings.soundEnabled ? <VolumeUp /> : <VolumeOff />}
                          알림 소리
                        </Box>
                      }
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={systemSettings.autoSave}
                          onChange={(e) => setSystemSettings({
                            ...systemSettings,
                            autoSave: e.target.checked
                          })}
                        />
                      }
                      label="자동 저장"
                    />
                    {systemSettings.autoSave && (
                      <Box sx={{ mt: 2 }}>
                        <Typography variant="caption" color="text.secondary">
                          자동 저장 간격: {systemSettings.autoSaveInterval}분
                        </Typography>
                        <Slider
                          value={systemSettings.autoSaveInterval}
                          onChange={(e, value) => setSystemSettings({
                            ...systemSettings,
                            autoSaveInterval: value as number
                          })}
                          min={1}
                          max={30}
                          marks
                          step={1}
                          valueLabelDisplay="auto"
                        />
                      </Box>
                    )}
                  </Grid>
                </Grid>
              </CardContent>
              <CardActions>
                <Button
                  variant="contained"
                  startIcon={<Save />}
                  onClick={handleSaveSystem}
                  disabled={saveLoading}
                >
                  저장
                </Button>
              </CardActions>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      <TabPanel value={tabValue} index={4}>
        {/* Integration Settings */}
        <Card>
          <CardHeader title="외부 서비스 연동" />
          <CardContent>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Google Analytics ID"
                  placeholder="UA-XXXXXXXXX-X"
                  value={integrationSettings.googleAnalytics}
                  onChange={(e) => setIntegrationSettings({
                    ...integrationSettings,
                    googleAnalytics: e.target.value
                  })}
                  helperText="Google Analytics 추적 ID를 입력하세요"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="네이버 애널리틱스 ID"
                  placeholder="na-XXXXXXXXXXXX"
                  value={integrationSettings.naverAnalytics}
                  onChange={(e) => setIntegrationSettings({
                    ...integrationSettings,
                    naverAnalytics: e.target.value
                  })}
                  helperText="네이버 애널리틱스 사이트 ID를 입력하세요"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="카카오 픽셀 ID"
                  placeholder="XXXXXXXXXXXXX"
                  value={integrationSettings.kakaoPixel}
                  onChange={(e) => setIntegrationSettings({
                    ...integrationSettings,
                    kakaoPixel: e.target.value
                  })}
                  helperText="카카오 픽셀 추적 ID를 입력하세요"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Facebook Pixel ID"
                  placeholder="XXXXXXXXXXXXXXXX"
                  value={integrationSettings.facebookPixel}
                  onChange={(e) => setIntegrationSettings({
                    ...integrationSettings,
                    facebookPixel: e.target.value
                  })}
                  helperText="Facebook 픽셀 ID를 입력하세요"
                />
              </Grid>
              <Grid item xs={12}>
                <Divider sx={{ my: 2 }} />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={integrationSettings.autoSync}
                      onChange={(e) => setIntegrationSettings({
                        ...integrationSettings,
                        autoSync: e.target.checked
                      })}
                    />
                  }
                  label="자동 동기화"
                />
                {integrationSettings.autoSync && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="caption" color="text.secondary">
                      동기화 간격: {integrationSettings.syncInterval}분
                    </Typography>
                    <Slider
                      value={integrationSettings.syncInterval}
                      onChange={(e, value) => setIntegrationSettings({
                        ...integrationSettings,
                        syncInterval: value as number
                      })}
                      min={5}
                      max={120}
                      marks
                      step={5}
                      valueLabelDisplay="auto"
                    />
                  </Box>
                )}
              </Grid>
            </Grid>
          </CardContent>
          <CardActions>
            <Button variant="contained" startIcon={<Save />}>
              저장
            </Button>
          </CardActions>
        </Card>
      </TabPanel>

      <TabPanel value={tabValue} index={5}>
        {/* Shipping Settings */}
        <Card>
          <CardHeader title="배송 설정" />
          <CardContent>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>기본 택배사</InputLabel>
                  <Select
                    value={shippingSettings.defaultCarrier}
                    onChange={(e) => setShippingSettings({
                      ...shippingSettings,
                      defaultCarrier: e.target.value
                    })}
                    label="기본 택배사"
                  >
                    <MenuItem value="cj">CJ대한통운</MenuItem>
                    <MenuItem value="hanjin">한진택배</MenuItem>
                    <MenuItem value="lotte">롯데택배</MenuItem>
                    <MenuItem value="post">우체국택배</MenuItem>
                    <MenuItem value="logen">로젠택배</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="반품지 주소"
                  value={shippingSettings.returnAddress}
                  onChange={(e) => setShippingSettings({
                    ...shippingSettings,
                    returnAddress: e.target.value
                  })}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="무료배송 기준금액"
                  type="number"
                  value={shippingSettings.freeShippingThreshold}
                  onChange={(e) => setShippingSettings({
                    ...shippingSettings,
                    freeShippingThreshold: parseInt(e.target.value)
                  })}
                  InputProps={{
                    startAdornment: <InputAdornment position="start">₩</InputAdornment>,
                  }}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="기본 배송비"
                  type="number"
                  value={shippingSettings.shippingFee}
                  onChange={(e) => setShippingSettings({
                    ...shippingSettings,
                    shippingFee: parseInt(e.target.value)
                  })}
                  InputProps={{
                    startAdornment: <InputAdornment position="start">₩</InputAdornment>,
                  }}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="반품 가능 기간"
                  type="number"
                  value={shippingSettings.returnPeriod}
                  onChange={(e) => setShippingSettings({
                    ...shippingSettings,
                    returnPeriod: parseInt(e.target.value)
                  })}
                  InputProps={{
                    endAdornment: <InputAdornment position="end">일</InputAdornment>,
                  }}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="교환 가능 기간"
                  type="number"
                  value={shippingSettings.exchangePeriod}
                  onChange={(e) => setShippingSettings({
                    ...shippingSettings,
                    exchangePeriod: parseInt(e.target.value)
                  })}
                  InputProps={{
                    endAdornment: <InputAdornment position="end">일</InputAdornment>,
                  }}
                />
              </Grid>
            </Grid>
          </CardContent>
          <CardActions>
            <Button variant="contained" startIcon={<Save />}>
              저장
            </Button>
          </CardActions>
        </Card>
      </TabPanel>

      <TabPanel value={tabValue} index={6}>
        {/* Data Management */}
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader title="데이터 내보내기" />
              <CardContent>
                <Typography variant="body2" color="text.secondary" paragraph>
                  모든 데이터를 백업 파일로 내보낼 수 있습니다.
                </Typography>
                <FormGroup>
                  <FormControlLabel control={<Checkbox defaultChecked />} label="상품 데이터" />
                  <FormControlLabel control={<Checkbox defaultChecked />} label="주문 데이터" />
                  <FormControlLabel control={<Checkbox defaultChecked />} label="고객 데이터" />
                  <FormControlLabel control={<Checkbox defaultChecked />} label="설정 데이터" />
                </FormGroup>
              </CardContent>
              <CardActions>
                <Button
                  variant="contained"
                  startIcon={<Download />}
                  onClick={handleExportData}
                >
                  데이터 내보내기
                </Button>
              </CardActions>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader title="데이터 가져오기" />
              <CardContent>
                <Typography variant="body2" color="text.secondary" paragraph>
                  백업 파일에서 데이터를 복원할 수 있습니다.
                </Typography>
                <Alert severity="warning" sx={{ mb: 2 }}>
                  데이터 가져오기는 기존 데이터를 덮어쓸 수 있습니다.
                </Alert>
              </CardContent>
              <CardActions>
                <Button
                  variant="outlined"
                  startIcon={<CloudUpload />}
                  onClick={handleImportData}
                >
                  데이터 가져오기
                </Button>
              </CardActions>
            </Card>
          </Grid>
          <Grid item xs={12}>
            <Card>
              <CardHeader title="데이터 사용량" />
              <CardContent>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={3}>
                    <Typography variant="subtitle2" color="text.secondary">
                      총 상품 수
                    </Typography>
                    <Typography variant="h4">1,234</Typography>
                  </Grid>
                  <Grid item xs={12} md={3}>
                    <Typography variant="subtitle2" color="text.secondary">
                      총 주문 수
                    </Typography>
                    <Typography variant="h4">5,678</Typography>
                  </Grid>
                  <Grid item xs={12} md={3}>
                    <Typography variant="subtitle2" color="text.secondary">
                      총 고객 수
                    </Typography>
                    <Typography variant="h4">890</Typography>
                  </Grid>
                  <Grid item xs={12} md={3}>
                    <Typography variant="subtitle2" color="text.secondary">
                      저장 공간
                    </Typography>
                    <Typography variant="h4">2.3 GB</Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* Import Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>데이터 가져오기</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            현재 데이터가 모두 삭제되고 백업 파일의 데이터로 대체됩니다.
          </Alert>
          <Box sx={{ textAlign: 'center', py: 3 }}>
            <CloudUpload sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              백업 파일 선택
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              .json 또는 .zip 형식의 백업 파일을 업로드하세요.
            </Typography>
            <Button variant="contained" component="label">
              파일 선택
              <input type="file" hidden accept=".json,.zip" />
            </Button>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>취소</Button>
          <Button variant="contained" color="error">
            가져오기
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default Settings