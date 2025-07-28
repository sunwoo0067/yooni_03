import React, { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  CardMedia,
  Typography,
  Grid,
  Button,
  Chip,
  TextField,
  InputAdornment,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Avatar,
  Rating,
  Divider,
  IconButton,
  Tooltip,
  Badge,
  LinearProgress,
} from '@mui/material'
import {
  Search,
  FilterList,
  AutoAwesome,
  TrendingUp,
  AttachMoney,
  Inventory,
  ThumbUp,
  ThumbDown,
  BookmarkBorder,
  Bookmark,
  Psychology,
  Lightbulb,
  Category,
  LocalOffer,
} from '@mui/icons-material'

// 샘플 데이터
const aiRecommendations = [
  {
    id: 1,
    name: '스마트워치 충전 스탠드',
    category: '전자제품 액세서리',
    image: 'https://via.placeholder.com/200',
    confidence: 95,
    expectedRevenue: 15000000,
    expectedGrowth: 35,
    competitorCount: 3,
    marketDemand: 'high',
    reasoning: '스마트워치 판매량 증가에 따른 액세서리 수요 급증',
    tags: ['트렌드', '고수익', '빠른회전'],
    saved: false,
  },
  {
    id: 2,
    name: '휴대용 공기청정기',
    category: '생활가전',
    image: 'https://via.placeholder.com/200',
    confidence: 88,
    expectedRevenue: 25000000,
    expectedGrowth: 28,
    competitorCount: 5,
    marketDemand: 'medium',
    reasoning: '미세먼지 증가로 인한 개인 위생 제품 수요 상승',
    tags: ['건강', '프리미엄'],
    saved: true,
  },
  {
    id: 3,
    name: '접이식 캠핑 테이블',
    category: '아웃도어',
    image: 'https://via.placeholder.com/200',
    confidence: 92,
    expectedRevenue: 18000000,
    expectedGrowth: 42,
    competitorCount: 8,
    marketDemand: 'high',
    reasoning: '캠핑 인구 증가 및 경량화 트렌드',
    tags: ['시즌상품', '트렌드'],
    saved: false,
  },
]

const categoryInsights = [
  {
    category: '전자제품',
    growth: 25,
    opportunity: '웨어러블 액세서리 시장 확대',
    icon: <Category />,
  },
  {
    category: '생활용품',
    growth: 18,
    opportunity: '친환경 제품 수요 증가',
    icon: <Category />,
  },
  {
    category: '스포츠/레저',
    growth: 35,
    opportunity: '홈트레이닝 장비 인기',
    icon: <Category />,
  },
]

