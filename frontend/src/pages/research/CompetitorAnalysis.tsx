import React, { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Paper,
  Chip,
  Button,
  TextField,
  InputAdornment,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Avatar,
  IconButton,
  Menu,
  MenuItem,
  Tooltip,
  Rating,
  LinearProgress,
  Alert,
  Tab,
  Tabs,
} from '@mui/material'
import {
  Search,
  MoreVert,
  TrendingUp,
  TrendingDown,
  Store,
  Inventory,
  LocalShipping,
  Speed,
  CompareArrows,
  Assessment,
  Warning,
} from '@mui/icons-material'
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, BarChart, Bar, Cell, Legend } from 'recharts'

// 샘플 데이터
const competitors = [
  {
    id: 1,
    name: 'A마켓',
    logo: 'https://via.placeholder.com/40',
    rating: 4.5,
    products: 1250,
    avgPrice: 45000,
    deliveryTime: '1-2일',
    marketShare: 25,
    priceChange: -5,
  },
  {
    id: 2,
    name: 'B스토어',
    logo: 'https://via.placeholder.com/40',
    rating: 4.3,
    products: 980,
    avgPrice: 52000,
    deliveryTime: '2-3일',
    marketShare: 18,
    priceChange: 3,
  },
  {
    id: 3,
    name: 'C샵',
    logo: 'https://via.placeholder.com/40',
    rating: 4.7,
    products: 1500,
    avgPrice: 38000,
    deliveryTime: '당일',
    marketShare: 32,
    priceChange: -2,
  },
]

const competitorMetrics = [
  { metric: '가격 경쟁력', A마켓: 85, B스토어: 72, C샵: 95 },
  { metric: '상품 다양성', A마켓: 78, B스토어: 65, C샵: 90 },
  { metric: '배송 속도', A마켓: 82, B스토어: 70, C샵: 98 },
  { metric: '고객 만족도', A마켓: 88, B스토어: 75, C샵: 92 },
  { metric: '브랜드 인지도', A마켓: 90, B스토어: 80, C샵: 85 },
]

const priceComparisonData = [
  { category: '전자제품', 우리: 45000, A마켓: 48000, B스토어: 52000, C샵: 43000 },
  { category: '패션', 우리: 32000, A마켓: 35000, B스토어: 38000, C샵: 30000 },
  { category: '뷰티', 우리: 25000, A마켓: 27000, B스토어: 29000, C샵: 24000 },
  { category: '스포츠', 우리: 55000, A마켓: 58000, B스토어: 62000, C샵: 53000 },
]

