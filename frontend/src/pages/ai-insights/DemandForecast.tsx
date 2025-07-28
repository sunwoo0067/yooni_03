import React, { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  Alert,
  LinearProgress,
  Tabs,
  Tab,
  Badge,
  Avatar,
} from '@mui/material'
import {
  Timeline,
  TrendingUp,
  Warning,
  CheckCircle,
  Psychology,
  CalendarMonth,
  Inventory,
  ShoppingCart,
  CloudQueue,
  WbSunny,
  AcUnit,
  Event,
  Download,
  Refresh,
} from '@mui/icons-material'
import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Cell, Legend } from 'recharts'

// 샘플 데이터
const demandForecastData = [
  { month: '1월', actual: 1200, predicted: 1150, lowerBound: 1050, upperBound: 1250 },
  { month: '2월', actual: 1350, predicted: 1320, lowerBound: 1200, upperBound: 1440 },
  { month: '3월', actual: 1500, predicted: 1480, lowerBound: 1350, upperBound: 1610 },
  { month: '4월', actual: 1650, predicted: 1680, lowerBound: 1540, upperBound: 1820 },
  { month: '5월', actual: 1800, predicted: 1850, lowerBound: 1700, upperBound: 2000 },
  { month: '6월', actual: null, predicted: 2100, lowerBound: 1930, upperBound: 2270 },
  { month: '7월', actual: null, predicted: 2350, lowerBound: 2160, upperBound: 2540 },
  { month: '8월', actual: null, predicted: 2200, lowerBound: 2020, upperBound: 2380 },
]

const categoryForecast = [
  {
    category: '전자제품',
    currentStock: 450,
    predictedDemand: 680,
    stockStatus: 'low',
    growthRate: 25,
    seasonalFactor: 'high',
  },
  {
    category: '패션',
    currentStock: 820,
    predictedDemand: 750,
    stockStatus: 'optimal',
    growthRate: 15,
    seasonalFactor: 'medium',
  },
  {
    category: '스포츠/레저',
    currentStock: 320,
    predictedDemand: 520,
    stockStatus: 'critical',
    growthRate: 42,
    seasonalFactor: 'high',
  },
  {
    category: '생활용품',
    currentStock: 650,
    predictedDemand: 600,
    stockStatus: 'optimal',
    growthRate: 8,
    seasonalFactor: 'low',
  },
]

const seasonalFactors = [
  { factor: '여름 시즌', impact: 85, icon: <WbSunny />, categories: ['에어컨', '선풍기', '수영복'] },
  { factor: '휴가철', impact: 72, icon: <Event />, categories: ['여행용품', '캠핑장비', '선크림'] },
  { factor: '신학기', impact: 65, icon: <CalendarMonth />, categories: ['문구류', '가방', '전자기기'] },
]

