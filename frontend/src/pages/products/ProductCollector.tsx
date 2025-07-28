import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  CircularProgress,
  Alert,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Paper,
  IconButton,
  InputAdornment,
  CardMedia,
  CardActions,
} from '@mui/material'
import {
  CloudDownload,
  Search,
  CheckCircle,
  Error,
  Warning,
  ContentCopy,
  Link,
  Category,
  AttachMoney,
  Inventory,
  Store,
  AddShoppingCart,
  Visibility,
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { useNotification } from '@components/ui/NotificationSystem'
import { collectorAPI } from '@services/api'
import { formatCurrency } from '@utils/format'
import { toast } from 'react-hot-toast'

interface CollectedProduct {
  id?: string
  source: string
  name: string
  price: number
  original_price?: number
  image_url?: string
  main_image_url?: string
  product_url?: string
  category?: string
  brand?: string
  description?: string
  stock_status: string
  supplier_id?: string
  supplier_name?: string
  collected_at: string
}

interface WholesalerSource {
  id: string
  name: string
  description: string
  categories: string[]
  is_active?: boolean
}

const ProductCollector: React.FC = () => {
  const navigate = useNavigate()
  const notification = useNotification()
  const [isCollecting, setIsCollecting] = useState(false)
  const [selectedSource, setSelectedSource] = useState('ownerclan')
  const [keyword, setKeyword] = useState('')
  const [category, setCategory] = useState('')
  const [priceMin, setPriceMin] = useState(0)
  const [priceMax, setPriceMax] = useState(1000000)
  const [collectedProducts, setCollectedProducts] = useState<CollectedProduct[]>([])
  const [collectionProgress, setCollectionProgress] = useState(0)
  const [availableSources, setAvailableSources] = useState<WholesalerSource[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)

  // 초기 데이터 로드
  useEffect(() => {
    loadSources()
  }, [])

  // 도매처 목록 로드
  const loadSources = async () => {
    try {
      const response = await collectorAPI.getSources()
      if (response.data) {
        setAvailableSources(response.data)
        // 카테고리 목록 추출
        const allCategories = new Set<string>()
        response.data.forEach((source: WholesalerSource) => {
          source.categories?.forEach(cat => allCategories.add(cat))
        })
        setCategories(Array.from(allCategories))
      }
    } catch (error) {
      console.error('Failed to load sources:', error)
      // 폴백 데이터
      setAvailableSources([
        {
          id: 'ownerclan',
          name: '오너클랜',
          description: '국내 대표 B2B 도매 플랫폼',
          categories: ['전자제품', '패션', '생활용품', '스포츠']
        },
        {
          id: 'domeme',
          name: '도매매',
          description: '합리적인 가격의 도매 상품',
          categories: ['전자제품', '생활용품', '건강식품']
        },
        {
          id: 'gentrade',
          name: '젠트레이드',
          description: '프리미엄 도매 상품 전문',
          categories: ['전자제품', '패션', '뷰티']
        }
      ])
    }
  }

  // 상품 수집
  const handleCollectProducts = async () => {
    if (!keyword.trim() && !category) {
      notification.error('검색어 또는 카테고리를 선택해주세요')
      return
    }

    setIsCollecting(true)
    setCollectionProgress(0)
    setCollectedProducts([])

    try {
      // 진행률 업데이트
      const progressInterval = setInterval(() => {
        setCollectionProgress(prev => Math.min(prev + 10, 90))
      }, 300)

      const response = await collectorAPI.collectProducts({
        source: selectedSource,
        keyword: keyword.trim(),
        category,
        price_min: priceMin,
        price_max: priceMax,
        limit: 50,
      })

      clearInterval(progressInterval)
      setCollectionProgress(100)

      if (response.data.products && response.data.products.length > 0) {
        setCollectedProducts(response.data.products)
        notification.success(`${response.data.products.length}개의 상품을 수집했습니다.`)
      } else {
        notification.warning('수집된 상품이 없습니다. 다른 검색어를 시도해보세요.')
      }
    } catch (error: any) {
      console.error('상품 수집 오류:', error)
      notification.error(error.response?.data?.detail || '상품 수집 중 오류가 발생했습니다.')
    } finally {
      setIsCollecting(false)
      setTimeout(() => setCollectionProgress(0), 1000)
    }
  }

  // 상품 소싱 (실제 판매 상품으로 등록)
  const handleSourceProduct = async (product: CollectedProduct) => {
    if (!product.id) return

    try {
      setIsLoading(true)
      await collectorAPI.sourceProduct(product.id, 0.3) // 30% 마진
      notification.success(`"${product.name}" 상품이 판매 상품으로 등록되었습니다.`)
      
      // 수집된 상품 목록에서 제거
      setCollectedProducts(prev => prev.filter(p => p.id !== product.id))
    } catch (error: any) {
      notification.error('상품 소싱에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  // 수집된 상품 목록 페이지로 이동
  const handleViewCollectedProducts = () => {
    navigate('/products/sync')
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          🛍️ 도매처 상품 수집
        </Typography>
        <Typography variant="body1" color="text.secondary">
          국내 주요 도매처에서 상품을 검색하여 데이터베이스에 수집합니다. 수집된 상품은 나중에 판매 상품으로 등록할 수 있습니다.
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* 수집 설정 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                수집 설정
              </Typography>
              
              {/* 도매처 선택 */}
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>도매처 선택</InputLabel>
                <Select
                  value={selectedSource}
                  onChange={(e) => setSelectedSource(e.target.value)}
                  label="도매처 선택"
                >
                  {availableSources.map((source) => (
                    <MenuItem key={source.id} value={source.id}>
                      <Box>
                        <Typography variant="body1">{source.name}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {source.description}
                        </Typography>
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {/* 검색 키워드 */}
              <TextField
                fullWidth
                label="검색 키워드"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="예: 무선이어폰, 블루투스헤드폰"
                sx={{ mb: 2 }}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search />
                    </InputAdornment>
                  ),
                }}
              />

              {/* 카테고리 */}
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>카테고리</InputLabel>
                <Select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  label="카테고리"
                >
                  <MenuItem value="">전체</MenuItem>
                  {categories.map((cat) => (
                    <MenuItem key={cat} value={cat}>{cat}</MenuItem>
                  ))}
                </Select>
              </FormControl>

              {/* 가격 범위 */}
              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary" gutterBottom>
                  가격 범위
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <TextField
                      fullWidth
                      label="최소 가격"
                      type="number"
                      value={priceMin}
                      onChange={(e) => setPriceMin(Number(e.target.value))}
                      InputProps={{
                        startAdornment: <InputAdornment position="start">₩</InputAdornment>,
                      }}
                    />
                  </Grid>
                  <Grid item xs={6}>
                    <TextField
                      fullWidth
                      label="최대 가격"
                      type="number"
                      value={priceMax}
                      onChange={(e) => setPriceMax(Number(e.target.value))}
                      InputProps={{
                        startAdornment: <InputAdornment position="start">₩</InputAdornment>,
                      }}
                    />
                  </Grid>
                </Grid>
              </Box>

              {/* 수집 버튼 */}
              <Button
                fullWidth
                variant="contained"
                size="large"
                onClick={handleCollectProducts}
                disabled={isCollecting}
                startIcon={isCollecting ? <CircularProgress size={20} /> : <CloudDownload />}
              >
                {isCollecting ? '상품 수집 중...' : '상품 수집 시작'}
              </Button>

              {/* 진행률 표시 */}
              {collectionProgress > 0 && (
                <Box sx={{ mt: 2 }}>
                  <LinearProgress variant="determinate" value={collectionProgress} />
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                    수집 진행률: {collectionProgress}%
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* 수집 가이드 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Store sx={{ mr: 1 }} />
                수집 가이드
              </Typography>
              
              <List>
                <ListItem>
                  <ListItemIcon>
                    <CheckCircle color="success" />
                  </ListItemIcon>
                  <ListItemText
                    primary="실시간 상품 수집"
                    secondary="도매처의 최신 상품 정보를 실시간으로 수집합니다"
                  />
                </ListItem>
                <Divider />
                <ListItem>
                  <ListItemIcon>
                    <Category color="primary" />
                  </ListItemIcon>
                  <ListItemText
                    primary="카테고리별 수집"
                    secondary="원하는 카테고리의 상품만 선택적으로 수집할 수 있습니다"
                  />
                </ListItem>
                <Divider />
                <ListItem>
                  <ListItemIcon>
                    <AttachMoney color="warning" />
                  </ListItemIcon>
                  <ListItemText
                    primary="가격 필터링"
                    secondary="설정한 가격 범위 내의 상품만 수집됩니다"
                  />
                </ListItem>
                <Divider />
                <ListItem>
                  <ListItemIcon>
                    <Inventory color="info" />
                  </ListItemIcon>
                  <ListItemText
                    primary="재고 상태 확인"
                    secondary="실시간 재고 상태를 확인하여 판매 가능한 상품만 수집합니다"
                  />
                </ListItem>
              </List>

              <Alert severity="info" sx={{ mt: 2 }}>
                수집된 상품은 '도매처 동기화' 페이지에서 확인하고 판매 상품으로 등록할 수 있습니다.
              </Alert>

              <Button
                fullWidth
                variant="outlined"
                sx={{ mt: 2 }}
                onClick={handleViewCollectedProducts}
              >
                수집된 상품 목록 보기
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* 수집 결과 */}
        {collectedProducts.length > 0 && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  수집 결과 ({collectedProducts.length}개)
                </Typography>
                
                <Grid container spacing={2}>
                  {collectedProducts.map((product, index) => (
                    <Grid item xs={12} sm={6} md={4} lg={3} key={index}>
                      <Card>
                        <CardMedia
                          component="img"
                          height="200"
                          image={product.main_image_url || product.image_url || '/placeholder.png'}
                          alt={product.name}
                        />
                        <CardContent>
                          <Typography variant="subtitle2" noWrap>
                            {product.name}
                          </Typography>
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            {product.brand} | {product.category}
                          </Typography>
                          <Typography variant="h6" color="primary">
                            {formatCurrency(product.price)}
                          </Typography>
                          {product.original_price && (
                            <Typography variant="caption" color="text.secondary" sx={{ textDecoration: 'line-through' }}>
                              {formatCurrency(product.original_price)}
                            </Typography>
                          )}
                          <Box sx={{ mt: 1 }}>
                            <Chip 
                              label={product.source} 
                              size="small" 
                              sx={{ mr: 1 }}
                            />
                            <Chip 
                              label={product.stock_status} 
                              size="small" 
                              color={product.stock_status === 'available' ? 'success' : 'warning'}
                            />
                          </Box>
                        </CardContent>
                        <CardActions>
                          <Button 
                            size="small" 
                            startIcon={<Visibility />}
                            href={product.product_url || '#'}
                            target="_blank"
                            disabled={!product.product_url}
                          >
                            원본
                          </Button>
                          <Button 
                            size="small" 
                            color="primary"
                            startIcon={<AddShoppingCart />}
                            onClick={() => handleSourceProduct(product)}
                            disabled={isLoading}
                          >
                            소싱
                          </Button>
                        </CardActions>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  )
}

export default ProductCollector