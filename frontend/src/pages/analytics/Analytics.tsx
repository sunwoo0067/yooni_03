import React, { useState, useMemo } from 'react'
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tab,
  Tabs,
  Button,
  ButtonGroup,
  IconButton,
  Tooltip,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  LinearProgress,
  Chip,
} from '@mui/material'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts'
import {
  DateRange,
  TrendingUp,
  TrendingDown,
  AttachMoney,
  ShoppingCart,
  Inventory,
  People,
  LocalShipping,
  Star,
  CalendarToday,
  FileDownload,
  Print,
  Refresh,
  FilterList,
  BarChartOutlined,
  ShowChart,
  PieChartOutline,
  Timeline,
} from '@mui/icons-material'
import { formatCurrency, formatNumber, formatPercentage, formatDate } from '@utils/format'
import { toast } from 'react-hot-toast'
import { DatePicker } from '@mui/x-date-pickers/DatePicker'
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider'
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns'
import { ko } from 'date-fns/locale'

// Types
interface StatCard {
  title: string
  value: string | number
  change: number
  icon: React.ReactNode
  color: string
}

interface ChartData {
  name: string
  value: number
  [key: string]: any
}

interface ProductPerformance {
  id: string
  name: string
  sales: number
  revenue: number
  quantity: number
  avgPrice: number
  growth: number
}

interface PlatformAnalytics {
  platform: string
  orders: number
  revenue: number
  products: number
  conversionRate: number
}

