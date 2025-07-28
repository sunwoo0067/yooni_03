import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
  Tabs,
  Tab,
  Paper,
  Chip,
  LinearProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Rating,
} from '@mui/material'
import {
  TrendingUp as TrendingUpIcon,
  AttachMoney as MoneyIcon,
  Psychology as AIIcon,
  Category as CategoryIcon,
  Recommend as RecommendIcon,
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
    <div hidden={value !== index} {...other}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  )
}

export default function AISourcing() {
  const [tabValue, setTabValue] = useState(0)
  const [recommendationType, setRecommendationType] = useState<'balanced' | 'trend' | 'profit'>('balanced')

  // AI 대시보드 데이터
  const { data: dashboardData, isLoading: dashboardLoading } = useQuery({
    queryKey: ['ai-dashboard'],
    queryFn: async () => {
      const response = await api.get('/ai-sourcing/dashboard')
      return response.data
    },
  })

  // 상품 추천
  const { data: recommendationsData, isLoading: recLoading } = useQuery({
    queryKey: ['ai-recommendations', recommendationType],
    queryFn: async () => {
      const response = await api.get('/ai-sourcing/recommendations', {
        params: { recommendation_type: recommendationType, limit: 20 },
      })
      return response.data
    },
  })

  // 카테고리 트렌드
  const { data: categoryTrends } = useQuery({
    queryKey: ['category-trends'],
    queryFn: async () => {
      const response = await api.get('/ai-sourcing/trends/categories')
      return response.data
    },
  })

  // 카테고리 기회
  const { data: opportunities } = useQuery({
    queryKey: ['category-opportunities'],
    queryFn: async () => {
      const response = await api.get('/ai-sourcing/opportunities')
      return response.data
    },
  })

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
  }

  const getProfitScoreColor = (score: number) => {
    if (score >= 80) return 'success'
    if (score >= 60) return 'primary'
    if (score >= 40) return 'warning'
    return 'error'
  }

  const getPotentialColor = (potential: string) => {
    const colors = {
      '매우 높음': 'error',
      '높음': 'warning',
      '보통': 'primary',
      '낮음': 'default',
      '매우 낮음': 'default',
    }
    return colors[potential] || 'default'
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          <AIIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          AI 기반 상품 소싱
        </Typography>
      </Box>

      {/* 대시보드 요약 */}
      {dashboardLoading ? (
        <CircularProgress />
      ) : dashboardData?.status === 'success' ? (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={3}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <TrendingUpIcon color="primary" sx={{ fontSize: 40 }} />
              <Typography variant="h4">
                {dashboardData.summary.total_trending_products}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                트렌딩 상품
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} md={3}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <MoneyIcon color="success" sx={{ fontSize: 40 }} />
              <Typography variant="h4">
                {dashboardData.summary.avg_profit_score.toFixed(1)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                평균 수익성 점수
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} md={3}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <RecommendIcon color="warning" sx={{ fontSize: 40 }} />
              <Typography variant="h4">
                {dashboardData.summary.top_recommendations_count}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                추천 상품
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} md={3}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <CategoryIcon color="info" sx={{ fontSize: 40 }} />
              <Typography variant="h4">
                {dashboardData.summary.opportunity_categories}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                유망 카테고리
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      ) : null}

      <Card>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="AI 추천 상품" />
          <Tab label="카테고리 트렌드" />
          <Tab label="사업 기회 분석" />
          <Tab label="수익성 분석" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          {/* AI 추천 상품 */}
          <Box mb={2}>
            <Button
              variant={recommendationType === 'balanced' ? 'contained' : 'outlined'}
              onClick={() => setRecommendationType('balanced')}
              sx={{ mr: 1 }}
            >
              균형 추천
            </Button>
            <Button
              variant={recommendationType === 'trend' ? 'contained' : 'outlined'}
              onClick={() => setRecommendationType('trend')}
              sx={{ mr: 1 }}
            >
              트렌드 기반
            </Button>
            <Button
              variant={recommendationType === 'profit' ? 'contained' : 'outlined'}
              onClick={() => setRecommendationType('profit')}
            >
              수익성 기반
            </Button>
          </Box>

          {recLoading ? (
            <LinearProgress />
          ) : recommendationsData?.status === 'success' ? (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>상품명</TableCell>
                    <TableCell>공급사</TableCell>
                    <TableCell>카테고리</TableCell>
                    <TableCell align="right">도매가</TableCell>
                    <TableCell align="right">추천가</TableCell>
                    <TableCell align="right">예상 마진</TableCell>
                    <TableCell align="center">수익성 점수</TableCell>
                    <TableCell>추천 사유</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {recommendationsData.recommendations.map((rec: any) => (
                    <TableRow key={rec.product_code}>
                      <TableCell>{rec.product_name}</TableCell>
                      <TableCell>
                        <Chip label={rec.supplier} size="small" />
                      </TableCell>
                      <TableCell>{rec.category}</TableCell>
                      <TableCell align="right">
                        {rec.wholesale_price.toLocaleString()}원
                      </TableCell>
                      <TableCell align="right">
                        {rec.profit_analysis?.recommended_price?.toLocaleString()}원
                      </TableCell>
                      <TableCell align="right">
                        {(rec.profit_analysis?.net_margin * 100).toFixed(1)}%
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={rec.profit_analysis?.profit_score || rec.recommendation_score}
                          color={getProfitScoreColor(
                            rec.profit_analysis?.profit_score || rec.recommendation_score
                          )}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{rec.reason}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Alert severity="info">추천 상품을 불러올 수 없습니다</Alert>
          )}
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          {/* 카테고리 트렌드 */}
          {categoryTrends?.status === 'success' ? (
            <Grid container spacing={2}>
              {categoryTrends.categories.map((cat: any) => (
                <Grid item xs={12} md={6} key={cat.category}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        {cat.category}
                      </Typography>
                      <Box display="flex" justifyContent="space-between" mb={1}>
                        <Typography variant="body2" color="text.secondary">
                          상품 수
                        </Typography>
                        <Typography variant="body2">{cat.product_count}개</Typography>
                      </Box>
                      <Box display="flex" justifyContent="space-between" mb={1}>
                        <Typography variant="body2" color="text.secondary">
                          평균 순위
                        </Typography>
                        <Typography variant="body2">{cat.avg_rank}위</Typography>
                      </Box>
                      <Box display="flex" justifyContent="space-between" mb={2}>
                        <Typography variant="body2" color="text.secondary">
                          총 리뷰
                        </Typography>
                        <Typography variant="body2">
                          {cat.total_reviews.toLocaleString()}개
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={cat.recommendation_score}
                        sx={{ mb: 1 }}
                      />
                      <Box display="flex" justifyContent="space-between">
                        <Typography variant="caption">트렌드 점수</Typography>
                        <Typography variant="caption" fontWeight="bold">
                          {cat.recommendation_score}
                        </Typography>
                      </Box>
                      <Box mt={1}>
                        <Chip
                          label={cat.potential}
                          size="small"
                          color={getPotentialColor(cat.potential)}
                        />
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          ) : (
            <Alert severity="info">카테고리 트렌드를 불러올 수 없습니다</Alert>
          )}
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          {/* 사업 기회 분석 */}
          {opportunities?.status === 'success' ? (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>카테고리</TableCell>
                    <TableCell align="center">시장 잠재력</TableCell>
                    <TableCell align="center">베스트셀러 수</TableCell>
                    <TableCell align="center">도매 상품 수</TableCell>
                    <TableCell align="center">평균 수익성</TableCell>
                    <TableCell align="center">기회 점수</TableCell>
                    <TableCell>추천</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {opportunities.opportunities.map((opp: any) => (
                    <TableRow key={opp.category}>
                      <TableCell>{opp.category}</TableCell>
                      <TableCell align="center">
                        <Rating
                          value={opp.market_potential / 20}
                          readOnly
                          size="small"
                          precision={0.5}
                        />
                      </TableCell>
                      <TableCell align="center">{opp.current_bestsellers}</TableCell>
                      <TableCell align="center">{opp.wholesale_available}</TableCell>
                      <TableCell align="center">
                        <Chip
                          label={opp.avg_profit_score}
                          size="small"
                          color={getProfitScoreColor(opp.avg_profit_score)}
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="h6" color="primary">
                          {opp.opportunity_score}
                        </Typography>
                      </TableCell>
                      <TableCell>{opp.recommendation}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Alert severity="info">사업 기회를 분석할 수 없습니다</Alert>
          )}
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          {/* 수익성 분석 */}
          <Alert severity="info" sx={{ mb: 2 }}>
            개별 상품의 수익성 분석은 상품 목록에서 확인하세요
          </Alert>
          {dashboardData?.profit_summary && (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      수익성 점수 분포
                    </Typography>
                    <Box>
                      {Object.entries(dashboardData.profit_summary).map(([key, value]: [string, any]) => (
                        <Box key={key} display="flex" justifyContent="space-between" mb={1}>
                          <Typography variant="body2">
                            {key === 'excellent' ? '우수 (80+)' :
                             key === 'good' ? '양호 (60-80)' :
                             key === 'fair' ? '보통 (40-60)' :
                             key === 'poor' ? '미흡 (20-40)' : '부진 (<20)'}
                          </Typography>
                          <Chip label={value} size="small" />
                        </Box>
                      ))}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}
        </TabPanel>
      </Card>
    </Box>
  )
}