const productAlerts = [
  {
    product: '무선 이어폰 프로',
    alert: '재고 부족 예상',
    severity: 'error',
    predictedShortage: '3일 후',
    recommendation: '긴급 발주 필요',
  },
  {
    product: '캠핑 체어',
    alert: '수요 급증 예상',
    severity: 'warning',
    predictedIncrease: '35%',
    recommendation: '재고 확충 권장',
  },
  {
    product: '요가매트',
    alert: '적정 재고 유지',
    severity: 'success',
    stockDays: 15,
    recommendation: '현 수준 유지',
  },
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
      id={`forecast-tabpanel-${index}`}
      aria-labelledby={`forecast-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  )
}

const DemandForecast: React.FC = () => {
  const [timeRange, setTimeRange] = useState('3months')
  const [category, setCategory] = useState('all')
  const [tabValue, setTabValue] = useState(0)

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
  }

  const getStockStatusColor = (status: string) => {
    switch (status) {
      case 'critical':
        return 'error'
      case 'low':
        return 'warning'
      case 'optimal':
        return 'success'
      case 'excess':
        return 'info'
      default:
        return 'default'
    }
  }

  const getStockStatusText = (status: string) => {
    switch (status) {
      case 'critical':
        return '긴급'
      case 'low':
        return '부족'
      case 'optimal':
        return '적정'
      case 'excess':
        return '과잉'
      default:
        return status
    }
  }

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          AI 수요 예측
        </Typography>
        <Typography variant="body1" color="text.secondary">
          AI가 예측한 수요 변화를 확인하고 재고를 최적화하세요
        </Typography>
      </Box>

      {/* 필터 및 컨트롤 */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={3}>
              <FormControl fullWidth>
                <InputLabel>예측 기간</InputLabel>
                <Select
                  value={timeRange}
                  onChange={(e) => setTimeRange(e.target.value)}
                  label="예측 기간"
                >
                  <MenuItem value="1month">1개월</MenuItem>
                  <MenuItem value="3months">3개월</MenuItem>
                  <MenuItem value="6months">6개월</MenuItem>
                  <MenuItem value="1year">1년</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={3}>
              <FormControl fullWidth>
                <InputLabel>카테고리</InputLabel>
                <Select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  label="카테고리"
                >
                  <MenuItem value="all">전체</MenuItem>
                  <MenuItem value="electronics">전자제품</MenuItem>
                  <MenuItem value="fashion">패션</MenuItem>
                  <MenuItem value="sports">스포츠/레저</MenuItem>
                  <MenuItem value="home">생활용품</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                <Button variant="outlined" startIcon={<Download />}>
                  리포트 다운로드
                </Button>
                <Button variant="contained" startIcon={<Refresh />}>
                  예측 업데이트
                </Button>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* AI 예측 정확도 */}
      <Alert
        severity="success"
        sx={{ mb: 3 }}
        icon={<Psychology />}
      >
        AI 예측 정확도: <strong>92.5%</strong> | 
        지난 3개월 평균 오차율: <strong>±7.5%</strong> | 
        다음 업데이트: <strong>2시간 후</strong>
      </Alert>

      {/* 탭 네비게이션 */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="수요 예측" />
          <Tab label="카테고리별 분석" />
          <Tab label="재고 알림" />
          <Tab label="계절성 분석" />
        </Tabs>
      </Box>

      {/* 수요 예측 탭 */}
      <TabPanel value={tabValue} index={0}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              월별 수요 예측
            </Typography>
            <ResponsiveContainer width="100%" height={400}>
              <AreaChart data={demandForecastData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <RechartsTooltip />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="upperBound"
                  stackId="1"
                  stroke="none"
                  fill="#e3f2fd"
                  name="예측 상한"
                />
                <Area
                  type="monotone"
                  dataKey="lowerBound"
                  stackId="2"
                  stroke="none"
                  fill="#e3f2fd"
                  name="예측 하한"
                />
                <Line
                  type="monotone"
                  dataKey="predicted"
                  stroke="#2196f3"
                  strokeWidth={3}
                  dot={{ r: 4 }}
                  name="AI 예측"
                />
                <Line
                  type="monotone"
                  dataKey="actual"
                  stroke="#4caf50"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={{ r: 4 }}
                  name="실제"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </TabPanel>

      {/* 카테고리별 분석 탭 */}
      <TabPanel value={tabValue} index={1}>
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>카테고리</TableCell>
                <TableCell align="center">현재 재고</TableCell>
                <TableCell align="center">예상 수요</TableCell>
                <TableCell align="center">재고 상태</TableCell>
                <TableCell align="center">성장률</TableCell>
                <TableCell align="center">계절 요인</TableCell>
                <TableCell align="center">권장 조치</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {categoryForecast.map((item) => (
                <TableRow key={item.category}>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {item.category}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">{item.currentStock.toLocaleString()}</TableCell>
                  <TableCell align="center">
                    <Typography color="primary" fontWeight="bold">
                      {item.predictedDemand.toLocaleString()}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={getStockStatusText(item.stockStatus)}
                      size="small"
                      color={getStockStatusColor(item.stockStatus) as any}
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <TrendingUp color="success" fontSize="small" />
                      <Typography variant="body2" color="success.main" sx={{ ml: 0.5 }}>
                        +{item.growthRate}%
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={item.seasonalFactor}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Button
                      size="small"
                      variant={item.stockStatus === 'critical' ? 'contained' : 'outlined'}
                      color={item.stockStatus === 'critical' ? 'error' : 'primary'}
                    >
                      재고 계획
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </TabPanel>

      {/* 재고 알림 탭 */}
      <TabPanel value={tabValue} index={2}>
        <Grid container spacing={3}>
          {productAlerts.map((alert, index) => (
            <Grid item xs={12} key={index}>
              <Alert
                severity={alert.severity as any}
                sx={{ mb: 2 }}
                action={
                  <Button size="small" variant="outlined">
                    {alert.recommendation}
                  </Button>
                }
              >
                <Typography variant="subtitle2">{alert.product}</Typography>
                <Typography variant="body2">
                  {alert.alert} - {alert.predictedShortage || alert.predictedIncrease || `재고 가용일: ${alert.stockDays}일`}
                </Typography>
              </Alert>
            </Grid>
          ))}
          
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  재고 회전율 분석
                </Typography>
                <Grid container spacing={3} sx={{ mt: 1 }}>
                  <Grid item xs={12} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'success.light' }}>
                      <Inventory sx={{ fontSize: 40, color: 'success.main' }} />
                      <Typography variant="h4" color="success.main">
                        85%
                      </Typography>
                      <Typography variant="body2">최적 재고율</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'warning.light' }}>
                      <ShoppingCart sx={{ fontSize: 40, color: 'warning.main' }} />
                      <Typography variant="h4" color="warning.main">
                        12일
                      </Typography>
                      <Typography variant="body2">평균 재고 회전일</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'error.light' }}>
                      <Warning sx={{ fontSize: 40, color: 'error.main' }} />
                      <Typography variant="h4" color="error.main">
                        3
                      </Typography>
                      <Typography variant="body2">긴급 발주 필요</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'info.light' }}>
                      <CheckCircle sx={{ fontSize: 40, color: 'info.main' }} />
                      <Typography variant="h4" color="info.main">
                        92%
                      </Typography>
                      <Typography variant="body2">재고 정확도</Typography>
                    </Paper>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* 계절성 분석 탭 */}
      <TabPanel value={tabValue} index={3}>
        <Grid container spacing={3}>
          {seasonalFactors.map((factor, index) => (
            <Grid item xs={12} md={4} key={index}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Avatar sx={{ bgcolor: 'primary.light', mr: 2 }}>
                      {factor.icon}
                    </Avatar>
                    <Box sx={{ flexGrow: 1 }}>
                      <Typography variant="subtitle1">{factor.factor}</Typography>
                      <Typography variant="h6" color="primary">
                        영향도: {factor.impact}%
                      </Typography>
                    </Box>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={factor.impact}
                    sx={{ mb: 2, height: 8, borderRadius: 4 }}
                  />
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    주요 영향 카테고리:
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {factor.categories.map((cat) => (
                      <Chip key={cat} label={cat} size="small" />
                    ))}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
          
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  계절별 수요 패턴
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={[
                    { season: '봄', electronics: 65, fashion: 85, sports: 70, home: 60 },
                    { season: '여름', electronics: 80, fashion: 70, sports: 95, home: 75 },
                    { season: '가을', electronics: 75, fashion: 90, sports: 60, home: 70 },
                    { season: '겨울', electronics: 90, fashion: 80, sports: 50, home: 85 },
                  ]}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="season" />
                    <YAxis />
                    <RechartsTooltip />
                    <Legend />
                    <Bar dataKey="electronics" fill="#8884d8" name="전자제품" />
                    <Bar dataKey="fashion" fill="#82ca9d" name="패션" />
                    <Bar dataKey="sports" fill="#ffc658" name="스포츠" />
                    <Bar dataKey="home" fill="#ff7c7c" name="생활용품" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>
    </Box>
  )
}

export default DemandForecast