const Analytics: React.FC = () => {
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().setMonth(new Date().getMonth() - 1)),
    end: new Date(),
  })
  const [period, setPeriod] = useState('month')
  const [tabValue, setTabValue] = useState(0)
  const [chartType, setChartType] = useState('line')
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(10)

  // Mock data
  const salesData = [
    { name: '1월', 매출: 4500000, 주문: 120, 평균주문액: 37500 },
    { name: '2월', 매출: 5200000, 주문: 145, 평균주문액: 35862 },
    { name: '3월', 매출: 4800000, 주문: 132, 평균주문액: 36364 },
    { name: '4월', 매출: 5800000, 주문: 158, 평균주문액: 36709 },
    { name: '5월', 매출: 6200000, 주문: 165, 평균주문액: 37576 },
    { name: '6월', 매출: 7100000, 주문: 189, 평균주문액: 37566 },
    { name: '7월', 매출: 6800000, 주문: 178, 평균주문액: 38202 },
    { name: '8월', 매출: 7500000, 주문: 195, 평균주문액: 38462 },
    { name: '9월', 매출: 8200000, 주문: 210, 평균주문액: 39048 },
    { name: '10월', 매출: 8900000, 주문: 225, 평균주문액: 39556 },
    { name: '11월', 매출: 9500000, 주문: 245, 평균주문액: 38776 },
    { name: '12월', 매출: 10200000, 주문: 268, 평균주문액: 38060 },
  ]

  const categoryData = [
    { name: '전자기기', value: 35, revenue: 45000000 },
    { name: '의류/패션', value: 25, revenue: 32000000 },
    { name: '생활용품', value: 20, revenue: 25600000 },
    { name: '화장품', value: 15, revenue: 19200000 },
    { name: '기타', value: 5, revenue: 6400000 },
  ]

  const platformData: PlatformAnalytics[] = [
    { platform: '쿠팡', orders: 450, revenue: 56000000, products: 156, conversionRate: 3.2 },
    { platform: '네이버', orders: 380, revenue: 42000000, products: 98, conversionRate: 2.8 },
    { platform: 'G마켓', orders: 220, revenue: 18000000, products: 67, conversionRate: 2.1 },
    { platform: '11번가', orders: 180, revenue: 12000000, products: 45, conversionRate: 1.9 },
  ]

  const productPerformance: ProductPerformance[] = [
    { id: '1', name: '무선 이어폰 프로', sales: 2450000, revenue: 24500000, quantity: 245, avgPrice: 100000, growth: 12.5 },
    { id: '2', name: '스마트워치 울트라', sales: 1850000, revenue: 18500000, quantity: 37, avgPrice: 500000, growth: 8.3 },
    { id: '3', name: '충전 케이블 세트', sales: 1200000, revenue: 12000000, quantity: 400, avgPrice: 30000, growth: -5.2 },
    { id: '4', name: '블루투스 스피커', sales: 980000, revenue: 9800000, quantity: 98, avgPrice: 100000, growth: 15.7 },
    { id: '5', name: '무선 충전기', sales: 750000, revenue: 7500000, quantity: 150, avgPrice: 50000, growth: 22.1 },
  ]

  const customerData = [
    { name: '신규 고객', value: 35 },
    { name: '재구매 고객', value: 45 },
    { name: 'VIP 고객', value: 20 },
  ]

  const radarData = [
    { category: '매출', A: 120, B: 110, fullMark: 150 },
    { category: '주문수', A: 98, B: 130, fullMark: 150 },
    { category: '고객수', A: 86, B: 130, fullMark: 150 },
    { category: '재구매율', A: 99, B: 100, fullMark: 150 },
    { category: '평균주문액', A: 85, B: 90, fullMark: 150 },
    { category: '만족도', A: 65, B: 85, fullMark: 150 },
  ]

  // Statistics
  const statistics = useMemo(() => {
    const currentMonthRevenue = 10200000
    const lastMonthRevenue = 9500000
    const revenueGrowth = ((currentMonthRevenue - lastMonthRevenue) / lastMonthRevenue) * 100

    const currentMonthOrders = 268
    const lastMonthOrders = 245
    const orderGrowth = ((currentMonthOrders - lastMonthOrders) / lastMonthOrders) * 100

    const avgOrderValue = currentMonthRevenue / currentMonthOrders
    const conversionRate = 2.8

    return {
      totalRevenue: currentMonthRevenue,
      revenueGrowth,
      totalOrders: currentMonthOrders,
      orderGrowth,
      avgOrderValue,
      conversionRate,
      totalCustomers: 1250,
      customerGrowth: 8.5,
    }
  }, [])

  const statCards: StatCard[] = [
    {
      title: '총 매출',
      value: formatCurrency(statistics.totalRevenue),
      change: statistics.revenueGrowth,
      icon: <AttachMoney />,
      color: 'success.main',
    },
    {
      title: '총 주문',
      value: formatNumber(statistics.totalOrders),
      change: statistics.orderGrowth,
      icon: <ShoppingCart />,
      color: 'primary.main',
    },
    {
      title: '평균 주문액',
      value: formatCurrency(statistics.avgOrderValue),
      change: 3.2,
      icon: <TrendingUp />,
      color: 'warning.main',
    },
    {
      title: '전환율',
      value: formatPercentage(statistics.conversionRate / 100),
      change: 0.3,
      icon: <Timeline />,
      color: 'info.main',
    },
  ]

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8']

  const handleExport = () => {
    toast.success('리포트를 내보냈습니다.')
  }

  const handlePrint = () => {
    window.print()
  }

  const handleRefresh = () => {
    toast.success('데이터를 새로고침했습니다.')
  }

  const renderChart = () => {
    switch (chartType) {
      case 'line':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={salesData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <RechartsTooltip formatter={(value) => formatCurrency(Number(value))} />
              <Legend />
              <Line type="monotone" dataKey="매출" stroke="#8884d8" activeDot={{ r: 8 }} />
              <Line type="monotone" dataKey="주문" stroke="#82ca9d" />
            </LineChart>
          </ResponsiveContainer>
        )
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={salesData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <RechartsTooltip formatter={(value) => formatCurrency(Number(value))} />
              <Legend />
              <Bar dataKey="매출" fill="#8884d8" />
              <Bar dataKey="평균주문액" fill="#82ca9d" />
            </BarChart>
          </ResponsiveContainer>
        )
      case 'area':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart data={salesData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <RechartsTooltip formatter={(value) => formatCurrency(Number(value))} />
              <Legend />
              <Area type="monotone" dataKey="매출" stackId="1" stroke="#8884d8" fill="#8884d8" />
              <Area type="monotone" dataKey="평균주문액" stackId="1" stroke="#82ca9d" fill="#82ca9d" />
            </AreaChart>
          </ResponsiveContainer>
        )
      default:
        return null
    }
  }

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={ko}>
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h4" gutterBottom>
              분석 및 리포트
            </Typography>
            <Typography variant="body1" color="text.secondary">
              비즈니스 성과를 분석하고 인사이트를 얻으세요
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="outlined"
              startIcon={<Refresh />}
              onClick={handleRefresh}
            >
              새로고침
            </Button>
            <Button
              variant="outlined"
              startIcon={<Print />}
              onClick={handlePrint}
            >
              인쇄
            </Button>
            <Button
              variant="contained"
              startIcon={<FileDownload />}
              onClick={handleExport}
            >
              내보내기
            </Button>
          </Box>
        </Box>

        {/* Date Range Selector */}
        <Paper sx={{ p: 2, mb: 3 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={3}>
              <DatePicker
                label="시작일"
                value={dateRange.start}
                onChange={(newValue) => setDateRange({ ...dateRange, start: newValue || new Date() })}
                slotProps={{ textField: { fullWidth: true, size: 'small' } }}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <DatePicker
                label="종료일"
                value={dateRange.end}
                onChange={(newValue) => setDateRange({ ...dateRange, end: newValue || new Date() })}
                slotProps={{ textField: { fullWidth: true, size: 'small' } }}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <ButtonGroup size="small" fullWidth>
                <Button
                  variant={period === 'day' ? 'contained' : 'outlined'}
                  onClick={() => setPeriod('day')}
                >
                  일별
                </Button>
                <Button
                  variant={period === 'week' ? 'contained' : 'outlined'}
                  onClick={() => setPeriod('week')}
                >
                  주별
                </Button>
                <Button
                  variant={period === 'month' ? 'contained' : 'outlined'}
                  onClick={() => setPeriod('month')}
                >
                  월별
                </Button>
                <Button
                  variant={period === 'year' ? 'contained' : 'outlined'}
                  onClick={() => setPeriod('year')}
                >
                  연별
                </Button>
              </ButtonGroup>
            </Grid>
            <Grid item xs={12} md={3}>
              <FormControl size="small" fullWidth>
                <InputLabel>빠른 선택</InputLabel>
                <Select label="빠른 선택" defaultValue="thisMonth">
                  <MenuItem value="today">오늘</MenuItem>
                  <MenuItem value="yesterday">어제</MenuItem>
                  <MenuItem value="thisWeek">이번 주</MenuItem>
                  <MenuItem value="thisMonth">이번 달</MenuItem>
                  <MenuItem value="lastMonth">지난 달</MenuItem>
                  <MenuItem value="thisYear">올해</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </Paper>

        {/* Statistics Cards */}
        <Grid container spacing={3} sx={{ mb: 3 }}>
          {statCards.map((stat, index) => (
            <Grid item xs={12} sm={6} md={3} key={index}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography color="text.secondary" variant="body2">
                        {stat.title}
                      </Typography>
                      <Typography variant="h4" sx={{ mt: 1, mb: 1 }}>
                        {stat.value}
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        {stat.change > 0 ? (
                          <TrendingUp color="success" fontSize="small" />
                        ) : (
                          <TrendingDown color="error" fontSize="small" />
                        )}
                        <Typography
                          variant="body2"
                          color={stat.change > 0 ? 'success.main' : 'error.main'}
                        >
                          {stat.change > 0 ? '+' : ''}{stat.change.toFixed(1)}%
                        </Typography>
                      </Box>
                    </Box>
                    <Box
                      sx={{
                        backgroundColor: `${stat.color}15`,
                        borderRadius: 2,
                        p: 1,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      {React.cloneElement(stat.icon as React.ReactElement, {
                        sx: { fontSize: 40, color: stat.color },
                      })}
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        {/* Tabs */}
        <Paper sx={{ mb: 3 }}>
          <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
            <Tab label="매출 분석" />
            <Tab label="상품 분석" />
            <Tab label="플랫폼 분석" />
            <Tab label="고객 분석" />
            <Tab label="비교 분석" />
          </Tabs>
        </Paper>

        {/* Tab Content */}
        {tabValue === 0 && (
          <Grid container spacing={3}>
            {/* Sales Chart */}
            <Grid item xs={12}>
              <Paper sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                  <Typography variant="h6">매출 추이</Typography>
                  <ButtonGroup size="small">
                    <Button
                      variant={chartType === 'line' ? 'contained' : 'outlined'}
                      onClick={() => setChartType('line')}
                    >
                      <ShowChart />
                    </Button>
                    <Button
                      variant={chartType === 'bar' ? 'contained' : 'outlined'}
                      onClick={() => setChartType('bar')}
                    >
                      <BarChartOutlined />
                    </Button>
                    <Button
                      variant={chartType === 'area' ? 'contained' : 'outlined'}
                      onClick={() => setChartType('area')}
                    >
                      <Timeline />
                    </Button>
                  </ButtonGroup>
                </Box>
                {renderChart()}
              </Paper>
            </Grid>

            {/* Category Distribution */}
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  카테고리별 매출 비중
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={categoryData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={(entry) => `${entry.name} ${entry.value}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {categoryData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <RechartsTooltip />
                  </PieChart>
                </ResponsiveContainer>
              </Paper>
            </Grid>

            {/* Sales Summary */}
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  매출 요약
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableBody>
                      <TableRow>
                        <TableCell>총 매출</TableCell>
                        <TableCell align="right">
                          <Typography variant="h6">{formatCurrency(128200000)}</Typography>
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>월 평균 매출</TableCell>
                        <TableCell align="right">{formatCurrency(10683333)}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>최고 매출월</TableCell>
                        <TableCell align="right">12월 ({formatCurrency(10200000)})</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>최저 매출월</TableCell>
                        <TableCell align="right">1월 ({formatCurrency(4500000)})</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>전년 대비 성장률</TableCell>
                        <TableCell align="right">
                          <Chip label="+25.3%" color="success" size="small" />
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>
          </Grid>
        )}

        {tabValue === 1 && (
          <Grid container spacing={3}>
            {/* Product Performance Table */}
            <Grid item xs={12}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  상품별 성과
                </Typography>
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>상품명</TableCell>
                        <TableCell align="right">판매량</TableCell>
                        <TableCell align="right">매출</TableCell>
                        <TableCell align="right">평균 판매가</TableCell>
                        <TableCell align="center">성장률</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {productPerformance
                        .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                        .map((product) => (
                          <TableRow key={product.id}>
                            <TableCell>{product.name}</TableCell>
                            <TableCell align="right">{formatNumber(product.quantity)}개</TableCell>
                            <TableCell align="right">{formatCurrency(product.revenue)}</TableCell>
                            <TableCell align="right">{formatCurrency(product.avgPrice)}</TableCell>
                            <TableCell align="center">
                              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
                                {product.growth > 0 ? (
                                  <TrendingUp color="success" fontSize="small" />
                                ) : (
                                  <TrendingDown color="error" fontSize="small" />
                                )}
                                <Typography
                                  variant="body2"
                                  color={product.growth > 0 ? 'success.main' : 'error.main'}
                                >
                                  {product.growth > 0 ? '+' : ''}{product.growth}%
                                </Typography>
                              </Box>
                            </TableCell>
                          </TableRow>
                        ))}
                    </TableBody>
                  </Table>
                </TableContainer>
                <TablePagination
                  rowsPerPageOptions={[5, 10, 25]}
                  component="div"
                  count={productPerformance.length}
                  rowsPerPage={rowsPerPage}
                  page={page}
                  onPageChange={(e, newPage) => setPage(newPage)}
                  onRowsPerPageChange={(e) => {
                    setRowsPerPage(parseInt(e.target.value, 10))
                    setPage(0)
                  }}
                />
              </Paper>
            </Grid>
          </Grid>
        )}

        {tabValue === 2 && (
          <Grid container spacing={3}>
            {/* Platform Performance */}
            <Grid item xs={12}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  플랫폼별 성과
                </Typography>
                <Grid container spacing={3}>
                  {platformData.map((platform, index) => (
                    <Grid item xs={12} sm={6} md={3} key={index}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="h6" color="primary" gutterBottom>
                            {platform.platform}
                          </Typography>
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="body2" color="text.secondary">
                              매출
                            </Typography>
                            <Typography variant="h5">
                              {formatCurrency(platform.revenue)}
                            </Typography>
                          </Box>
                          <Grid container spacing={2}>
                            <Grid item xs={6}>
                              <Typography variant="caption" color="text.secondary">
                                주문 수
                              </Typography>
                              <Typography variant="body2" fontWeight={500}>
                                {formatNumber(platform.orders)}건
                              </Typography>
                            </Grid>
                            <Grid item xs={6}>
                              <Typography variant="caption" color="text.secondary">
                                상품 수
                              </Typography>
                              <Typography variant="body2" fontWeight={500}>
                                {formatNumber(platform.products)}개
                              </Typography>
                            </Grid>
                            <Grid item xs={12}>
                              <Typography variant="caption" color="text.secondary">
                                전환율
                              </Typography>
                              <LinearProgress
                                variant="determinate"
                                value={platform.conversionRate * 10}
                                sx={{ mt: 1, mb: 0.5 }}
                              />
                              <Typography variant="body2" fontWeight={500}>
                                {platform.conversionRate}%
                              </Typography>
                            </Grid>
                          </Grid>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              </Paper>
            </Grid>
          </Grid>
        )}

        {tabValue === 3 && (
          <Grid container spacing={3}>
            {/* Customer Analysis */}
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  고객 유형별 분포
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={customerData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      fill="#8884d8"
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {customerData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <RechartsTooltip />
                  </PieChart>
                </ResponsiveContainer>
                <Box sx={{ mt: 2 }}>
                  {customerData.map((item, index) => (
                    <Box key={index} sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <Box
                        sx={{
                          width: 12,
                          height: 12,
                          borderRadius: '50%',
                          backgroundColor: COLORS[index % COLORS.length],
                          mr: 1,
                        }}
                      />
                      <Typography variant="body2">
                        {item.name}: {item.value}%
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </Paper>
            </Grid>

            {/* Customer Metrics */}
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  고객 지표
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="body2" color="text.secondary">
                          총 고객 수
                        </Typography>
                        <Typography variant="h4">1,250</Typography>
                        <Chip label="+8.5%" color="success" size="small" sx={{ mt: 1 }} />
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="body2" color="text.secondary">
                          재구매율
                        </Typography>
                        <Typography variant="h4">45%</Typography>
                        <Chip label="+2.3%" color="success" size="small" sx={{ mt: 1 }} />
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="body2" color="text.secondary">
                          고객 생애 가치
                        </Typography>
                        <Typography variant="h5">{formatCurrency(856000)}</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="body2" color="text.secondary">
                          평균 구매 주기
                        </Typography>
                        <Typography variant="h5">32일</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              </Paper>
            </Grid>
          </Grid>
        )}

        {tabValue === 4 && (
          <Grid container spacing={3}>
            {/* Comparison Analysis */}
            <Grid item xs={12}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  이번 달 vs 지난 달 비교
                </Typography>
                <ResponsiveContainer width="100%" height={400}>
                  <RadarChart data={radarData}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="category" />
                    <PolarRadiusAxis />
                    <Radar name="이번 달" dataKey="A" stroke="#8884d8" fill="#8884d8" fillOpacity={0.6} />
                    <Radar name="지난 달" dataKey="B" stroke="#82ca9d" fill="#82ca9d" fillOpacity={0.6} />
                    <Legend />
                  </RadarChart>
                </ResponsiveContainer>
              </Paper>
            </Grid>
          </Grid>
        )}
      </Box>
    </LocalizationProvider>
  )
}

export default Analytics