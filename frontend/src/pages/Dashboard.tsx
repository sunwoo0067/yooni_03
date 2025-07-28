import React, { useState, useCallback, useEffect } from 'react'
import {
  Box,
  IconButton,
  LinearProgress,
  Chip,
  Button,
  Menu,
  MenuItem,
  Typography,
  Paper,
  Fab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Switch,
  FormControlLabel,
  useTheme,
  alpha,
} from '@mui/material'
import {
  TrendingUp,
  TrendingDown,
  ShoppingCart,
  Inventory,
  People,
  AttachMoney,
  MoreVert,
  Refresh,
  Download,
  Add,
  DragIndicator,
  Settings,
  Fullscreen,
  FullscreenExit,
  Notifications,
  Timeline,
  Speed,
  AutoGraph,
  Close,
} from '@mui/icons-material'
import {
  LineChart, Line,
  BarChart, Bar,
  PieChart, Pie, Cell,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend as RechartsLegend,
  ResponsiveContainer
} from 'recharts'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { analyticsAPI } from '@services/api'
import { Responsive, WidthProvider } from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'
import { Card, StatCard } from '@components/ui/Card'
import SearchBar from '@components/ui/SearchBar'
import QuickActions, { QuickAction } from '@components/ui/QuickActions'

// react-grid-layout 설정
const ResponsiveGridLayout = WidthProvider(Responsive)

// Color palette for charts
const COLORS = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']

// 위젯 타입 정의
type WidgetType = 'stats' | 'revenue' | 'orders' | 'platform' | 'activity' | 'products' | 'performance' | 'notifications'

interface Widget {
  id: string
  type: WidgetType
  title: string
  refreshInterval?: number
}

// 사용 가능한 위젯 목록
const availableWidgets: Widget[] = [
  { id: 'stats', type: 'stats', title: '통계 요약' },
  { id: 'revenue', type: 'revenue', title: '매출 추이', refreshInterval: 60000 },
  { id: 'orders', type: 'orders', title: '주문 현황', refreshInterval: 30000 },
  { id: 'platform', type: 'platform', title: '플랫폼별 매출' },
  { id: 'activity', type: 'activity', title: '최근 활동', refreshInterval: 10000 },
  { id: 'products', type: 'products', title: '인기 상품' },
  { id: 'performance', type: 'performance', title: '성과 지표' },
  { id: 'notifications', type: 'notifications', title: '알림', refreshInterval: 5000 },
]

// 기본 레이아웃 설정
const defaultLayouts = {
  lg: [
    { i: 'stats', x: 0, y: 0, w: 12, h: 2, minW: 8, minH: 2 },
    { i: 'revenue', x: 0, y: 2, w: 8, h: 3, minW: 4, minH: 2 },
    { i: 'platform', x: 8, y: 2, w: 4, h: 3, minW: 3, minH: 2 },
    { i: 'orders', x: 0, y: 5, w: 6, h: 3, minW: 4, minH: 2 },
    { i: 'activity', x: 6, y: 5, w: 6, h: 3, minW: 4, minH: 2 },
    { i: 'products', x: 0, y: 8, w: 6, h: 3, minW: 4, minH: 2 },
    { i: 'performance', x: 6, y: 8, w: 6, h: 3, minW: 4, minH: 2 },
  ],
  md: [
    { i: 'stats', x: 0, y: 0, w: 10, h: 2 },
    { i: 'revenue', x: 0, y: 2, w: 6, h: 3 },
    { i: 'platform', x: 6, y: 2, w: 4, h: 3 },
    { i: 'orders', x: 0, y: 5, w: 5, h: 3 },
    { i: 'activity', x: 5, y: 5, w: 5, h: 3 },
    { i: 'products', x: 0, y: 8, w: 5, h: 3 },
    { i: 'performance', x: 5, y: 8, w: 5, h: 3 },
  ],
  sm: [
    { i: 'stats', x: 0, y: 0, w: 6, h: 2 },
    { i: 'revenue', x: 0, y: 2, w: 6, h: 3 },
    { i: 'platform', x: 0, y: 5, w: 6, h: 3 },
    { i: 'orders', x: 0, y: 8, w: 6, h: 3 },
    { i: 'activity', x: 0, y: 11, w: 6, h: 3 },
    { i: 'products', x: 0, y: 14, w: 6, h: 3 },
    { i: 'performance', x: 0, y: 17, w: 6, h: 3 },
  ],
}

