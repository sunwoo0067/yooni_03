import React, { useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  CardHeader,
  CardActions,
  Tabs,
  Tab,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Switch,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Alert,
  LinearProgress,
  Divider,
  Avatar,
  AvatarGroup,
  ToggleButton,
  ToggleButtonGroup,
  Badge,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  FormControlLabel,
  Checkbox,
  Radio,
  RadioGroup,
  InputAdornment,
  Stack,
} from '@mui/material'
import {
  Campaign,
  Email,
  Sms,
  NotificationsActive,
  Schedule,
  People,
  TrendingUp,
  AttachMoney,
  LocalOffer,
  CardGiftcard,
  Timer,
  PlayArrow,
  Pause,
  Stop,
  Edit,
  Delete,
  ContentCopy,
  Add,
  FilterList,
  Send,
  CheckCircle,
  Warning,
  Error as ErrorIcon,
  Info,
  Refresh,
  Download,
  Upload,
  Settings,
  Analytics,
  AutoAwesome,
  Psychology,
  Rule,
  EventRepeat,
  Celebration,
  ShoppingCart,
  PersonAdd,
  Star,
  ThumbUp,
  Visibility,
  BarChart,
  Timeline,
} from '@mui/icons-material'
import { formatCurrency, formatDate, formatNumber, formatPercentage } from '@utils/format'
import { toast } from 'react-hot-toast'
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker'
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider'
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns'
import { ko } from 'date-fns/locale'

// Types
interface Campaign {
  id: string
  name: string
  type: 'email' | 'sms' | 'push' | 'coupon' | 'event'
  status: 'draft' | 'scheduled' | 'active' | 'paused' | 'completed'
  targetAudience: string
  audienceCount: number
  startDate: string
  endDate?: string
  budget?: number
  spent?: number
  sent: number
  opened: number
  clicked: number
  converted: number
  revenue: number
}

interface Automation {
  id: string
  name: string
  trigger: string
  status: 'active' | 'inactive'
  actions: string[]
  targetCount: number
  executionCount: number
  lastRun: string
}

