import React, { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Paper,
  Chip,
  Button,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Avatar,
  IconButton,
  Tooltip,
  Alert,
  Tab,
  Tabs,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material'
import {
  Speed,
  Storage,
  Memory,
  NetworkCheck,
  Security,
  Warning,
  CheckCircle,
  Error,
  Refresh,
  Timeline,
  BugReport,
  CloudQueue,
  Api,
  Schedule,
  NotificationsActive,
} from '@mui/icons-material'
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

// 샘플 데이터
const systemMetrics = [
  {
    name: 'CPU 사용률',
    value: 68,
    status: 'normal',
    icon: <Speed />,
    unit: '%',
  },
  {
    name: '메모리 사용률',
    value: 45,
    status: 'normal',
    icon: <Memory />,
    unit: '%',
  },
  {
    name: '디스크 사용률',
    value: 82,
    status: 'warning',
    icon: <Storage />,
    unit: '%',
  },
  {
    name: '네트워크 대역폭',
    value: 35,
    status: 'normal',
    icon: <NetworkCheck />,
    unit: '%',
  },
]

const performanceData = Array.from({ length: 24 }, (_, i) => ({
  time: `${i}:00`,
  cpu: Math.random() * 30 + 40,
  memory: Math.random() * 20 + 35,
  requests: Math.floor(Math.random() * 500 + 1000),
}))

const apiEndpoints = [
  { endpoint: '/api/products', status: 'operational', avgResponseTime: 120, requests: 5420, errors: 3 },
  { endpoint: '/api/orders', status: 'operational', avgResponseTime: 98, requests: 3210, errors: 0 },
  { endpoint: '/api/auth', status: 'degraded', avgResponseTime: 350, requests: 1850, errors: 12 },
  { endpoint: '/api/analytics', status: 'operational', avgResponseTime: 220, requests: 890, errors: 1 },
]

const recentEvents = [
  { id: 1, type: 'error', message: '인증 서비스 응답 시간 증가', time: '5분 전', severity: 'high' },
  { id: 2, type: 'warning', message: '디스크 사용률 80% 초과', time: '15분 전', severity: 'medium' },
  { id: 3, type: 'info', message: '백업 완료', time: '1시간 전', severity: 'low' },
  { id: 4, type: 'success', message: '시스템 업데이트 성공', time: '3시간 전', severity: 'low' },
]

const serviceStatus = [
  { name: '웹 서버', status: 'operational', uptime: 99.9 },
  { name: 'API 서버', status: 'operational', uptime: 99.8 },
  { name: '데이터베이스', status: 'operational', uptime: 99.95 },
  { name: '캐시 서버', status: 'degraded', uptime: 98.5 },
  { name: '검색 엔진', status: 'operational', uptime: 99.7 },
]

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index, ...other }) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`monitoring-tabpanel-${index}`}
      aria-labelledby={`monitoring-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  )
}

const SystemMonitoring: React.FC = () => {
  const [tabValue, setTabValue] = useState(0)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        setRefreshCount(prev => prev + 1)
      }, 5000) // 5초마다 새로고침
      return () => clearInterval(interval)
    }
  }, [autoRefresh])

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'operational':
        return 'success'
      case 'degraded':
        return 'warning'
      case 'down':
        return 'error'
      default:
        return 'default'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'operational':
        return <CheckCircle color="success" />
      case 'degraded':
        return <Warning color="warning" />
      case 'down':
        return <Error color="error" />
      default:
        return null
    }
  }

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'error':
        return <Error color="error" />
      case 'warning':
        return <Warning color="warning" />
      case 'info':
        return <NotificationsActive color="info" />
      case 'success':
        return <CheckCircle color="success" />
      default:
        return null
    }
  }

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          시스템 모니터링
        </Typography>
        <Typography variant="body1" color="text.secondary">
          실시간 시스템 상태와 성능을 모니터링합니다
        </Typography>
      </Box>

      {/* 시스템 상태 요약 */}
      <Alert
        severity="info"
        sx={{ mb: 3 }}
        action={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip
              label={autoRefresh ? '자동 새로고침 ON' : '자동 새로고침 OFF'}
              color={autoRefresh ? 'primary' : 'default'}
              size="small"
              onClick={() => setAutoRefresh(!autoRefresh)}
            />
            <IconButton size="small" onClick={() => setRefreshCount(prev => prev + 1)}>
              <Refresh />
            </IconButton>
          </Box>
        }
      >
        전체 시스템 상태: <strong>정상</strong> | 
        가동률: <strong>99.8%</strong> | 
        마지막 업데이트: <strong>방금 전</strong>
      </Alert>

      {/* 주요 메트릭스 */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {systemMetrics.map((metric) => (
          <Grid item xs={12} sm={6} md={3} key={metric.name}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Avatar
                    sx={{
                      bgcolor: metric.status === 'warning' ? 'warning.light' : 'primary.light',
                      color: metric.status === 'warning' ? 'warning.main' : 'primary.main',
                    }}
                  >
                    {metric.icon}
                  </Avatar>
                  <Box sx={{ ml: 2, flexGrow: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      {metric.name}
                    </Typography>
                    <Typography variant="h4">
                      {metric.value}{metric.unit}
                    </Typography>
                  </Box>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={metric.value}
                  color={metric.status === 'warning' ? 'warning' : 'primary'}
                  sx={{ height: 8, borderRadius: 4 }}
                />
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* 탭 네비게이션 */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="실시간 성능" />
          <Tab label="서비스 상태" />
          <Tab label="API 모니터링" />
          <Tab label="이벤트 로그" />
        </Tabs>
      </Box>

      {/* 실시간 성능 탭 */}
      <TabPanel value={tabValue} index={0}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  CPU & 메모리 사용률
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={performanceData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis />
                    <RechartsTooltip />
                    <Line
                      type="monotone"
                      dataKey="cpu"
                      stroke="#8884d8"
                      strokeWidth={2}
                      name="CPU"
                    />
                    <Line
                      type="monotone"
                      dataKey="memory"
                      stroke="#82ca9d"
                      strokeWidth={2}
                      name="메모리"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  요청 처리량
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={performanceData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis />
                    <RechartsTooltip />
                    <Area
                      type="monotone"
                      dataKey="requests"
                      stroke="#ffc658"
                      fill="#ffc658"
                      fillOpacity={0.6}
                      name="요청/분"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* 서비스 상태 탭 */}
      <TabPanel value={tabValue} index={1}>
        <Grid container spacing={3}>
          {serviceStatus.map((service) => (
            <Grid item xs={12} md={6} lg={4} key={service.name}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6">{service.name}</Typography>
                    {getStatusIcon(service.status)}
                  </Box>
                  <Chip
                    label={service.status.toUpperCase()}
                    color={getStatusColor(service.status) as any}
                    size="small"
                    sx={{ mb: 2 }}
                  />
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="body2" color="text.secondary">
                      가동률
                    </Typography>
                    <Typography variant="h6" color={service.uptime >= 99 ? 'success.main' : 'warning.main'}>
                      {service.uptime}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={service.uptime}
                    color={service.uptime >= 99 ? 'success' : 'warning'}
                    sx={{ mt: 1, height: 6, borderRadius: 3 }}
                  />
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </TabPanel>

      {/* API 모니터링 탭 */}
      <TabPanel value={tabValue} index={2}>
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>엔드포인트</TableCell>
                <TableCell align="center">상태</TableCell>
                <TableCell align="center">평균 응답시간</TableCell>
                <TableCell align="center">요청 수</TableCell>
                <TableCell align="center">오류</TableCell>
                <TableCell align="center">오류율</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {apiEndpoints.map((api) => (
                <TableRow key={api.endpoint}>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Api sx={{ mr: 1, color: 'text.secondary' }} />
                      <Typography variant="body2">{api.endpoint}</Typography>
                    </Box>
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={api.status.toUpperCase()}
                      size="small"
                      color={getStatusColor(api.status) as any}
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Typography
                      variant="body2"
                      color={api.avgResponseTime > 300 ? 'error' : 'text.primary'}
                    >
                      {api.avgResponseTime}ms
                    </Typography>
                  </TableCell>
                  <TableCell align="center">{api.requests.toLocaleString()}</TableCell>
                  <TableCell align="center">
                    <Typography
                      variant="body2"
                      color={api.errors > 0 ? 'error' : 'text.primary'}
                    >
                      {api.errors}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Typography
                      variant="body2"
                      color={api.errors / api.requests > 0.01 ? 'error' : 'success.main'}
                    >
                      {((api.errors / api.requests) * 100).toFixed(2)}%
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </TabPanel>

      {/* 이벤트 로그 탭 */}
      <TabPanel value={tabValue} index={3}>
        <List>
          {recentEvents.map((event) => (
            <React.Fragment key={event.id}>
              <ListItem>
                <ListItemIcon>
                  {getEventIcon(event.type)}
                </ListItemIcon>
                <ListItemText
                  primary={event.message}
                  secondary={event.time}
                />
                <Chip
                  label={event.severity}
                  size="small"
                  color={
                    event.severity === 'high' ? 'error' :
                    event.severity === 'medium' ? 'warning' : 'default'
                  }
                />
              </ListItem>
              <Divider />
            </React.Fragment>
          ))}
        </List>
        <Box sx={{ mt: 2, textAlign: 'center' }}>
          <Button variant="outlined">
            전체 로그 보기
          </Button>
        </Box>
      </TabPanel>

      {/* 시스템 상태 요약 카드 */}
      <Paper
        sx={{
          position: 'fixed',
          bottom: 20,
          right: 20,
          p: 2,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          bgcolor: 'success.main',
          color: 'success.contrastText',
        }}
        elevation={3}
      >
        <CheckCircle />
        <Typography variant="body2">모든 시스템 정상 작동 중</Typography>
      </Paper>
    </Box>
  )
}

export default SystemMonitoring