const AIRecommendations: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('')
  const [category, setCategory] = useState('all')
  const [sortBy, setSortBy] = useState('confidence')
  const [recommendations, setRecommendations] = useState(aiRecommendations)

  const handleSaveToggle = (id: number) => {
    setRecommendations(prev =>
      prev.map(item =>
        item.id === id ? { ...item, saved: !item.saved } : item
      )
    )
  }

  const getDemandColor = (demand: string) => {
    switch (demand) {
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
          AI 상품 추천
        </Typography>
        <Typography variant="body1" color="text.secondary">
          AI가 분석한 고수익 예상 상품을 확인하고 도입을 검토하세요
        </Typography>
      </Box>

      {/* 필터 및 검색 */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                placeholder="상품명 검색..."
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
                  <MenuItem value="outdoor">아웃도어</MenuItem>
                  <MenuItem value="home">생활용품</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={3}>
              <FormControl fullWidth>
                <InputLabel>정렬 기준</InputLabel>
                <Select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  label="정렬 기준"
                >
                  <MenuItem value="confidence">AI 신뢰도</MenuItem>
                  <MenuItem value="revenue">예상 수익</MenuItem>
                  <MenuItem value="growth">성장률</MenuItem>
                  <MenuItem value="demand">시장 수요</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={2}>
              <Button
                fullWidth
                variant="outlined"
                startIcon={<FilterList />}
              >
                필터
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* AI 인사이트 요약 */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {categoryInsights.map((insight) => (
          <Grid item xs={12} md={4} key={insight.category}>
            <Paper sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Avatar sx={{ bgcolor: 'primary.light', mr: 2 }}>
                  {insight.icon}
                </Avatar>
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="subtitle2">{insight.category}</Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <TrendingUp color="success" fontSize="small" />
                    <Typography variant="h6" color="success.main" sx={{ ml: 0.5 }}>
                      +{insight.growth}%
                    </Typography>
                  </Box>
                </Box>
              </Box>
              <Typography variant="body2" color="text.secondary">
                {insight.opportunity}
              </Typography>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {/* 추천 상품 목록 */}
      <Grid container spacing={3}>
        {recommendations.map((product) => (
          <Grid item xs={12} md={6} lg={4} key={product.id}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Box sx={{ position: 'relative' }}>
                <CardMedia
                  component="img"
                  height="200"
                  image={product.image}
                  alt={product.name}
                />
                <Box
                  sx={{
                    position: 'absolute',
                    top: 8,
                    right: 8,
                    display: 'flex',
                    gap: 1,
                  }}
                >
                  <Chip
                    label={`AI ${product.confidence}%`}
                    color="primary"
                    size="small"
                    icon={<Psychology />}
                  />
                  <IconButton
                    size="small"
                    sx={{ bgcolor: 'background.paper' }}
                    onClick={() => handleSaveToggle(product.id)}
                  >
                    {product.saved ? <Bookmark color="primary" /> : <BookmarkBorder />}
                  </IconButton>
                </Box>
              </Box>
              <CardContent sx={{ flexGrow: 1 }}>
                <Typography variant="h6" gutterBottom>
                  {product.name}
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  {product.category}
                </Typography>
                
                <Box sx={{ my: 2 }}>
                  <Chip
                    label={`수요: ${product.marketDemand.toUpperCase()}`}
                    size="small"
                    color={getDemandColor(product.marketDemand) as any}
                    sx={{ mr: 1 }}
                  />
                  {product.tags.map((tag) => (
                    <Chip
                      key={tag}
                      label={tag}
                      size="small"
                      variant="outlined"
                      sx={{ mr: 1, mb: 1 }}
                    />
                  ))}
                </Box>

                <Divider sx={{ my: 2 }} />

                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.secondary">
                      예상 수익
                    </Typography>
                    <Typography variant="subtitle1" color="primary">
                      ₩{(product.expectedRevenue / 1000000).toFixed(0)}M
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.secondary">
                      성장률
                    </Typography>
                    <Typography variant="subtitle1" color="success.main">
                      +{product.expectedGrowth}%
                    </Typography>
                  </Grid>
                </Grid>

                <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Lightbulb fontSize="small" color="primary" />
                    <Typography variant="caption" sx={{ ml: 1 }}>
                      AI 분석
                    </Typography>
                  </Box>
                  <Typography variant="body2">
                    {product.reasoning}
                  </Typography>
                </Box>

                <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                  <Button
                    fullWidth
                    variant="contained"
                    startIcon={<AutoAwesome />}
                  >
                    상세 분석
                  </Button>
                  <Button
                    fullWidth
                    variant="outlined"
                  >
                    도입 검토
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* AI 추천 알고리즘 설명 */}
      <Paper sx={{ mt: 4, p: 3, bgcolor: 'primary.main', color: 'primary.contrastText' }}>
        <Grid container spacing={3} alignItems="center">
          <Grid item xs={12} md={8}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Psychology sx={{ fontSize: 48 }} />
              <Box>
                <Typography variant="h6">
                  AI 추천 알고리즘
                </Typography>
                <Typography variant="body2">
                  시장 트렌드, 경쟁사 분석, 소비자 수요, 계절성 등 다양한 요소를 종합적으로 분석하여
                  귀하의 비즈니스에 최적화된 상품을 추천합니다.
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
            >
              AI 설정 관리
            </Button>
          </Grid>
        </Grid>
      </Paper>
    </Box>
  )
}

export default AIRecommendations