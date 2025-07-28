import React, { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
  TextField,
  InputAdornment,
  Slider,
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Avatar,
  IconButton,
  Tooltip,
  Switch,
  FormControlLabel,
  Alert,
  LinearProgress,
  Divider,
} from '@mui/material'
import {
  AttachMoney,
  TrendingUp,
  TrendingDown,
  Psychology,
  Calculate,
  CompareArrows,
  Warning,
  CheckCircle,
  Refresh,
  Download,
  AutoFixHigh,
  Timeline,
} from '@mui/icons-material'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Area, AreaChart, Scatter, ScatterChart, ZAxis, Cell } from 'recharts'

// 샘플 데이터
const priceOptimizationData = [
  {
    id: 1,
    product: '무선 이어폰 프로',
    category: '전자제품',
    currentPrice: 89000,
    suggestedPrice: 84500,
    priceChange: -5.1,
    expectedSalesIncrease: 25,
    profitImpact: 8,
    competitorAvg: 92000,
    elasticity: 1.8,
    confidence: 92,
    status: 'recommended',
  },
  {
    id: 2,
    product: '캠핑 체어 프리미엄',
    category: '아웃도어',
    currentPrice: 45000,
    suggestedPrice: 48000,
    priceChange: 6.7,
    expectedSalesIncrease: -5,
    profitImpact: 12,
    competitorAvg: 52000,
    elasticity: 0.8,
    confidence: 85,
    status: 'review',
  },
  {
    id: 3,
    product: '요가매트 에코',
    category: '스포츠',
    currentPrice: 35000,
    suggestedPrice: 32000,
    priceChange: -8.6,
    expectedSalesIncrease: 35,
    profitImpact: 15,
    competitorAvg: 38000,
    elasticity: 2.2,
    confidence: 88,
    status: 'recommended',
  },
]

const priceElasticityData = [
  { price: 70, demand: 100 },
  { price: 75, demand: 92 },
  { price: 80, demand: 85 },
  { price: 85, demand: 78 },
  { price: 90, demand: 70 },
  { price: 95, demand: 60 },
  { price: 100, demand: 48 },
]

const revenueSimulation = [
  { price: 75000, revenue: 6900000, profit: 2100000 },
  { price: 80000, revenue: 6800000, profit: 2200000 },
  { price: 85000, revenue: 6630000, profit: 2250000 },
  { price: 90000, revenue: 6300000, profit: 2100000 },
  { price: 95000, revenue: 5700000, profit: 1900000 },
]

const competitorPrices = [
  { competitor: 'A마켓', price: 92000, marketShare: 25 },
  { competitor: 'B스토어', price: 88000, marketShare: 18 },
  { competitor: 'C샵', price: 95000, marketShare: 32 },
  { competitor: '우리', price: 89000, marketShare: 15 },
]