const marketShareTrend = [
  { month: '1월', 우리: 15, A마켓: 25, B스토어: 18, C샵: 30, 기타: 12 },
  { month: '2월', 우리: 16, A마켓: 24, B스토어: 19, C샵: 29, 기타: 12 },
  { month: '3월', 우리: 18, A마켓: 24, B스토어: 18, C샵: 31, 기타: 9 },
  { month: '4월', 우리: 19, A마켓: 23, B스토어: 18, C샵: 32, 기타: 8 },
  { month: '5월', 우리: 21, A마켓: 23, B스토어: 17, C샵: 32, 기타: 7 },
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
      id={`competitor-tabpanel-${index}`}
      aria-labelledby={`competitor-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  )
}

const CompetitorAnalysis: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('')
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [selectedCompetitor, setSelectedCompetitor] = useState<number | null>(null)
  const [tabValue, setTabValue] = useState(0)

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, id: number) => {
    setAnchorEl(event.currentTarget)
    setSelectedCompetitor(id)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
    setSelectedCompetitor(null)
  }

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
  }

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          경쟁사 분석
        </Typography>
        <Typography variant="body1" color="text.secondary">
          주요 경쟁사의 가격, 상품, 서비스를 비교 분석합니다
        </Typography>
      </Box>

      {/* 검색 바 */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <TextField
            fullWidth
            placeholder="경쟁사 검색..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
            }}
          />
        </CardContent>
      </Card>

      {/* 경쟁사 요약 알림 */}
      <Alert severity="info" sx={{ mb: 3 }}>
        <Typography variant="body2">
          현재 시장 점유율 21% (전월 대비 +2%p) | 주요 경쟁사 대비 평균 가격 -8% | 
          <strong> 가격 경쟁력 우위</strong> 유지 중
        </Typography>
      </Alert>

      {/* 탭 네비게이션 */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="경쟁사 개요" />
          <Tab label="가격 비교" />
          <Tab label="시장 점유율" />
          <Tab label="종합 분석" />
        </Tabs>
      </Box>

      {/* 경쟁사 개요 탭 */}
      <TabPanel value={tabValue} index={0}>
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>경쟁사</TableCell>
                <TableCell align="center">평점</TableCell>
                <TableCell align="center">상품 수</TableCell>
                <TableCell align="center">평균 가격</TableCell>
                <TableCell align="center">배송 기간</TableCell>
                <TableCell align="center">시장 점유율</TableCell>
                <TableCell align="center">가격 변동</TableCell>
                <TableCell align="center">액션</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {competitors.map((competitor) => (
                <TableRow key={competitor.id}>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Avatar src={competitor.logo} sx={{ mr: 2 }} />
                      <Typography variant="body2">{competitor.name}</Typography>
                    </Box>
                  </TableCell>
                  <TableCell align="center">
                    <Rating value={competitor.rating} readOnly size="small" />
                  </TableCell>
                  <TableCell align="center">{competitor.products.toLocaleString()}</TableCell>
                  <TableCell align="center">₩{competitor.avgPrice.toLocaleString()}</TableCell>
                  <TableCell align="center">
                    <Chip
                      label={competitor.deliveryTime}
                      size="small"
                      color={competitor.deliveryTime === '당일' ? 'success' : 'default'}
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Typography variant="body2">{competitor.marketShare}%</Typography>
                      <LinearProgress
                        variant="determinate"
                        value={competitor.marketShare}
                        sx={{ ml: 1, width: 50, height: 6, borderRadius: 3 }}
                      />
                    </Box>
                  </TableCell>
                  <TableCell align="center">
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      {competitor.priceChange > 0 ? (
                        <TrendingUp color="error" fontSize="small" />
                      ) : (
                        <TrendingDown color="success" fontSize="small" />
                      )}
                      <Typography
                        variant="body2"
                        color={competitor.priceChange > 0 ? 'error' : 'success.main'}
                      >
                        {Math.abs(competitor.priceChange)}%
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell align="center">
                    <IconButton
                      size="small"
                      onClick={(e) => handleMenuOpen(e, competitor.id)}
                    >
                      <MoreVert />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </TabPanel>

      {/* 가격 비교 탭 */}
      <TabPanel value={tabValue} index={1}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  카테고리별 가격 비교
                </Typography>
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart data={priceComparisonData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="category" />
                    <YAxis />
                    <RechartsTooltip />
                    <Legend />
                    <Bar dataKey="우리" fill="#8884d8" />
                    <Bar dataKey="A마켓" fill="#82ca9d" />
                    <Bar dataKey="B스토어" fill="#ffc658" />
                    <Bar dataKey="C샵" fill="#ff7c7c" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* 시장 점유율 탭 */}
      <TabPanel value={tabValue} index={2}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  시장 점유율 추이
                </Typography>
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart data={marketShareTrend}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis />
                    <RechartsTooltip />
                    <Legend />
                    <Line type="monotone" dataKey="우리" stroke="#8884d8" strokeWidth={3} />
                    <Line type="monotone" dataKey="A마켓" stroke="#82ca9d" />
                    <Line type="monotone" dataKey="B스토어" stroke="#ffc658" />
                    <Line type="monotone" dataKey="C샵" stroke="#ff7c7c" />
                    <Line type="monotone" dataKey="기타" stroke="#888888" strokeDasharray="5 5" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* 종합 분석 탭 */}
      <TabPanel value={tabValue} index={3}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  경쟁력 분석
                </Typography>
                <ResponsiveContainer width="100%" height={400}>
                  <RadarChart data={competitorMetrics}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="metric" />
                    <PolarRadiusAxis angle={90} domain={[0, 100]} />
                    <Radar name="A마켓" dataKey="A마켓" stroke="#82ca9d" fill="#82ca9d" fillOpacity={0.3} />
                    <Radar name="B스토어" dataKey="B스토어" stroke="#ffc658" fill="#ffc658" fillOpacity={0.3} />
                    <Radar name="C샵" dataKey="C샵" stroke="#ff7c7c" fill="#ff7c7c" fillOpacity={0.3} />
                    <Legend />
                  </RadarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  주요 인사이트
                </Typography>
                <Box sx={{ mt: 2 }}>
                  <Alert severity="success" sx={{ mb: 2 }}>
                    <Typography variant="subtitle2">강점</Typography>
                    <Typography variant="body2">
                      • 가격 경쟁력 우수 (경쟁사 대비 평균 -8%)
                      <br />
                      • 시장 점유율 지속 상승 중 (+6%p/5개월)
                    </Typography>
                  </Alert>
                  <Alert severity="warning" sx={{ mb: 2 }}>
                    <Typography variant="subtitle2">개선 필요</Typography>
                    <Typography variant="body2">
                      • 상품 다양성 부족 (C샵 대비 -35%)
                      <br />
                      • 배송 속도 개선 필요 (당일 배송 비율 15%)
                    </Typography>
                  </Alert>
                  <Alert severity="info">
                    <Typography variant="subtitle2">기회</Typography>
                    <Typography variant="body2">
                      • 프리미엄 상품 라인 확대
                      <br />
                      • 물류 인프라 투자로 경쟁 우위 확보
                    </Typography>
                  </Alert>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* 액션 메뉴 */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleMenuClose}>상세 분석</MenuItem>
        <MenuItem onClick={handleMenuClose}>가격 비교</MenuItem>
        <MenuItem onClick={handleMenuClose}>벤치마킹</MenuItem>
      </Menu>
    </Box>
  )
}

export default CompetitorAnalysis