// Dashboard Component
export default function Dashboard() {
  const theme = useTheme()
  const [layouts, setLayouts] = useState(defaultLayouts)
  const [activeWidgets, setActiveWidgets] = useState<string[]>(['stats', 'revenue', 'orders', 'platform', 'activity', 'products'])
  const [isEditMode, setIsEditMode] = useState(false)
  const [addWidgetOpen, setAddWidgetOpen] = useState(false)
  const [fullscreenWidget, setFullscreenWidget] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const { data: dashboardData, isLoading, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => {
      try {
        // 실제 API에서 대시보드 통계 가져오기
        const response = await analyticsAPI.getDashboard()
        const stats = response.data
        
        // 실제 데이터를 차트 형식으로 변환
        return {
          stats: {
            totalRevenue: (stats.orders?.revenue || 0),
            totalOrders: (stats.orders?.total || 0),
            totalProducts: (stats.products?.total || 0),
            totalCustomers: 0, // 아직 고객 데이터 없음
          },
          revenueChart: {
            labels: ['1월', '2월', '3월', '4월', '5월', '6월'],
            data: [3200000, 4100000, 3800000, 5200000, 4900000, stats.orders?.revenue || 0],
          },
          orderChart: {
            labels: ['월', '화', '수', '목', '금', '토', '일'],
            data: [45, 52, 38, 65, 59, 82, stats.orders?.total || 0],
          },
          platformSales: {
            labels: ['연결된 플랫폼', '미연결 플랫폼'],
            data: [stats.platforms?.connected || 0, stats.platforms?.disconnected || 0],
          },
        }
      } catch (error) {
        console.warn('API 실패, 기본 데이터 사용:', error)
        // API 실패시 fallback 데이터
        return {
          stats: {
            totalRevenue: 0,
            totalOrders: 0,
            totalProducts: 0,
            totalCustomers: 0,
          },
          revenueChart: {
            labels: ['1월', '2월', '3월', '4월', '5월', '6월'],
            data: [0, 0, 0, 0, 0, 0],
          },
          orderChart: {
            labels: ['월', '화', '수', '목', '금', '토', '일'],
            data: [0, 0, 0, 0, 0, 0, 0],
          },
          platformSales: {
            labels: ['연결된 플랫폼', '미연결 플랫폼'],
            data: [0, 0],
          },
        }
      }
    },
    refetchInterval: autoRefresh ? 30000 : false, // 30초마다 자동 업데이트
  })

  // 위젯별 실시간 업데이트
  useEffect(() => {
    if (!autoRefresh) return

    const intervals: NodeJS.Timeout[] = []
    
    activeWidgets.forEach((widgetId) => {
      const widget = availableWidgets.find(w => w.id === widgetId)
      if (widget?.refreshInterval) {
        const interval = setInterval(() => {
          // 개별 위젯 업데이트 로직
          console.log(`Updating widget: ${widgetId}`)
        }, widget.refreshInterval)
        intervals.push(interval)
      }
    })

    return () => {
      intervals.forEach(clearInterval)
    }
  }, [activeWidgets, autoRefresh])

  const handleRefresh = () => {
    refetch()
    toast.success('대시보드가 업데이트되었습니다.')
  }

  const handleExport = () => {
    toast.success('리포트 다운로드를 시작합니다.')
  }

  const handleLayoutChange = (layout: any, layouts: any) => {
    setLayouts(layouts)
    // 레이아웃을 localStorage에 저장
    localStorage.setItem('dashboardLayouts', JSON.stringify(layouts))
  }

  const handleAddWidget = (widgetId: string) => {
    if (!activeWidgets.includes(widgetId)) {
      setActiveWidgets([...activeWidgets, widgetId])
    }
    setAddWidgetOpen(false)
  }

  const handleRemoveWidget = (widgetId: string) => {
    setActiveWidgets(activeWidgets.filter(id => id !== widgetId))
  }

  const toggleFullscreen = (widgetId: string) => {
    setFullscreenWidget(fullscreenWidget === widgetId ? null : widgetId)
  }

  // Chart data transformations
  const revenueChartData = dashboardData?.revenueChart?.labels?.map((label: string, index: number) => ({
    name: label,
    매출: dashboardData?.revenueChart?.data[index] || 0
  })) || []

  const orderChartData = dashboardData?.orderChart?.labels?.map((label: string, index: number) => ({
    name: label,
    주문수: dashboardData?.orderChart?.data[index] || 0
  })) || []

  const platformChartData = dashboardData?.platformSales?.labels?.map((label: string, index: number) => ({
    name: label,
    value: dashboardData?.platformSales?.data[index] || 0
  })) || []

  // 빠른 액션 정의
  const quickActions: QuickAction[] = [
    {
      id: 'add-widget',
      icon: <Add />,
      name: '위젯 추가',
      action: () => setAddWidgetOpen(true),
      color: 'primary',
    },
    {
      id: 'edit-mode',
      icon: <Settings />,
      name: isEditMode ? '편집 종료' : '대시보드 편집',
      action: () => setIsEditMode(!isEditMode),
      color: isEditMode ? 'secondary' : 'primary',
    },
    {
      id: 'auto-refresh',
      icon: <Refresh />,
      name: autoRefresh ? '자동 업데이트 끄기' : '자동 업데이트 켜기',
      action: () => setAutoRefresh(!autoRefresh),
      color: autoRefresh ? 'success' : 'warning',
    },
    {
      id: 'export',
      icon: <Download />,
      name: '리포트 다운로드',
      action: handleExport,
    },
  ]

  // 위젯 렌더링 함수
  const renderWidget = (widgetId: string) => {
    const isFullscreen = fullscreenWidget === widgetId
    
    switch (widgetId) {
      case 'stats':
        return (
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 2, height: '100%' }}>
            <StatCard
              title="총 매출"
              value={`₩${dashboardData?.stats.totalRevenue.toLocaleString() || 0}`}
              change={12.5}
              icon={<AttachMoney />}
              color="primary"
            />
            <StatCard
              title="총 주문"
              value={dashboardData?.stats.totalOrders || 0}
              change={8.2}
              icon={<ShoppingCart />}
              color="secondary"
            />
            <StatCard
              title="상품 수"
              value={dashboardData?.stats.totalProducts || 0}
              change={-2.4}
              icon={<Inventory />}
              color="warning"
            />
            <StatCard
              title="고객 수"
              value={dashboardData?.stats.totalCustomers || 0}
              change={15.3}
              icon={<People />}
              color="success"
            />
          </Box>
        )
        
      case 'revenue':
        return (
          <Box sx={{ height: '100%', p: 2 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={revenueChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <RechartsTooltip />
                <RechartsLegend />
                <Line 
                  type="monotone" 
                  dataKey="매출" 
                  stroke={theme.palette.primary.main}
                  fill={theme.palette.primary.main}
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </Box>
        )
        
      case 'orders':
        return (
          <Box sx={{ height: '100%', p: 2 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={orderChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <RechartsTooltip />
                <RechartsLegend />
                <Bar 
                  dataKey="주문수" 
                  fill={theme.palette.secondary.main}
                />
              </BarChart>
            </ResponsiveContainer>
          </Box>
        )
        
      case 'platform':
        return (
          <Box sx={{ height: '100%', p: 2 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={platformChartData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => entry.name}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {platformChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <RechartsTooltip />
              </PieChart>
            </ResponsiveContainer>
          </Box>
        )
        
      case 'activity':
        return (
          <Box sx={{ p: 2, height: '100%', overflow: 'auto' }}>
            {[
              { time: '5분 전', event: '새 주문 접수', detail: '무선 이어폰 외 2건', type: 'order' },
              { time: '15분 전', event: '상품 품절', detail: '블루투스 스피커', type: 'warning' },
              { time: '1시간 전', event: '배송 완료', detail: '주문번호 #12345', type: 'success' },
              { time: '2시간 전', event: '신규 고객 가입', detail: 'user@example.com', type: 'info' },
            ].map((activity, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Box display="flex" justifyContent="space-between" py={1.5} borderBottom={1} borderColor="divider">
                  <Box>
                    <Typography variant="body2" fontWeight="medium">
                      {activity.event}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {activity.detail}
                    </Typography>
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {activity.time}
                  </Typography>
                </Box>
              </motion.div>
            ))}
          </Box>
        )
        
      case 'products':
        return (
          <Box sx={{ p: 2, height: '100%', overflow: 'auto' }}>
            {[
              { rank: 1, name: '무선 이어폰 Pro', sales: 234, revenue: '₩11,700,000' },
              { rank: 2, name: '스마트워치 Series 5', sales: 189, revenue: '₩9,450,000' },
              { rank: 3, name: '블루투스 스피커', sales: 156, revenue: '₩4,680,000' },
              { rank: 4, name: '무선 충전기', sales: 134, revenue: '₩2,680,000' },
              { rank: 5, name: 'USB-C 허브', sales: 98, revenue: '₩1,960,000' },
            ].map((product) => (
              <Box key={product.rank} display="flex" alignItems="center" justifyContent="space-between" py={1.5} borderBottom={1} borderColor="divider">
                <Box display="flex" alignItems="center">
                  <Chip label={product.rank} size="small" sx={{ mr: 2, minWidth: 32 }} />
                  <Box>
                    <Typography variant="body2" fontWeight="medium">
                      {product.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      판매 {product.sales}개
                    </Typography>
                  </Box>
                </Box>
                <Typography variant="body2" fontWeight="bold" color="primary">
                  {product.revenue}
                </Typography>
              </Box>
            ))}
          </Box>
        )
        
      case 'performance':
        const performanceData = [
          { subject: '판매율', 현재: 85, 목표: 90, fullMark: 100 },
          { subject: '재고회전율', 현재: 72, 목표: 80, fullMark: 100 },
          { subject: '고객만족도', 현재: 90, 목표: 95, fullMark: 100 },
          { subject: '배송정확도', 현재: 88, 목표: 95, fullMark: 100 },
          { subject: '품질지수', 현재: 94, 목표: 95, fullMark: 100 },
        ]
        return (
          <Box sx={{ height: '100%', p: 2 }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={performanceData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="subject" />
                <PolarRadiusAxis angle={90} domain={[0, 100]} />
                <Radar 
                  name="현재" 
                  dataKey="현재" 
                  stroke={theme.palette.primary.main} 
                  fill={theme.palette.primary.main} 
                  fillOpacity={0.3}
                />
                <Radar 
                  name="목표" 
                  dataKey="목표" 
                  stroke={theme.palette.secondary.main} 
                  fill={theme.palette.secondary.main} 
                  fillOpacity={0.3}
                />
                <RechartsLegend />
              </RadarChart>
            </ResponsiveContainer>
          </Box>
        )
        
      case 'notifications':
        return (
          <Box sx={{ p: 2, height: '100%', overflow: 'auto' }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Chip 
                icon={<Notifications />} 
                label="재고 부족 경고: 5개 상품" 
                color="warning" 
                size="small" 
                onClick={() => {}}
              />
              <Chip 
                icon={<Speed />} 
                label="판매 속도 감소: -15%" 
                color="error" 
                size="small" 
                onClick={() => {}}
              />
              <Chip 
                icon={<TrendingUp />} 
                label="매출 목표 달성: 102%" 
                color="success" 
                size="small" 
                onClick={() => {}}
              />
              <Chip 
                icon={<Timeline />} 
                label="AI 분석 완료" 
                color="info" 
                size="small" 
                onClick={() => {}}
              />
            </Box>
          </Box>
        )
        
      default:
        return null
    }
  }

  if (isLoading) {
    return <LinearProgress />
  }

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Paper sx={{ p: 2, mb: 2, borderRadius: 0 }} elevation={0}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box>
              <Typography variant="h4" fontWeight="bold">
                대시보드
              </Typography>
              <Typography variant="body2" color="text.secondary">
                오늘의 비즈니스 현황을 한눈에 확인하세요
              </Typography>
            </Box>
            {autoRefresh && (
              <Chip
                icon={<AutoGraph />}
                label="실시간 업데이트 중"
                color="success"
                size="small"
                variant="outlined"
              />
            )}
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <SearchBar
              placeholder="대시보드 검색..."
              suggestions={[
                { id: '1', title: '매출 통계', type: 'product' },
                { id: '2', title: '주문 현황', type: 'order' },
                { id: '3', title: '고객 분석', type: 'customer' },
              ]}
            />
            <FormControlLabel
              control={
                <Switch
                  checked={isEditMode}
                  onChange={(e) => setIsEditMode(e.target.checked)}
                  color="primary"
                />
              }
              label="편집 모드"
            />
            <Button
              startIcon={<Refresh />}
              onClick={handleRefresh}
              disabled={autoRefresh}
            >
              새로고침
            </Button>
            <Button
              variant="contained"
              startIcon={<Download />}
              onClick={handleExport}
            >
              리포트
            </Button>
          </Box>
        </Box>
      </Paper>

      {/* 위젯 그리드 */}
      <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
        <ResponsiveGridLayout
          className="layout"
          layouts={layouts}
          onLayoutChange={handleLayoutChange}
          breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
          cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
          rowHeight={100}
          isDraggable={isEditMode}
          isResizable={isEditMode}
          containerPadding={[0, 0]}
          margin={[16, 16]}
        >
          {activeWidgets.map((widgetId) => {
            const widget = availableWidgets.find(w => w.id === widgetId)
            if (!widget) return null

            return (
              <Card
                key={widgetId}
                title={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {isEditMode && (
                      <DragIndicator sx={{ cursor: 'move', color: 'text.secondary' }} />
                    )}
                    <Typography variant="h6">{widget.title}</Typography>
                    {widget.refreshInterval && autoRefresh && (
                      <Chip
                        icon={<Refresh />}
                        label="자동"
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                    )}
                  </Box>
                }
                onMenuClick={(e) => {
                  const menu = document.createElement('div')
                  // 메뉴 항목 처리
                }}
                actions={
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <IconButton
                      size="small"
                      onClick={() => toggleFullscreen(widgetId)}
                    >
                      {fullscreenWidget === widgetId ? <FullscreenExit /> : <Fullscreen />}
                    </IconButton>
                    {isEditMode && (
                      <IconButton
                        size="small"
                        onClick={() => handleRemoveWidget(widgetId)}
                        color="error"
                      >
                        <Close />
                      </IconButton>
                    )}
                  </Box>
                }
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  '& .MuiCardContent-root': {
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden',
                  },
                }}
              >
                <AnimatePresence mode="wait">
                  <motion.div
                    key={widgetId}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    style={{ height: '100%' }}
                  >
                    {renderWidget(widgetId)}
                  </motion.div>
                </AnimatePresence>
              </Card>
            )
          })}
        </ResponsiveGridLayout>
      </Box>

      {/* 위젯 추가 다이얼로그 */}
      <Dialog open={addWidgetOpen} onClose={() => setAddWidgetOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>위젯 추가</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 2, mt: 2 }}>
            {availableWidgets
              .filter(w => !activeWidgets.includes(w.id))
              .map((widget) => (
                <Paper
                  key={widget.id}
                  sx={{
                    p: 2,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: 4,
                    },
                  }}
                  onClick={() => handleAddWidget(widget.id)}
                >
                  <Typography variant="subtitle1" fontWeight="bold">
                    {widget.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {widget.refreshInterval ? `${widget.refreshInterval / 1000}초마다 업데이트` : '정적 데이터'}
                  </Typography>
                </Paper>
              ))}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddWidgetOpen(false)}>닫기</Button>
        </DialogActions>
      </Dialog>

      {/* 빠른 작업 버튼 */}
      <QuickActions
        actions={quickActions}
        position={{ vertical: 'bottom', horizontal: 'right' }}
        variant="menu"
      />

      {/* 전체 화면 뷰 */}
      <Dialog
        open={!!fullscreenWidget}
        onClose={() => setFullscreenWidget(null)}
        fullScreen
      >
        {fullscreenWidget && (
          <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h5">
                {availableWidgets.find(w => w.id === fullscreenWidget)?.title}
              </Typography>
              <IconButton onClick={() => setFullscreenWidget(null)}>
                <Close />
              </IconButton>
            </Box>
            <Box sx={{ flex: 1, overflow: 'auto' }}>
              {renderWidget(fullscreenWidget)}
            </Box>
          </Box>
        )}
      </Dialog>
    </Box>
  )
}