const PriceOptimization: React.FC = () => {
  const [autoOptimize, setAutoOptimize] = useState(false)
  const [priceAdjustment, setPriceAdjustment] = useState(0)
  const [selectedProduct, setSelectedProduct] = useState<number | null>(null)

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'recommended':
        return 'success'
      case 'review':
        return 'warning'
      case 'hold':
        return 'info'
      default:
        return 'default'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'recommended':
        return '추천'
      case 'review':
        return '검토 필요'
      case 'hold':
        return '유지'
      default:
        return status
    }
  }

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          AI 가격 최적화
        </Typography>
        <Typography variant="body1" color="text.secondary">
          AI가 분석한 최적 가격 전략으로 수익을 극대화하세요
        </Typography>
      </Box>

      {/* 자동 최적화 설정 */}
      <Alert
        severity="info"
        sx={{ mb: 3 }}
        action={
          <FormControlLabel
            control={
              <Switch
                checked={autoOptimize}
                onChange={(e) => setAutoOptimize(e.target.checked)}
                color="primary"
              />
            }
            label="자동 최적화"
          />
        }
      >
        AI가 실시간으로 시장 상황을 분석하여 최적 가격을 제안합니다.
        현재 <strong>3개 상품</strong>에 대한 가격 조정을 추천합니다.
      </Alert>

      {/* 가격 최적화 테이블 */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">가격 최적화 추천</Typography>
            <Box>
              <IconButton size="small">
                <Refresh />
              </IconButton>
              <IconButton size="small">
                <Download />
              </IconButton>
            </Box>
          </Box>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>상품명</TableCell>
                  <TableCell align="center">현재 가격</TableCell>
                  <TableCell align="center">추천 가격</TableCell>
                  <TableCell align="center">가격 변동</TableCell>
                  <TableCell align="center">예상 판매 증가</TableCell>
                  <TableCell align="center">수익 영향</TableCell>
                  <TableCell align="center">AI 신뢰도</TableCell>
                  <TableCell align="center">상태</TableCell>
                  <TableCell align="center">액션</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {priceOptimizationData.map((item) => (
                  <TableRow
                    key={item.id}
                    sx={{ cursor: 'pointer' }}
                    onClick={() => setSelectedProduct(item.id)}
                    selected={selectedProduct === item.id}
                  >
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Avatar sx={{ mr: 2, bgcolor: 'primary.light' }}>
                          <AttachMoney />
                        </Avatar>
                        <Box>
                          <Typography variant="body2">{item.product}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {item.category}
                          </Typography>
                        </Box>
                      </Box>
                    </TableCell>
                    <TableCell align="center">
                      ₩{item.currentPrice.toLocaleString()}
                    </TableCell>
                    <TableCell align="center">
                      <Typography color="primary" fontWeight="bold">
                        ₩{item.suggestedPrice.toLocaleString()}
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        {item.priceChange > 0 ? (
                          <TrendingUp color="error" fontSize="small" />
                        ) : (
                          <TrendingDown color="success" fontSize="small" />
                        )}
                        <Typography
                          variant="body2"
                          color={item.priceChange > 0 ? 'error' : 'success.main'}
                          sx={{ ml: 0.5 }}
                        >
                          {Math.abs(item.priceChange)}%
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell align="center">
                      <Typography
                        variant="body2"
                        color={item.expectedSalesIncrease > 0 ? 'success.main' : 'error.main'}
                      >
                        {item.expectedSalesIncrease > 0 ? '+' : ''}{item.expectedSalesIncrease}%
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <Typography
                        variant="body2"
                        color="primary"
                        fontWeight="bold"
                      >
                        +{item.profitImpact}%
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <LinearProgress
                          variant="determinate"
                          value={item.confidence}
                          sx={{ width: 60, mr: 1 }}
                        />
                        <Typography variant="body2">{item.confidence}%</Typography>
                      </Box>
                    </TableCell>
                    <TableCell align="center">
                      <Chip
                        label={getStatusText(item.status)}
                        size="small"
                        color={getStatusColor(item.status) as any}
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Button
                        size="small"
                        variant="contained"
                        onClick={(e) => {
                          e.stopPropagation()
                          // 가격 적용 로직
                        }}
                      >
                        적용
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <Grid container spacing={3}>
        {/* 가격 탄력성 분석 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                가격 탄력성 분석
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="price" name="가격" unit="원" />
                  <YAxis dataKey="demand" name="수요" />
                  <ZAxis range={[100]} />
                  <RechartsTooltip cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter name="가격-수요" data={priceElasticityData} fill="#8884d8">
                    {priceElasticityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill="#8884d8" />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
              <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  <Psychology fontSize="small" sx={{ verticalAlign: 'middle', mr: 1 }} />
                  가격 탄력성: 1.8 (탄력적) - 가격 인하 시 수요 증가 효과가 큼
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* 수익 시뮬레이션 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                수익 시뮬레이션
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={revenueSimulation}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="price" />
                  <YAxis />
                  <RechartsTooltip />
                  <Area
                    type="monotone"
                    dataKey="revenue"
                    stackId="1"
                    stroke="#8884d8"
                    fill="#8884d8"
                    fillOpacity={0.6}
                    name="매출"
                  />
                  <Area
                    type="monotone"
                    dataKey="profit"
                    stackId="2"
                    stroke="#82ca9d"
                    fill="#82ca9d"
                    fillOpacity={0.6}
                    name="수익"
                  />
                </AreaChart>
              </ResponsiveContainer>
              <Box sx={{ mt: 2 }}>
                <Chip
                  icon={<AutoFixHigh />}
                  label="최적 가격: ₩85,000 (수익 극대화)"
                  color="primary"
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* 경쟁사 가격 비교 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                경쟁사 가격 비교
              </Typography>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={competitorPrices}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="competitor" />
                  <YAxis />
                  <RechartsTooltip />
                  <Bar dataKey="price" fill="#8884d8">
                    {competitorPrices.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.competitor === '우리' ? '#ff7300' : '#8884d8'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* 가격 조정 시뮬레이터 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                가격 조정 시뮬레이터
              </Typography>
              <Box sx={{ mt: 3 }}>
                <Typography gutterBottom>가격 조정률: {priceAdjustment}%</Typography>
                <Slider
                  value={priceAdjustment}
                  onChange={(e, newValue) => setPriceAdjustment(newValue as number)}
                  min={-20}
                  max={20}
                  marks
                  valueLabelDisplay="auto"
                />
                <Grid container spacing={2} sx={{ mt: 2 }}>
                  <Grid item xs={6}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'grey.50' }}>
                      <Typography variant="caption" color="text.secondary">
                        예상 판매량 변화
                      </Typography>
                      <Typography variant="h6" color={priceAdjustment < 0 ? 'success.main' : 'error.main'}>
                        {priceAdjustment < 0 ? '+' : ''}{Math.round(-priceAdjustment * 1.8)}%
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'grey.50' }}>
                      <Typography variant="caption" color="text.secondary">
                        예상 수익 변화
                      </Typography>
                      <Typography variant="h6" color="primary">
                        {priceAdjustment > 5 ? '+' : ''}{Math.round(priceAdjustment * 0.7)}%
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* AI 인사이트 */}
      <Paper sx={{ mt: 3, p: 3, bgcolor: 'primary.main', color: 'primary.contrastText' }}>
        <Grid container spacing={3} alignItems="center">
          <Grid item xs={12} md={8}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Psychology sx={{ fontSize: 48 }} />
              <Box>
                <Typography variant="h6">
                  AI 가격 최적화 인사이트
                </Typography>
                <Typography variant="body2">
                  현재 시장 상황과 경쟁사 동향을 고려할 때, 주력 상품의 5-8% 가격 인하를 통해
                  시장 점유율을 확대하고 전체 수익을 15% 증가시킬 수 있습니다.
                </Typography>
              </Box>
            </Box>
          </Grid>
          <Grid item xs={12} md={4} sx={{ textAlign: { md: 'right' } }}>
            <Button
              variant="contained"
              sx={{
                bgcolor: 'white',
                color: 'primary.main',
                '&:hover': {
                  bgcolor: 'grey.100',
                },
              }}
              startIcon={<Calculate />}
            >
              전체 최적화 실행
            </Button>
          </Grid>
        </Grid>
      </Paper>
    </Box>
  )
}

export default PriceOptimization