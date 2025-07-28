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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  InputAdornment,
  Pagination,
  Badge,
} from '@mui/material'
import {
  ShoppingCart,
  Visibility,
  CheckCircle,
  Cancel,
  AttachMoney,
  Inventory,
  FilterList,
  Refresh,
  TrendingUp,
  Assessment,
  Star,
} from '@mui/icons-material'
import { useNotification } from '@components/ui/NotificationSystem'
import axios from 'axios'

interface CollectedProduct {
  id: string
  source: string
  name: string
  price: number
  original_price?: number
  image_url?: string
  product_url?: string
  category?: string
  brand?: string
  description?: string
  stock_status: string
  supplier_id?: string
  collected_at: string
  status: string
  quality_score?: number
}

interface SourcingFilters {
  source: string
  status: string
  category: string
  keyword: string
  priceMin: string
  priceMax: string
}

const ProductSourcing: React.FC = () => {
  const notification = useNotification()
  const [products, setProducts] = useState<CollectedProduct[]>([])
  const [loading, setLoading] = useState(false)
  const [totalPages, setTotalPages] = useState(1)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalProducts, setTotalProducts] = useState(0)
  
  // 필터 상태
  const [filters, setFilters] = useState<SourcingFilters>({
    source: '',
    status: 'collected', // 기본적으로 수집된 상품만 표시
    category: '',
    keyword: '',
    priceMin: '',
    priceMax: ''
  })

  // 소싱 다이얼로그 상태
  const [sourcingDialog, setSourcingDialog] = useState<{
    open: boolean
    product: CollectedProduct | null
    sellingPrice: string
    markupPercentage: string
  }>({
    open: false,
    product: null,
    sellingPrice: '',
    markupPercentage: '30'
  })

  // 상품 상세 다이얼로그
  const [detailDialog, setDetailDialog] = useState<{
    open: boolean
    product: CollectedProduct | null
  }>({
    open: false,
    product: null
  })

  // 수집된 상품 목록 조회
  const fetchCollectedProducts = async (page: number = 1) => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (filters.source) params.append('source', filters.source)
      if (filters.status) params.append('status', filters.status)
      if (filters.category) params.append('category', filters.category)
      if (filters.keyword) params.append('keyword', filters.keyword)
      if (filters.priceMin) params.append('price_min', filters.priceMin)
      if (filters.priceMax) params.append('price_max', filters.priceMax)
      params.append('page', page.toString())
      params.append('limit', '20')

      const response = await axios.get(`/api/v1/product-collector/collected?${params}`)
      
      if (response.data.success) {
        setProducts(response.data.products)
        setTotalPages(response.data.total_pages)
        setTotalProducts(response.data.total)
        setCurrentPage(page)
      }
    } catch (error) {
      console.error('상품 조회 오류:', error)
      notification.error('상품 목록을 불러오는데 실패했습니다')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCollectedProducts(1)
  }, [filters])

  // 필터 변경 핸들러
  const handleFilterChange = (field: keyof SourcingFilters, value: string) => {
    setFilters(prev => ({ ...prev, [field]: value }))
  }

  // 소싱 다이얼로그 열기
  const openSourcingDialog = (product: CollectedProduct) => {
    const defaultMarkup = 30
    const suggestedPrice = product.price * (1 + defaultMarkup / 100)
    
    setSourcingDialog({
      open: true,
      product,
      sellingPrice: suggestedPrice.toFixed(0),
      markupPercentage: defaultMarkup.toString()
    })
  }

  // 마진율 변경 시 판매가 자동 계산
  const handleMarkupChange = (markup: string) => {
    if (sourcingDialog.product) {
      const markupNum = parseFloat(markup) || 0
      const newPrice = sourcingDialog.product.price * (1 + markupNum / 100)
      setSourcingDialog(prev => ({
        ...prev,
        markupPercentage: markup,
        sellingPrice: newPrice.toFixed(0)
      }))
    }
  }

  // 상품 소싱 실행
  const handleSourceProduct = async () => {
    if (!sourcingDialog.product) return

    try {
      const formData = new FormData()
      formData.append('selling_price', sourcingDialog.sellingPrice)
      formData.append('markup_percentage', sourcingDialog.markupPercentage)

      const response = await axios.post(
        `/api/v1/product-collector/source-product/${sourcingDialog.product.id}`,
        formData
      )

      if (response.data.success) {
        notification.success('상품이 성공적으로 소싱되었습니다!')
        setSourcingDialog({ open: false, product: null, sellingPrice: '', markupPercentage: '30' })
        fetchCollectedProducts(currentPage) // 목록 새로고침
      }
    } catch (error: any) {
      console.error('소싱 오류:', error)
      const errorMessage = error.response?.data?.detail || '소싱 중 오류가 발생했습니다'
      notification.error(errorMessage)
    }
  }

  // 상품 거부
  const handleRejectProduct = async (productId: string) => {
    const reason = prompt('거부 이유를 입력해주세요:')
    if (!reason) return

    try {
      const formData = new FormData()
      formData.append('reason', reason)

      const response = await axios.delete(
        `/api/v1/product-collector/collected/${productId}`,
        { data: formData }
      )

      if (response.data.success) {
        notification.success('상품이 거부되었습니다')
        fetchCollectedProducts(currentPage)
      }
    } catch (error: any) {
      console.error('거부 오류:', error)
      const errorMessage = error.response?.data?.detail || '거부 처리 중 오류가 발생했습니다'
      notification.error(errorMessage)
    }
  }

  // 도매처 이름 변환
  const getSourceName = (source: string) => {
    const sourceMap: Record<string, string> = {
      'ownerclan': '오너클랜',
      'domeme': '도매매',
      'gentrade': '젠트레이드'
    }
    return sourceMap[source] || source
  }

  // 상태 칩 컴포넌트
  const StatusChip = ({ status }: { status: string }) => {
    const statusConfig = {
      'collected': { color: 'primary' as const, label: '수집됨' },
      'sourced': { color: 'success' as const, label: '소싱됨' },
      'rejected': { color: 'error' as const, label: '거부됨' },
      'expired': { color: 'default' as const, label: '만료됨' }
    }
    
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.collected
    return <Chip size="small" color={config.color} label={config.label} />
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          🛒 상품 소싱
        </Typography>
        <Typography variant="body1" color="text.secondary">
          수집된 상품에서 판매할 상품을 선택하고 소싱합니다
        </Typography>
      </Box>

      {/* 필터 섹션 */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <FilterList sx={{ mr: 1 }} />
            <Typography variant="h6">필터</Typography>
            <Box sx={{ flexGrow: 1 }} />
            <Button
              startIcon={<Refresh />}
              onClick={() => fetchCollectedProducts(currentPage)}
              size="small"
            >
              새로고침
            </Button>
          </Box>
          
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={2}>
              <FormControl fullWidth size="small">
                <InputLabel>도매처</InputLabel>
                <Select
                  value={filters.source}
                  onChange={(e) => handleFilterChange('source', e.target.value)}
                  label="도매처"
                >
                  <MenuItem value="">전체</MenuItem>
                  <MenuItem value="ownerclan">오너클랜</MenuItem>
                  <MenuItem value="domeme">도매매</MenuItem>
                  <MenuItem value="gentrade">젠트레이드</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} sm={6} md={2}>
              <FormControl fullWidth size="small">
                <InputLabel>상태</InputLabel>
                <Select
                  value={filters.status}
                  onChange={(e) => handleFilterChange('status', e.target.value)}
                  label="상태"
                >
                  <MenuItem value="">전체</MenuItem>
                  <MenuItem value="collected">수집됨</MenuItem>
                  <MenuItem value="sourced">소싱됨</MenuItem>
                  <MenuItem value="rejected">거부됨</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                fullWidth
                size="small"
                label="카테고리"
                value={filters.category}
                onChange={(e) => handleFilterChange('category', e.target.value)}
              />
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                fullWidth
                size="small"
                label="키워드 검색"
                value={filters.keyword}
                onChange={(e) => handleFilterChange('keyword', e.target.value)}
                placeholder="상품명, 설명 검색"
              />
            </Grid>
            
            <Grid item xs={6} sm={3} md={1.5}>
              <TextField
                fullWidth
                size="small"
                label="최소 가격"
                type="number"
                value={filters.priceMin}
                onChange={(e) => handleFilterChange('priceMin', e.target.value)}
                InputProps={{
                  endAdornment: <InputAdornment position="end">원</InputAdornment>
                }}
              />
            </Grid>
            
            <Grid item xs={6} sm={3} md={1.5}>
              <TextField
                fullWidth
                size="small"
                label="최대 가격"
                type="number"
                value={filters.priceMax}
                onChange={(e) => handleFilterChange('priceMax', e.target.value)}
                InputProps={{
                  endAdornment: <InputAdornment position="end">원</InputAdornment>
                }}
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* 통계 카드 */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Inventory sx={{ fontSize: 40, color: 'primary.main', mb: 1 }} />
              <Typography variant="h6">{totalProducts}</Typography>
              <Typography variant="body2" color="text.secondary">
                총 수집 상품
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <CheckCircle sx={{ fontSize: 40, color: 'success.main', mb: 1 }} />
              <Typography variant="h6">
                {products.filter(p => p.status === 'sourced').length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                소싱 완료
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <TrendingUp sx={{ fontSize: 40, color: 'warning.main', mb: 1 }} />
              <Typography variant="h6">
                {products.filter(p => p.status === 'collected').length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                소싱 대기
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* 상품 목록 */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            수집된 상품 목록
          </Typography>
          
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : products.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Inventory sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />
              <Typography variant="body1" color="text.secondary">
                조건에 맞는 상품이 없습니다
              </Typography>
            </Box>
          ) : (
            <>
              <TableContainer component={Paper} sx={{ mt: 2 }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>이미지</TableCell>
                      <TableCell>상품 정보</TableCell>
                      <TableCell>도매처</TableCell>
                      <TableCell>가격</TableCell>
                      <TableCell>품질점수</TableCell>
                      <TableCell>상태</TableCell>
                      <TableCell>수집일</TableCell>
                      <TableCell>작업</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {products.map((product) => (
                      <TableRow key={product.id} hover>
                        <TableCell>
                          <img
                            src={product.image_url || 'https://via.placeholder.com/60x60?text=No+Image'}
                            alt={product.name}
                            style={{ width: 60, height: 60, objectFit: 'cover', borderRadius: 4 }}
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="subtitle2" gutterBottom>
                            {product.name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" display="block">
                            {product.brand && `${product.brand} • `}
                            {product.category}
                          </Typography>
                          {product.description && (
                            <Typography variant="caption" color="text.secondary" display="block">
                              {product.description.length > 50 
                                ? `${product.description.substring(0, 50)}...` 
                                : product.description}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Chip 
                            size="small" 
                            label={getSourceName(product.source)}
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="subtitle2">
                            {product.price.toLocaleString()}원
                          </Typography>
                          {product.original_price && product.original_price > product.price && (
                            <Typography 
                              variant="caption" 
                              color="text.secondary"
                              sx={{ textDecoration: 'line-through' }}
                            >
                              {product.original_price.toLocaleString()}원
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          {product.quality_score && (
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                              <Star sx={{ fontSize: 16, color: 'warning.main', mr: 0.5 }} />
                              <Typography variant="body2">
                                {product.quality_score.toFixed(1)}
                              </Typography>
                            </Box>
                          )}
                        </TableCell>
                        <TableCell>
                          <StatusChip status={product.status} />
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption">
                            {new Date(product.collected_at).toLocaleDateString()}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <Tooltip title="상세보기">
                              <IconButton
                                size="small"
                                onClick={() => setDetailDialog({ open: true, product })}
                              >
                                <Visibility />
                              </IconButton>
                            </Tooltip>
                            
                            {product.status === 'collected' && (
                              <>
                                <Tooltip title="소싱하기">
                                  <IconButton
                                    size="small"
                                    color="primary"
                                    onClick={() => openSourcingDialog(product)}
                                  >
                                    <ShoppingCart />
                                  </IconButton>
                                </Tooltip>
                                
                                <Tooltip title="거부하기">
                                  <IconButton
                                    size="small"
                                    color="error"
                                    onClick={() => handleRejectProduct(product.id)}
                                  >
                                    <Cancel />
                                  </IconButton>
                                </Tooltip>
                              </>
                            )}
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              
              {/* 페이지네이션 */}
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
                <Pagination
                  count={totalPages}
                  page={currentPage}
                  onChange={(_, page) => fetchCollectedProducts(page)}
                  color="primary"
                />
              </Box>
            </>
          )}
        </CardContent>
      </Card>

      {/* 소싱 다이얼로그 */}
      <Dialog 
        open={sourcingDialog.open} 
        onClose={() => setSourcingDialog({ open: false, product: null, sellingPrice: '', markupPercentage: '30' })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>상품 소싱</DialogTitle>
        <DialogContent>
          {sourcingDialog.product && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="h6" gutterBottom>
                {sourcingDialog.product.name}
              </Typography>
              
              <Grid container spacing={2} sx={{ mt: 1 }}>
                <Grid item xs={12}>
                  <Alert severity="info">
                    도매가: {sourcingDialog.product.price.toLocaleString()}원
                  </Alert>
                </Grid>
                
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="마진율 (%)"
                    type="number"
                    value={sourcingDialog.markupPercentage}
                    onChange={(e) => handleMarkupChange(e.target.value)}
                    inputProps={{ min: 0, max: 1000 }}
                  />
                </Grid>
                
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="판매가 (원)"
                    type="number"
                    value={sourcingDialog.sellingPrice}
                    onChange={(e) => setSourcingDialog(prev => ({ ...prev, sellingPrice: e.target.value }))}
                    inputProps={{ min: 0 }}
                  />
                </Grid>
                
                <Grid item xs={12}>
                  <Alert severity="success">
                    예상 수익: {(parseFloat(sourcingDialog.sellingPrice) - sourcingDialog.product.price).toLocaleString()}원
                  </Alert>
                </Grid>
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => setSourcingDialog({ open: false, product: null, sellingPrice: '', markupPercentage: '30' })}
          >
            취소
          </Button>
          <Button 
            variant="contained" 
            onClick={handleSourceProduct}
            startIcon={<ShoppingCart />}
          >
            소싱하기
          </Button>
        </DialogActions>
      </Dialog>

      {/* 상품 상세 다이얼로그 */}
      <Dialog 
        open={detailDialog.open} 
        onClose={() => setDetailDialog({ open: false, product: null })}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>상품 상세 정보</DialogTitle>
        <DialogContent>
          {detailDialog.product && (
            <Box sx={{ mt: 2 }}>
              <Grid container spacing={3}>
                <Grid item xs={12} md={4}>
                  <img
                    src={detailDialog.product.image_url || 'https://via.placeholder.com/300x300?text=No+Image'}
                    alt={detailDialog.product.name}
                    style={{ width: '100%', height: 'auto', borderRadius: 8 }}
                  />
                </Grid>
                <Grid item xs={12} md={8}>
                  <Typography variant="h5" gutterBottom>
                    {detailDialog.product.name}
                  </Typography>
                  
                  <Box sx={{ mb: 2 }}>
                    <Chip label={getSourceName(detailDialog.product.source)} sx={{ mr: 1 }} />
                    <StatusChip status={detailDialog.product.status} />
                  </Box>
                  
                  <Typography variant="body1" gutterBottom>
                    <strong>브랜드:</strong> {detailDialog.product.brand || 'N/A'}
                  </Typography>
                  
                  <Typography variant="body1" gutterBottom>
                    <strong>카테고리:</strong> {detailDialog.product.category || 'N/A'}
                  </Typography>
                  
                  <Typography variant="body1" gutterBottom>
                    <strong>가격:</strong> {detailDialog.product.price.toLocaleString()}원
                    {detailDialog.product.original_price && (
                      <span style={{ textDecoration: 'line-through', marginLeft: 8, color: '#999' }}>
                        {detailDialog.product.original_price.toLocaleString()}원
                      </span>
                    )}
                  </Typography>
                  
                  {detailDialog.product.quality_score && (
                    <Typography variant="body1" gutterBottom>
                      <strong>품질 점수:</strong> {detailDialog.product.quality_score.toFixed(1)}/10
                    </Typography>
                  )}
                  
                  <Typography variant="body1" gutterBottom>
                    <strong>수집일:</strong> {new Date(detailDialog.product.collected_at).toLocaleString()}
                  </Typography>
                  
                  {detailDialog.product.description && (
                    <Typography variant="body1" gutterBottom>
                      <strong>설명:</strong> {detailDialog.product.description}
                    </Typography>
                  )}
                  
                  {detailDialog.product.product_url && (
                    <Button
                      variant="outlined"
                      href={detailDialog.product.product_url}
                      target="_blank"
                      sx={{ mt: 2 }}
                    >
                      원본 상품 보기
                    </Button>
                  )}
                </Grid>
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialog({ open: false, product: null })}>
            닫기
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default ProductSourcing