import React from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Paper,
  Button,
  Chip,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Avatar,
  IconButton,
  Tooltip,
} from '@mui/material'
import {
  Psychology,
  TrendingUp,
  AttachMoney,
  Inventory,
  AutoAwesome,
  Lightbulb,
  Speed,
  CheckCircle,
  Warning,
  ArrowForward,
  Refresh,
  Timeline,
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { PieChart, Pie, Cell, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, RadialBarChart, RadialBar, Legend } from 'recharts'

// 샘플 데이터
const aiMetrics = [
  {
    title: 'AI 추천 적용률',
    value: 78,
    change: 12,
    status: 'success',
    icon: <Psychology />,
  },
  {
    title: '가격 최적화 성과',
    value: 85,
    change: 8,
    status: 'success',
    icon: <AttachMoney />,
  },
  {
    title: '수요 예측 정확도',
    value: 92,
    change: 5,
    status: 'success',
    icon: <Timeline />,
  },
  {
    title: '재고 효율성',
    value: 73,
    change: -2,
    status: 'warning',
    icon: <Inventory />,
  },
]

const aiInsights = [
  {
    id: 1,
    title: '무선 이어폰 가격 조정 추천',
    category: '가격 최적화',
    impact: 'high',
    description: '경쟁사 대비 5% 인하 시 판매량 25% 증가 예상',
    action: '가격 조정하기',
    route: '/ai-insights/price-optimization',
  },
  {
    id: 2,
    title: '캠핑용품 재고 확대 필요',
    category: '수요 예측',
    impact: 'medium',
    description: '다음 달 수요 35% 증가 예상, 재고 부족 위험',
    action: '재고 계획 보기',
    route: '/ai-insights/demand-forecast',
  },
  {
    id: 3,
    title: '신규 상품 추천',
    category: 'AI 추천',
    impact: 'high',
    description: '스마트워치 액세서리 라인 추가 시 매출 15% 증가 예상',
    action: '상품 추천 보기',
    route: '/ai-insights/recommendations',
  },
]

const performanceData = [
  { month: '1월', actual: 4200, predicted: 4000 },
  { month: '2월', actual: 4800, predicted: 4500 },
  { month: '3월', actual: 5200, predicted: 5100 },
  { month: '4월', actual: 5800, predicted: 5500 },
  { month: '5월', actual: 6500, predicted: 6200 },
  { month: '6월', actual: 7200, predicted: 7000 },
]

const aiModelStatus = [
  { name: '가격 최적화', value: 95, fill: '#0088FE' },
  { name: '수요 예측', value: 88, fill: '#00C49F' },
  { name: '상품 추천', value: 82, fill: '#FFBB28' },
  { name: '재고 관리', value: 75, fill: '#FF8042' },
]

const AIDashboard: React.FC = () => {
  const navigate = useNavigate()

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high':
        return 'error'
      case 'medium':
        return 'warning'
      case 'low':
        return 'info'
      default:
        return 'default'
    }
  }

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          AI 인사이트 대시보드
        </Typography>
        <Typography variant="body1" color="text.secondary">
          AI 기반 비즈니스 인사이트와 추천 사항을 확인하세요
        </Typography>
      </Box>

      {/* AI 성과 지표 */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {aiMetrics.map((metric) => (
          <Grid item xs={12} sm={6} md={3} key={metric.title}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Avatar
                    sx={{
                      bgcolor: metric.status === 'success' ? 'success.light' : 'warning.light',
                      color: metric.status === 'success' ? 'success.main' : 'warning.main',
                    }}
                  >
                    {metric.icon}
                  </Avatar>
                  <Box sx={{ ml: 2, flexGrow: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      {metric.title}
                    </Typography>
                    <Typography variant="h4">
                      {metric.value}%
                    </Typography>
                  </Box>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={metric.value}
                  color={metric.status as any}
                  sx={{ height: 8, borderRadius: 4 }}
                />
                <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                  <TrendingUp
                    fontSize="small"
                    color={metric.change > 0 ? 'success' : 'error'}
                  />
                  <Typography
                    variant="body2"
                    color={metric.change > 0 ? 'success.main' : 'error.main'}
                    sx={{ ml: 0.5 }}
                  >
                    {Math.abs(metric.change)}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                    전월 대비
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3}>
        {/* 주요 AI 인사이트 */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h6">
                  주요 AI 인사이트
                </Typography>
                <IconButton size="small">
                  <Refresh />
                </IconButton>
              </Box>
              <List>
                {aiInsights.map((insight, index) => (
                  <React.Fragment key={insight.id}>
                    <ListItem
                      sx={{
                        bgcolor: 'background.paper',
                        borderRadius: 2,
                        mb: index < aiInsights.length - 1 ? 2 : 0,
                        border: '1px solid',
                        borderColor: 'divider',
                      }}
                    >
                      <ListItemIcon>
                        <AutoAwesome color="primary" />
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="subtitle1">
                              {insight.title}
                            </Typography>
                            <Chip
                              label={insight.category}
                              size="small"
                              color="primary"
                              variant="outlined"
                            />
                            <Chip
                              label={insight.impact.toUpperCase()}
                              size="small"
                              color={getImpactColor(insight.impact) as any}
                            />
                          </Box>
                        }
                        secondary={insight.description}
                      />
                      <Button
                        variant="contained"
                        size="small"
                        endIcon={<ArrowForward />}
                        onClick={() => navigate(insight.route)}
                      >
                        {insight.action}
                      </Button>
                    </ListItem>
                  </React.Fragment>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* AI 모델 상태 */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                AI 모델 성능
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <RadialBarChart cx="50%" cy="50%" innerRadius="10%" outerRadius="90%" data={aiModelStatus}>
                  <RadialBar
                    background
                    dataKey="value"
                    cornerRadius={10}
                  />
                  <Legend
                    iconSize={10}
                    layout="vertical"
                    verticalAlign="middle"
                    align="right"
                  />
                  <RechartsTooltip />
                </RadialBarChart>
              </ResponsiveContainer>
              <Divider sx={{ my: 2 }} />
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography variant="body2" color="text.secondary">
                  전체 정확도
                </Typography>
                <Typography variant="h6" color="primary">
                  87.5%
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* 예측 vs 실제 성과 */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                AI 예측 vs 실제 성과
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={performanceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <RechartsTooltip />
                  <Area
                    type="monotone"
                    dataKey="predicted"
                    stackId="1"
                    stroke="#8884d8"
                    fill="#8884d8"
                    fillOpacity={0.6}
                    name="AI 예측"
                  />
                  <Area
                    type="monotone"
                    dataKey="actual"
                    stackId="2"
                    stroke="#82ca9d"
                    fill="#82ca9d"
                    fillOpacity={0.6}
                    name="실제 성과"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* 빠른 액션 */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3, bgcolor: 'primary.main', color: 'primary.contrastText' }}>
            <Grid container spacing={3} alignItems="center">
              <Grid item xs={12} md={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Lightbulb sx={{ fontSize: 48 }} />
                  <Box>
                    <Typography variant="h6">
                      AI가 발견한 새로운 기회
                    </Typography>
                    <Typography variant="body2">
                      현재 3개의 새로운 비즈니스 기회가 발견되었습니다
                    </Typography>
                  </Box>
                </Box>
              </Grid>
              <Grid item xs={12} md={6} sx={{ textAlign: { md: 'right' } }}>
                <Button
                  variant="contained"
                  size="large"
                  sx={{
                    bgcolor: 'white',
                    color: 'primary.main',
                    '&:hover': {
                      bgcolor: 'grey.100',
                    },
                  }}
                  endIcon={<ArrowForward />}
                >
                  기회 탐색하기
                </Button>
              </Grid>
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}

export default AIDashboard