interface Template {
  id: string
  name: string
  type: 'email' | 'sms' | 'push'
  category: string
  thumbnail?: string
  usageCount: number
}

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
      id={`marketing-tabpanel-${index}`}
      aria-labelledby={`marketing-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  )
}

const Marketing: React.FC = () => {
  const [tabValue, setTabValue] = useState(0)
  const [campaignDialogOpen, setCampaignDialogOpen] = useState(false)
  const [automationDialogOpen, setAutomationDialogOpen] = useState(false)
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false)
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null)
  const [selectedAutomation, setSelectedAutomation] = useState<Automation | null>(null)
  const [activeStep, setActiveStep] = useState(0)
  const [campaignType, setCampaignType] = useState<Campaign['type']>('email')
  const [selectedTemplate, setSelectedTemplate] = useState('')
  const [selectedAudience, setSelectedAudience] = useState('all')
  const [scheduledDate, setScheduledDate] = useState<Date | null>(null)
  const [automationTrigger, setAutomationTrigger] = useState('')

  // Mock data
  const campaigns: Campaign[] = [
    {
      id: '1',
      name: '신년 특별 할인 이벤트',
      type: 'email',
      status: 'active',
      targetAudience: '전체 고객',
      audienceCount: 1200,
      startDate: '2024-01-01',
      endDate: '2024-01-15',
      budget: 500000,
      spent: 320000,
      sent: 1200,
      opened: 456,
      clicked: 123,
      converted: 45,
      revenue: 2500000,
    },
    {
      id: '2',
      name: 'VIP 고객 감사 쿠폰',
      type: 'coupon',
      status: 'scheduled',
      targetAudience: 'VIP 고객',
      audienceCount: 45,
      startDate: '2024-01-20',
      sent: 0,
      opened: 0,
      clicked: 0,
      converted: 0,
      revenue: 0,
    },
    {
      id: '3',
      name: '휴면 고객 복귀 캠페인',
      type: 'sms',
      status: 'completed',
      targetAudience: '휴면 고객',
      audienceCount: 89,
      startDate: '2023-12-15',
      endDate: '2023-12-31',
      sent: 89,
      opened: 45,
      clicked: 12,
      converted: 8,
      revenue: 380000,
    },
  ]

  const automations: Automation[] = [
    {
      id: '1',
      name: '신규 가입 환영 시리즈',
      trigger: '회원 가입',
      status: 'active',
      actions: ['환영 이메일', '3일 후 쿠폰 발송', '7일 후 상품 추천'],
      targetCount: 250,
      executionCount: 1823,
      lastRun: '2024-01-10T15:30:00',
    },
    {
      id: '2',
      name: '장바구니 이탈 복구',
      trigger: '장바구니 이탈 24시간',
      status: 'active',
      actions: ['리마인더 이메일', '10% 할인 쿠폰'],
      targetCount: 45,
      executionCount: 567,
      lastRun: '2024-01-10T12:00:00',
    },
    {
      id: '3',
      name: '재구매 유도',
      trigger: '구매 후 30일',
      status: 'inactive',
      actions: ['상품 추천 이메일', '리뷰 작성 요청'],
      targetCount: 0,
      executionCount: 234,
      lastRun: '2023-12-20T10:00:00',
    },
  ]

  const templates: Template[] = [
    { id: '1', name: '기본 뉴스레터', type: 'email', category: '뉴스레터', usageCount: 45 },
    { id: '2', name: '할인 이벤트', type: 'email', category: '프로모션', usageCount: 32 },
    { id: '3', name: '신제품 소개', type: 'email', category: '상품', usageCount: 28 },
    { id: '4', name: '주문 확인', type: 'sms', category: '거래', usageCount: 156 },
    { id: '5', name: '배송 알림', type: 'sms', category: '거래', usageCount: 143 },
    { id: '6', name: '앱 업데이트', type: 'push', category: '시스템', usageCount: 12 },
  ]

  const audienceOptions = [
    { value: 'all', label: '전체 고객', count: 1250 },
    { value: 'vip', label: 'VIP 고객', count: 45 },
    { value: 'active', label: '활성 고객', count: 892 },
    { value: 'inactive', label: '휴면 고객', count: 89 },
    { value: 'new', label: '신규 고객', count: 128 },
    { value: 'custom', label: '맞춤 설정', count: 0 },
  ]

  const triggerOptions = [
    { value: 'signup', label: '회원 가입', icon: <PersonAdd /> },
    { value: 'purchase', label: '구매 완료', icon: <ShoppingCart /> },
    { value: 'cart_abandon', label: '장바구니 이탈', icon: <ShoppingCart /> },
    { value: 'birthday', label: '생일', icon: <Celebration /> },
    { value: 'inactive', label: '휴면 전환', icon: <Timer /> },
    { value: 'custom', label: '맞춤 조건', icon: <Rule /> },
  ]

  const getStatusColor = (status: Campaign['status']) => {
    switch (status) {
      case 'draft': return 'default'
      case 'scheduled': return 'info'
      case 'active': return 'success'
      case 'paused': return 'warning'
      case 'completed': return 'default'
    }
  }

  const getStatusLabel = (status: Campaign['status']) => {
    switch (status) {
      case 'draft': return '초안'
      case 'scheduled': return '예약됨'
      case 'active': return '진행중'
      case 'paused': return '일시정지'
      case 'completed': return '완료'
    }
  }

  const getCampaignIcon = (type: Campaign['type']) => {
    switch (type) {
      case 'email': return <Email />
      case 'sms': return <Sms />
      case 'push': return <NotificationsActive />
      case 'coupon': return <LocalOffer />
      case 'event': return <Celebration />
    }
  }

  const handleCreateCampaign = () => {
    if (activeStep === 2) {
      toast.success('캠페인이 생성되었습니다.')
      setCampaignDialogOpen(false)
      setActiveStep(0)
    } else {
      setActiveStep(prev => prev + 1)
    }
  }

  const handleCreateAutomation = () => {
    toast.success('자동화가 생성되었습니다.')
    setAutomationDialogOpen(false)
  }

  const handlePauseCampaign = (campaign: Campaign) => {
    toast.success(`${campaign.name} 캠페인이 일시정지되었습니다.`)
  }

  const handleDuplicateCampaign = (campaign: Campaign) => {
    toast.success(`${campaign.name} 캠페인이 복제되었습니다.`)
  }

  const handleToggleAutomation = (automation: Automation) => {
    const newStatus = automation.status === 'active' ? '비활성화' : '활성화'
    toast.success(`${automation.name}이(가) ${newStatus}되었습니다.`)
  }

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={ko}>
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h4" gutterBottom>
              마케팅 자동화
            </Typography>
            <Typography variant="body1" color="text.secondary">
              캠페인을 관리하고 마케팅을 자동화하세요
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="outlined"
              startIcon={<Analytics />}
              onClick={() => setTabValue(3)}
            >
              분석 보기
            </Button>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setCampaignDialogOpen(true)}
            >
              새 캠페인
            </Button>
          </Box>
        </Box>

        {/* Statistics */}
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography color="text.secondary" variant="body2">
                      활성 캠페인
                    </Typography>
                    <Typography variant="h4" sx={{ mt: 1 }}>
                      3
                    </Typography>
                  </Box>
                  <Avatar sx={{ bgcolor: 'primary.light' }}>
                    <Campaign />
                  </Avatar>
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
                      이번 달 전송
                    </Typography>
                    <Typography variant="h4" sx={{ mt: 1 }}>
                      2,456
                    </Typography>
                  </Box>
                  <Avatar sx={{ bgcolor: 'success.light' }}>
                    <Send />
                  </Avatar>
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
                      평균 오픈율
                    </Typography>
                    <Typography variant="h4" sx={{ mt: 1 }}>
                      38%
                    </Typography>
                  </Box>
                  <Avatar sx={{ bgcolor: 'warning.light' }}>
                    <Visibility />
                  </Avatar>
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
                      캠페인 수익
                    </Typography>
                    <Typography variant="h5" sx={{ mt: 1 }}>
                      {formatCurrency(3260000)}
                    </Typography>
                  </Box>
                  <Avatar sx={{ bgcolor: 'info.light' }}>
                    <AttachMoney />
                  </Avatar>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Tabs */}
        <Paper sx={{ mb: 3 }}>
          <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
            <Tab label="캠페인" />
            <Tab label="자동화" />
            <Tab label="템플릿" />
            <Tab label="분석" />
          </Tabs>
        </Paper>

        {/* Tab Content */}
        <TabPanel value={tabValue} index={0}>
          {/* Campaigns */}
          <Grid container spacing={3}>
            {campaigns.map((campaign) => (
              <Grid item xs={12} md={6} lg={4} key={campaign.id}>
                <Card>
                  <CardHeader
                    avatar={getCampaignIcon(campaign.type)}
                    title={campaign.name}
                    subheader={`${campaign.targetAudience} • ${campaign.audienceCount}명`}
                    action={
                      <Chip
                        label={getStatusLabel(campaign.status)}
                        color={getStatusColor(campaign.status)}
                        size="small"
                      />
                    }
                  />
                  <CardContent>
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" color="text.secondary">
                        기간: {formatDate(campaign.startDate)}
                        {campaign.endDate && ` ~ ${formatDate(campaign.endDate)}`}
                      </Typography>
                    </Box>
                    
                    {campaign.status !== 'draft' && campaign.status !== 'scheduled' && (
                      <>
                        <Grid container spacing={2} sx={{ mb: 2 }}>
                          <Grid item xs={6}>
                            <Typography variant="body2" color="text.secondary">
                              전송
                            </Typography>
                            <Typography variant="h6">
                              {formatNumber(campaign.sent)}
                            </Typography>
                          </Grid>
                          <Grid item xs={6}>
                            <Typography variant="body2" color="text.secondary">
                              오픈율
                            </Typography>
                            <Typography variant="h6">
                              {formatPercentage(campaign.opened / campaign.sent)}
                            </Typography>
                          </Grid>
                          <Grid item xs={6}>
                            <Typography variant="body2" color="text.secondary">
                              클릭률
                            </Typography>
                            <Typography variant="h6">
                              {formatPercentage(campaign.clicked / campaign.sent)}
                            </Typography>
                          </Grid>
                          <Grid item xs={6}>
                            <Typography variant="body2" color="text.secondary">
                              전환율
                            </Typography>
                            <Typography variant="h6">
                              {formatPercentage(campaign.converted / campaign.sent)}
                            </Typography>
                          </Grid>
                        </Grid>
                        
                        {campaign.budget && (
                          <Box sx={{ mb: 2 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                              <Typography variant="body2" color="text.secondary">
                                예산 사용
                              </Typography>
                              <Typography variant="body2">
                                {formatCurrency(campaign.spent || 0)} / {formatCurrency(campaign.budget)}
                              </Typography>
                            </Box>
                            <LinearProgress
                              variant="determinate"
                              value={((campaign.spent || 0) / campaign.budget) * 100}
                              sx={{ height: 6, borderRadius: 3 }}
                            />
                          </Box>
                        )}
                        
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <Typography variant="body2" color="text.secondary">
                            수익
                          </Typography>
                          <Typography variant="h6" color="success.main">
                            {formatCurrency(campaign.revenue)}
                          </Typography>
                        </Box>
                      </>
                    )}
                  </CardContent>
                  <CardActions>
                    {campaign.status === 'active' && (
                      <Button
                        size="small"
                        startIcon={<Pause />}
                        onClick={() => handlePauseCampaign(campaign)}
                      >
                        일시정지
                      </Button>
                    )}
                    {campaign.status === 'paused' && (
                      <Button
                        size="small"
                        startIcon={<PlayArrow />}
                        color="primary"
                      >
                        재개
                      </Button>
                    )}
                    <Button
                      size="small"
                      startIcon={<ContentCopy />}
                      onClick={() => handleDuplicateCampaign(campaign)}
                    >
                      복제
                    </Button>
                    <IconButton size="small">
                      <BarChart />
                    </IconButton>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          {/* Automations */}
          <Box sx={{ mb: 3, display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              variant="contained"
              startIcon={<AutoAwesome />}
              onClick={() => setAutomationDialogOpen(true)}
            >
              새 자동화
            </Button>
          </Box>
          
          <Grid container spacing={3}>
            {automations.map((automation) => (
              <Grid item xs={12} key={automation.id}>
                <Paper sx={{ p: 3 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Avatar sx={{ bgcolor: automation.status === 'active' ? 'success.light' : 'grey.300' }}>
                        <Psychology />
                      </Avatar>
                      <Box>
                        <Typography variant="h6">{automation.name}</Typography>
                        <Typography variant="body2" color="text.secondary">
                          트리거: {automation.trigger}
                        </Typography>
                      </Box>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={automation.status === 'active'}
                            onChange={() => handleToggleAutomation(automation)}
                          />
                        }
                        label={automation.status === 'active' ? '활성' : '비활성'}
                      />
                      <IconButton>
                        <Edit />
                      </IconButton>
                    </Box>
                  </Box>
                  
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 4, mb: 2 }}>
                    {automation.actions.map((action, index) => (
                      <React.Fragment key={index}>
                        {index > 0 && <Box sx={{ width: 40, height: 2, bgcolor: 'grey.300' }} />}
                        <Chip label={action} variant="outlined" />
                      </React.Fragment>
                    ))}
                  </Box>
                  
                  <Divider sx={{ my: 2 }} />
                  
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="body2" color="text.secondary">
                        대상 고객
                      </Typography>
                      <Typography variant="h6">
                        {formatNumber(automation.targetCount)}명
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="body2" color="text.secondary">
                        총 실행 횟수
                      </Typography>
                      <Typography variant="h6">
                        {formatNumber(automation.executionCount)}회
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="body2" color="text.secondary">
                        마지막 실행
                      </Typography>
                      <Typography variant="h6">
                        {formatDate(automation.lastRun)}
                      </Typography>
                    </Grid>
                  </Grid>
                </Paper>
              </Grid>
            ))}
          </Grid>
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          {/* Templates */}
          <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <ToggleButtonGroup
              value="email"
              exclusive
              size="small"
            >
              <ToggleButton value="all">
                전체
              </ToggleButton>
              <ToggleButton value="email">
                <Email sx={{ mr: 1, fontSize: 20 }} />
                이메일
              </ToggleButton>
              <ToggleButton value="sms">
                <Sms sx={{ mr: 1, fontSize: 20 }} />
                SMS
              </ToggleButton>
              <ToggleButton value="push">
                <NotificationsActive sx={{ mr: 1, fontSize: 20 }} />
                푸시
              </ToggleButton>
            </ToggleButtonGroup>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setTemplateDialogOpen(true)}
            >
              새 템플릿
            </Button>
          </Box>
          
          <Grid container spacing={3}>
            {templates.map((template) => (
              <Grid item xs={12} sm={6} md={4} key={template.id}>
                <Card>
                  <Box
                    sx={{
                      height: 200,
                      bgcolor: 'grey.100',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {template.type === 'email' && <Email sx={{ fontSize: 60, color: 'grey.400' }} />}
                    {template.type === 'sms' && <Sms sx={{ fontSize: 60, color: 'grey.400' }} />}
                    {template.type === 'push' && <NotificationsActive sx={{ fontSize: 60, color: 'grey.400' }} />}
                  </Box>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      {template.name}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <Chip label={template.category} size="small" />
                      <Typography variant="body2" color="text.secondary">
                        사용 {template.usageCount}회
                      </Typography>
                    </Box>
                  </CardContent>
                  <CardActions>
                    <Button size="small">미리보기</Button>
                    <Button size="small" color="primary">사용하기</Button>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          {/* Analytics */}
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  캠페인 성과 요약
                </Typography>
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>캠페인명</TableCell>
                        <TableCell>유형</TableCell>
                        <TableCell align="right">전송</TableCell>
                        <TableCell align="right">오픈율</TableCell>
                        <TableCell align="right">클릭률</TableCell>
                        <TableCell align="right">전환율</TableCell>
                        <TableCell align="right">수익</TableCell>
                        <TableCell align="right">ROI</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {campaigns.filter(c => c.status !== 'draft').map((campaign) => (
                        <TableRow key={campaign.id}>
                          <TableCell>{campaign.name}</TableCell>
                          <TableCell>
                            <Chip
                              icon={getCampaignIcon(campaign.type)}
                              label={campaign.type.toUpperCase()}
                              size="small"
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell align="right">{formatNumber(campaign.sent)}</TableCell>
                          <TableCell align="right">
                            {formatPercentage(campaign.opened / campaign.sent)}
                          </TableCell>
                          <TableCell align="right">
                            {formatPercentage(campaign.clicked / campaign.sent)}
                          </TableCell>
                          <TableCell align="right">
                            {formatPercentage(campaign.converted / campaign.sent)}
                          </TableCell>
                          <TableCell align="right">
                            {formatCurrency(campaign.revenue)}
                          </TableCell>
                          <TableCell align="right">
                            {campaign.spent ? 
                              formatPercentage((campaign.revenue - campaign.spent) / campaign.spent) :
                              '-'
                            }
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    채널별 성과
                  </Typography>
                  <List>
                    <ListItem>
                      <ListItemIcon>
                        <Email color="primary" />
                      </ListItemIcon>
                      <ListItemText
                        primary="이메일"
                        secondary="평균 오픈율 38% • 클릭률 12%"
                      />
                      <Chip label="우수" color="success" size="small" />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <Sms color="secondary" />
                      </ListItemIcon>
                      <ListItemText
                        primary="SMS"
                        secondary="평균 오픈율 95% • 클릭률 8%"
                      />
                      <Chip label="양호" color="warning" size="small" />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <NotificationsActive color="info" />
                      </ListItemIcon>
                      <ListItemText
                        primary="푸시 알림"
                        secondary="평균 오픈율 65% • 클릭률 15%"
                      />
                      <Chip label="우수" color="success" size="small" />
                    </ListItem>
                  </List>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    자동화 효과
                  </Typography>
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      자동화로 절약된 시간
                    </Typography>
                    <Typography variant="h4" color="primary">
                      156시간/월
                    </Typography>
                  </Box>
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      자동화 캠페인 수익
                    </Typography>
                    <Typography variant="h4" color="success.main">
                      {formatCurrency(8900000)}
                    </Typography>
                  </Box>
                  <Alert severity="info">
                    자동화를 통해 매출이 평균 23% 증가했습니다.
                  </Alert>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>

        {/* Create Campaign Dialog */}
        <Dialog open={campaignDialogOpen} onClose={() => setCampaignDialogOpen(false)} maxWidth="md" fullWidth>
          <DialogTitle>새 캠페인 만들기</DialogTitle>
          <DialogContent dividers>
            <Stepper activeStep={activeStep} orientation="vertical">
              <Step>
                <StepLabel>캠페인 유형 선택</StepLabel>
                <StepContent>
                  <Grid container spacing={2}>
                    {[
                      { value: 'email', label: '이메일', icon: <Email /> },
                      { value: 'sms', label: 'SMS', icon: <Sms /> },
                      { value: 'push', label: '푸시 알림', icon: <NotificationsActive /> },
                      { value: 'coupon', label: '쿠폰', icon: <LocalOffer /> },
                      { value: 'event', label: '이벤트', icon: <Celebration /> },
                    ].map((type) => (
                      <Grid item xs={12} sm={4} key={type.value}>
                        <Card
                          variant={campaignType === type.value ? 'elevation' : 'outlined'}
                          sx={{
                            cursor: 'pointer',
                            borderColor: campaignType === type.value ? 'primary.main' : undefined,
                            borderWidth: campaignType === type.value ? 2 : 1,
                          }}
                          onClick={() => setCampaignType(type.value as Campaign['type'])}
                        >
                          <CardContent sx={{ textAlign: 'center' }}>
                            <Avatar sx={{ bgcolor: 'primary.light', mx: 'auto', mb: 1 }}>
                              {type.icon}
                            </Avatar>
                            <Typography variant="subtitle1">{type.label}</Typography>
                          </CardContent>
                        </Card>
                      </Grid>
                    ))}
                  </Grid>
                </StepContent>
              </Step>
              
              <Step>
                <StepLabel>캠페인 설정</StepLabel>
                <StepContent>
                  <Grid container spacing={2}>
                    <Grid item xs={12}>
                      <TextField
                        fullWidth
                        label="캠페인명"
                        placeholder="예: 2024년 신년 특별 할인"
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <FormControl fullWidth>
                        <InputLabel>대상 고객</InputLabel>
                        <Select
                          value={selectedAudience}
                          onChange={(e) => setSelectedAudience(e.target.value)}
                          label="대상 고객"
                        >
                          {audienceOptions.map((option) => (
                            <MenuItem key={option.value} value={option.value}>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                                <span>{option.label}</span>
                                <Chip label={`${option.count}명`} size="small" />
                              </Box>
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <DateTimePicker
                        label="발송 일시"
                        value={scheduledDate}
                        onChange={setScheduledDate}
                        slotProps={{ textField: { fullWidth: true } }}
                      />
                    </Grid>
                    {campaignType === 'email' && (
                      <Grid item xs={12}>
                        <FormControl fullWidth>
                          <InputLabel>템플릿 선택</InputLabel>
                          <Select
                            value={selectedTemplate}
                            onChange={(e) => setSelectedTemplate(e.target.value)}
                            label="템플릿 선택"
                          >
                            <MenuItem value="">직접 작성</MenuItem>
                            {templates.filter(t => t.type === 'email').map((template) => (
                              <MenuItem key={template.id} value={template.id}>
                                {template.name}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Grid>
                    )}
                  </Grid>
                </StepContent>
              </Step>
              
              <Step>
                <StepLabel>내용 작성</StepLabel>
                <StepContent>
                  <Grid container spacing={2}>
                    {campaignType === 'email' && (
                      <>
                        <Grid item xs={12}>
                          <TextField
                            fullWidth
                            label="제목"
                            placeholder="이메일 제목을 입력하세요"
                          />
                        </Grid>
                        <Grid item xs={12}>
                          <TextField
                            fullWidth
                            multiline
                            rows={6}
                            label="내용"
                            placeholder="이메일 내용을 입력하세요"
                          />
                        </Grid>
                      </>
                    )}
                    {campaignType === 'sms' && (
                      <Grid item xs={12}>
                        <TextField
                          fullWidth
                          multiline
                          rows={4}
                          label="메시지"
                          placeholder="SMS 메시지를 입력하세요 (최대 80자)"
                          inputProps={{ maxLength: 80 }}
                          helperText="0 / 80자"
                        />
                      </Grid>
                    )}
                    {campaignType === 'coupon' && (
                      <>
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth
                            label="쿠폰명"
                            placeholder="예: 신년 특별 할인"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth
                            label="할인율/금액"
                            placeholder="예: 20% 또는 5,000원"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <DateTimePicker
                            label="유효 시작일"
                            value={null}
                            onChange={() => {}}
                            slotProps={{ textField: { fullWidth: true } }}
                          />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <DateTimePicker
                            label="유효 종료일"
                            value={null}
                            onChange={() => {}}
                            slotProps={{ textField: { fullWidth: true } }}
                          />
                        </Grid>
                      </>
                    )}
                  </Grid>
                </StepContent>
              </Step>
            </Stepper>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCampaignDialogOpen(false)}>취소</Button>
            {activeStep > 0 && (
              <Button onClick={() => setActiveStep(prev => prev - 1)}>이전</Button>
            )}
            <Button variant="contained" onClick={handleCreateCampaign}>
              {activeStep === 2 ? '캠페인 생성' : '다음'}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Create Automation Dialog */}
        <Dialog open={automationDialogOpen} onClose={() => setAutomationDialogOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle>새 자동화 만들기</DialogTitle>
          <DialogContent dividers>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="자동화 이름"
                  placeholder="예: 신규 가입 환영 시리즈"
                />
              </Grid>
              <Grid item xs={12}>
                <Typography variant="subtitle2" gutterBottom>
                  트리거 선택
                </Typography>
                <Grid container spacing={1}>
                  {triggerOptions.map((trigger) => (
                    <Grid item xs={12} sm={6} key={trigger.value}>
                      <Card
                        variant={automationTrigger === trigger.value ? 'elevation' : 'outlined'}
                        sx={{
                          cursor: 'pointer',
                          borderColor: automationTrigger === trigger.value ? 'primary.main' : undefined,
                          borderWidth: automationTrigger === trigger.value ? 2 : 1,
                        }}
                        onClick={() => setAutomationTrigger(trigger.value)}
                      >
                        <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 1.5 }}>
                          {trigger.icon}
                          <Typography variant="body2">{trigger.label}</Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              </Grid>
              <Grid item xs={12}>
                <Typography variant="subtitle2" gutterBottom>
                  액션 설정
                </Typography>
                <Alert severity="info" sx={{ mb: 2 }}>
                  트리거 발생 시 실행될 액션을 순서대로 추가하세요.
                </Alert>
                <Stack spacing={2}>
                  <Chip label="1. 환영 이메일 발송" onDelete={() => {}} />
                  <Chip label="2. 3일 후 - 첫 구매 10% 할인 쿠폰" onDelete={() => {}} />
                  <Chip label="3. 7일 후 - 인기 상품 추천" onDelete={() => {}} />
                  <Button variant="outlined" startIcon={<Add />} size="small">
                    액션 추가
                  </Button>
                </Stack>
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setAutomationDialogOpen(false)}>취소</Button>
            <Button variant="contained" onClick={handleCreateAutomation}>
              자동화 생성
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </LocalizationProvider>
  )
}

export default Marketing