import React, { useState, useCallback, useMemo } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  TextField,
  InputAdornment,
  IconButton,
  Chip,
  Menu,
  MenuItem,
  FormControl,
  Select,
  SelectChangeEvent,
  Card as MuiCard,
  CardContent,
  CardMedia,
  CardActions,
  SpeedDial,
  SpeedDialAction,
  SpeedDialIcon,
  Tooltip,
  Badge,
  ToggleButton,
  ToggleButtonGroup,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Checkbox,
  Slider,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Skeleton,
  useTheme,
  alpha,
  Fade,
  Zoom,
} from '@mui/material'
import {
  DataGrid,
  GridColDef,
  GridRowSelectionModel,
  GridActionsCellItem,
  GridRenderCellParams,
} from '@mui/x-data-grid'
import {
  Search,
  Add,
  FileDownload,
  FileUpload,
  FilterList,
  MoreVert,
  Edit,
  Delete,
  Sync,
  Category,
  Inventory,
  TrendingUp,
  Warning,
  CheckCircle,
  Cancel,
  CloudSync,
  Analytics,
  ViewModule,
  ViewList,
  FilterAlt,
  Visibility,
  ShoppingCart,
  LocalOffer,
  Star,
  Close,
} from '@mui/icons-material'
import { motion, AnimatePresence } from 'framer-motion'
import { useAppDispatch, useAppSelector } from '@store/hooks'
import {
  selectProductFilters,
  setFilters as setProductFilters,
  selectBulkSelection,
  setBulkSelection,
  clearBulkSelection,
} from '@store/slices/productSlice'
import { useProducts, useDeleteProduct } from '@hooks/useProducts'
import { formatCurrency, formatNumber } from '@utils/format'
import ProductFormDialog from './ProductFormDialog'
import ProductDetailDialog from './ProductDetailDialog'
import BulkActionsDialog from './BulkActionsDialog'
import ImportExportDialog from './ImportExportDialog'
import PlatformSyncDialog from './PlatformSyncDialog'
import { Product } from '@/types/product'
import { toast } from 'react-hot-toast'
import EmptyState, { ProductsEmptyState } from '@components/ui/EmptyState'
import { PageSkeleton, DataGridSkeleton } from '@components/ui/Skeleton'
import { useNotification, BusinessNotifications } from '@components/ui/NotificationSystem'
import { Card, StatCard } from '@components/ui/Card'
import Table from '@components/ui/Table'
import FilterPanel, { FilterGroup } from '@components/ui/FilterPanel'
import SearchBar from '@components/ui/SearchBar'
import QuickActions from '@components/ui/QuickActions'

const Products: React.FC = () => {
  const theme = useTheme()
  const dispatch = useAppDispatch()
  const productFilters = useAppSelector(selectProductFilters)
  const bulkSelection = useAppSelector(selectBulkSelection)
  
  // React Query hooks
  const { data: productsData, isLoading: loading, error } = useProducts(productFilters)
  const deleteProductMutation = useDeleteProduct()
  const products = productsData?.products || []
  
  // 강화된 알림 시스템
  const notification = useNotification()

  // States
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedRows, setSelectedRows] = useState<GridRowSelectionModel>([])
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)
  const [dialogState, setDialogState] = useState({
    form: false,
    detail: false,
    bulkActions: false,
    importExport: false,
    platformSync: false,
    preview: false,
  })
  const [localFilters, setLocalFilters] = useState<{
    category: string[]
    status: Array<'active' | 'inactive' | 'out_of_stock' | 'discontinued'>
    priceRange: [number, number]
    stock: string[]
    platform: string[]
  }>({
    category: [],
    status: [],
    priceRange: [0, 1000000],
    stock: [],
    platform: [],
  })
  const [speedDialOpen, setSpeedDialOpen] = useState(false)
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false)
  const [previewProduct, setPreviewProduct] = useState<Product | null>(null)

  // Update Redux filters when local filters change
  React.useEffect(() => {
    const filters = {
      search: searchQuery,
      category: localFilters.category.length > 0 ? localFilters.category[0] : undefined,
      status: localFilters.status.length > 0 ? localFilters.status[0] : undefined,
      priceMin: localFilters.priceRange[0],
      priceMax: localFilters.priceRange[1],
    }
    dispatch(setProductFilters(filters))
  }, [dispatch, searchQuery, localFilters])

  // Handlers
  const handleSearch = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(event.target.value)
  }, [])

  const handleFilterChange = useCallback((filterId: string, value: any) => {
    setLocalFilters(prev => ({
      ...prev,
      [filterId]: value,
    }))
  }, [])

  const handleViewModeChange = (_: React.MouseEvent<HTMLElement>, newMode: 'grid' | 'list' | null) => {
    if (newMode !== null) {
      setViewMode(newMode)
    }
  }

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
  }

  const handleDialogOpen = (dialog: keyof typeof dialogState, product?: Product) => {
    if (product) {
      setSelectedProduct(product)
    }
    setDialogState(prev => ({ ...prev, [dialog]: true }))
    handleMenuClose()
  }

  const handleDialogClose = (dialog: keyof typeof dialogState) => {
    setDialogState(prev => ({ ...prev, [dialog]: false }))
    if (dialog !== 'detail' && dialog !== 'preview') {
      setSelectedProduct(null)
    }
  }

  const handlePreview = (product: Product) => {
    setPreviewProduct(product)
    setDialogState(prev => ({ ...prev, preview: true }))
  }

  const handleDeleteProduct = async (product: Product) => {
    if (window.confirm(`정말로 "${product.name}" 상품을 삭제하시겠습니까?`)) {
      try {
        await deleteProductMutation.mutateAsync(product.id)
        
        // 강화된 알림 시스템 사용 (Undo 기능 포함)
        notification.showSuccess(
          '상품 삭제 완료',
          `"${product.name}" 상품이 삭제되었습니다.`,
          [
            {
              label: '취소 (복구)',
              action: () => {
                // 실제로는 복구 API 호출
                notification.showInfo('복구 완료', '상품이 복구되었습니다.')
              },
              variant: 'outlined',
              color: 'primary'
            }
          ]
        )
      } catch (error) {
        notification.showError(
          '삭제 실패',
          '상품 삭제 중 오류가 발생했습니다.',
          [
            {
              label: '다시 시도',
              action: () => handleDeleteProduct(product),
              variant: 'contained',
              color: 'error'
            }
          ]
        )
      }
    }
  }

  // 상품 선택 처리
  const handleSelectRow = (product: Product) => {
    setSelectedRows(prev => {
      const isSelected = prev.includes(product.id)
      if (isSelected) {
        return prev.filter(id => id !== product.id)
      } else {
        return [...prev, product.id]
      }
    })
  }

  // Filtered products
  const filteredProducts = useMemo(() => {
    return products.filter((product: Product) => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        if (
          !product.name.toLowerCase().includes(query) &&
          !product.sku?.toLowerCase().includes(query) &&
          !product.description?.toLowerCase().includes(query)
        ) {
          return false
        }
      }

      // Category filter
      if (localFilters.category.length > 0 && !localFilters.category.includes(product.category || '')) {
        return false
      }

      // Status filter
      if (localFilters.status.length > 0 && !localFilters.status.includes(product.status || '')) {
        return false
      }

      // Price range filter
      const [minPrice, maxPrice] = localFilters.priceRange
      if (product.price < minPrice || product.price > maxPrice) {
        return false
      }

      // Stock filter
      if (localFilters.stock.length > 0) {
        const stock = product.stock_quantity || 0
        if (localFilters.stock.includes('out_of_stock') && stock !== 0) return false
        if (localFilters.stock.includes('low_stock') && (stock === 0 || stock >= 10)) return false
        if (localFilters.stock.includes('in_stock') && stock < 10) return false
      }

      return true
    })
  }, [products, searchQuery, localFilters])

  // Statistics
  const statistics = useMemo(() => {
    const total = products.length
    const active = products.filter((p: Product) => p.status === 'active').length
    const outOfStock = products.filter((p: Product) => p.stock_quantity === 0).length
    const lowStock = products.filter((p: Product) => p.stock_quantity > 0 && p.stock_quantity < 10).length

    return { total, active, outOfStock, lowStock }
  }, [products])

  // DataGrid columns
  const columns: GridColDef[] = [
    {
      field: 'name',
      headerName: '상품명',
      flex: 1,
      minWidth: 200,
      renderCell: (params: GridRenderCellParams) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {params.row.main_image_url && (
            <img
              src={params.row.main_image_url}
              alt={params.row.name}
              style={{ width: 40, height: 40, borderRadius: 4, objectFit: 'cover' }}
            />
          )}
          <Box>
            <Typography variant="body2" fontWeight={500}>
              {params.row.name}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {params.row.sku || 'SKU 없음'}
            </Typography>
          </Box>
        </Box>
      ),
    },
    {
      field: 'category',
      headerName: '카테고리',
      width: 120,
      renderCell: (params: GridRenderCellParams) => (
        <Chip
          label={params.value || '미분류'}
          size="small"
          variant="outlined"
          icon={<Category fontSize="small" />}
        />
      ),
    },
    {
      field: 'price',
      headerName: '판매가',
      width: 120,
      align: 'right',
      headerAlign: 'right',
      valueFormatter: (params) => formatCurrency(params.value),
    },
    {
      field: 'cost',
      headerName: '원가',
      width: 100,
      align: 'right',
      headerAlign: 'right',
      valueFormatter: (params) => params.value ? formatCurrency(params.value) : '-',
    },
    {
      field: 'margin',
      headerName: '마진율',
      width: 100,
      align: 'right',
      headerAlign: 'right',
      renderCell: (params: GridRenderCellParams) => {
        if (!params.row.cost || !params.row.price) return '-'
        const margin = ((params.row.price - params.row.cost) / params.row.price) * 100
        return (
          <Chip
            label={`${margin.toFixed(1)}%`}
            size="small"
            color={margin >= 30 ? 'success' : margin >= 20 ? 'warning' : 'error'}
          />
        )
      },
    },
    {
      field: 'stock_quantity',
      headerName: '재고',
      width: 100,
      align: 'right',
      headerAlign: 'right',
      renderCell: (params: GridRenderCellParams) => {
        const stock = params.value || 0
        let color: 'error' | 'warning' | 'success' = 'success'
        let icon = <CheckCircle fontSize="small" />
        
        if (stock === 0) {
          color = 'error'
          icon = <Cancel fontSize="small" />
        } else if (stock < 10) {
          color = 'warning'
          icon = <Warning fontSize="small" />
        }

        return (
          <Chip
            label={formatNumber(stock)}
            size="small"
            color={color}
            icon={icon}
          />
        )
      },
    },
    {
      field: 'status',
      headerName: '상태',
      width: 100,
      renderCell: (params: GridRenderCellParams) => {
        const statusConfig = {
          active: { label: '판매중', color: 'success' as const },
          inactive: { label: '판매중지', color: 'warning' as const },
          out_of_stock: { label: '품절', color: 'error' as const },
          discontinued: { label: '단종', color: 'default' as const },
        }
        const config = statusConfig[params.value as keyof typeof statusConfig] || statusConfig.inactive
        
        return (
          <Chip
            label={config.label}
            size="small"
            color={config.color}
          />
        )
      },
    },
    {
      field: 'platform_sync',
      headerName: '플랫폼 연동',
      width: 150,
      renderCell: (params: GridRenderCellParams) => {
        const platforms = params.row.platform_listings || []
        const syncedCount = platforms.filter((p: any) => p.is_synced).length
        
        return (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CloudSync color={syncedCount > 0 ? 'primary' : 'disabled'} fontSize="small" />
            <Typography variant="body2" color={syncedCount > 0 ? 'text.primary' : 'text.disabled'}>
              {syncedCount}/{platforms.length}
            </Typography>
          </Box>
        )
      },
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: '작업',
      width: 100,
      getActions: (params) => [
        <GridActionsCellItem
          icon={<Analytics />}
          label="상세보기"
          onClick={() => handleDialogOpen('detail', params.row)}
        />,
        <GridActionsCellItem
          icon={<Edit />}
          label="수정"
          onClick={() => handleDialogOpen('form', params.row)}
        />,
        <GridActionsCellItem
          icon={<Delete />}
          label="삭제"
          onClick={() => handleDeleteProduct(params.row)}
          color="error"
        />,
      ],
    },
  ]

  const speedDialActions = [
    { icon: <Add />, name: '상품 추가', action: () => handleDialogOpen('form') },
    { icon: <FileUpload />, name: '가져오기', action: () => handleDialogOpen('importExport') },
    { icon: <Sync />, name: '플랫폼 동기화', action: () => handleDialogOpen('platformSync') },
  ]

  // 필터 그룹 정의
  const filterGroups: FilterGroup[] = [
    {
      id: 'category',
      label: '카테고리',
      type: 'checkbox',
      options: [
        { label: '패션', value: 'fashion', count: products.filter((p: Product) => p.category === 'fashion').length },
        { label: '전자제품', value: 'electronics', count: products.filter((p: Product) => p.category === 'electronics').length },
        { label: '홈/리빙', value: 'home', count: products.filter((p: Product) => p.category === 'home').length },
        { label: '뷰티', value: 'beauty', count: products.filter((p: Product) => p.category === 'beauty').length },
        { label: '스포츠', value: 'sports', count: products.filter((p: Product) => p.category === 'sports').length },
      ],
    },
    {
      id: 'status',
      label: '상태',
      type: 'checkbox',
      options: [
        { label: '판매중', value: 'active', count: products.filter((p: Product) => p.status === 'active').length },
        { label: '판매중지', value: 'inactive', count: products.filter((p: Product) => p.status === 'inactive').length },
        { label: '품절', value: 'out_of_stock', count: products.filter((p: Product) => p.status === 'out_of_stock').length },
        { label: '단종', value: 'discontinued', count: products.filter((p: Product) => p.status === 'discontinued').length },
      ],
    },
    {
      id: 'priceRange',
      label: '가격대',
      type: 'range',
      min: 0,
      max: 1000000,
    },
    {
      id: 'stock',
      label: '재고 상태',
      type: 'checkbox',
      options: [
        { label: '품절', value: 'out_of_stock', count: products.filter((p: Product) => (p.stock_quantity || 0) === 0).length },
        { label: '낮은 재고', value: 'low_stock', count: products.filter((p: Product) => (p.stock_quantity || 0) > 0 && (p.stock_quantity || 0) < 10).length },
        { label: '충분한 재고', value: 'in_stock', count: products.filter((p: Product) => (p.stock_quantity || 0) >= 10).length },
      ],
    },
  ]

  // 로딩 상태에서 스켈레톤 표시 (사용자 중심 개선)
  if (loading) {
    return <PageSkeleton />
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          상품 관리
        </Typography>
        <Typography variant="body1" color="text.secondary">
          상품을 추가하고 재고를 관리하세요
        </Typography>
      </Box>

      {/* Statistics Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="전체 상품"
            value={formatNumber(statistics.total)}
            icon={<Inventory />}
            color="primary"
            loading={loading}
            onClick={() => setLocalFilters({ ...localFilters, category: [], status: [] })}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="판매중"
            value={formatNumber(statistics.active)}
            icon={<CheckCircle />}
            color="success"
            loading={loading}
            onClick={() => setLocalFilters({ ...localFilters, status: ['active'] })}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="품절"
            value={formatNumber(statistics.outOfStock)}
            icon={<Cancel />}
            color="error"
            loading={loading}
            onClick={() => setLocalFilters({ ...localFilters, stock: ['out_of_stock'] })}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="낮은 재고"
            value={formatNumber(statistics.lowStock)}
            icon={<Warning />}
            color="warning"
            loading={loading}
            onClick={() => setLocalFilters({ ...localFilters, stock: ['low_stock'] })}
          />
        </Grid>
      </Grid>

      {/* Toolbar */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <Box sx={{ flex: 1, minWidth: 300 }}>
            <SearchBar
              placeholder="상품명, SKU, 설명으로 검색..."
              onSearch={setSearchQuery}
              suggestions={products.slice(0, 5).map((p: Product) => ({
                id: p.id,
                title: p.name,
                subtitle: p.sku || '상품 코드',
                type: 'product' as const,
                action: () => handlePreview(p),
              }))}
              fullWidth
            />
          </Box>
          
          <ToggleButtonGroup
            value={viewMode}
            exclusive
            onChange={handleViewModeChange}
            size="small"
          >
            <ToggleButton value="grid">
              <Tooltip title="그리드 보기">
                <ViewModule />
              </Tooltip>
            </ToggleButton>
            <ToggleButton value="list">
              <Tooltip title="리스트 보기">
                <ViewList />
              </Tooltip>
            </ToggleButton>
          </ToggleButtonGroup>

          <Badge badgeContent={Object.values(localFilters).flat().filter(v => v && v !== 'all').length} color="primary">
            <Button
              variant="outlined"
              startIcon={<FilterAlt />}
              onClick={() => setFilterDrawerOpen(true)}
            >
              필터
            </Button>
          </Badge>

          {selectedRows.length > 0 && (
            <Chip
              label={`${selectedRows.length}개 선택`}
              color="primary"
              onDelete={() => setSelectedRows([])}
              deleteIcon={<Close />}
            />
          )}

          <Box sx={{ flexGrow: 1 }} />

          {selectedRows.length > 0 && (
            <Button
              variant="contained"
              color="primary"
              startIcon={<FilterList />}
              onClick={() => handleDialogOpen('bulkActions')}
            >
              일괄 작업
            </Button>
          )}

          <IconButton onClick={handleMenuOpen}>
            <MoreVert />
          </IconButton>
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={handleMenuClose}
          >
            <MenuItem onClick={() => handleDialogOpen('importExport')}>
              <ListItemIcon><FileDownload /></ListItemIcon>
              <ListItemText>내보내기</ListItemText>
            </MenuItem>
            <MenuItem onClick={() => handleDialogOpen('platformSync')}>
              <ListItemIcon><Sync /></ListItemIcon>
              <ListItemText>플랫폼 동기화</ListItemText>
            </MenuItem>
          </Menu>
        </Box>
      </Paper>

      {/* Product Grid 또는 Empty State */}
      {filteredProducts.length === 0 ? (
        products.length === 0 ? (
          // 완전히 비어있는 경우 - 신규 사용자
          <ProductsEmptyState
            onAddProduct={() => handleDialogOpen('form')}
            onImport={() => handleDialogOpen('importExport')}
          />
        ) : (
          // 필터링 결과가 없는 경우
          <Paper sx={{ p: 8 }}>
            <EmptyState
              icon={<Search />}
              title="검색 결과가 없습니다"
              description="다른 검색어를 시도하거나 필터를 초기화해보세요."
              action={
                <Button
                  variant="outlined"
                  onClick={() => {
                    setSearchQuery('')
                    setLocalFilters({
                      category: [],
                      status: [],
                      priceRange: [0, 1000000],
                      stock: [],
                      platform: [],
                    })
                  }}
                >
                  필터 초기화
                </Button>
              }
              variant="compact"
            />
          </Paper>
        )
      ) : viewMode === 'grid' ? (
        // 그리드 보기
        <Grid container spacing={2}>
          <AnimatePresence mode="popLayout">
            {filteredProducts.map((product: Product, index: number) => (
              <Grid item xs={12} sm={6} md={4} lg={3} key={product.id}>
                <motion.div
                  layout
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ duration: 0.2, delay: index * 0.02 }}
                  whileHover={{ y: -4 }}
                >
                  <MuiCard
                    sx={{
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      position: 'relative',
                      overflow: 'visible',
                      cursor: 'pointer',
                      '&:hover': {
                        boxShadow: theme.shadows[8],
                        '& .product-actions': {
                          opacity: 1,
                        },
                      },
                    }}
                    onClick={() => handlePreview(product)}
                  >
                    {/* 상품 이미지 */}
                    <Box sx={{ position: 'relative', paddingTop: '100%' }}>
                      {product.main_image_url ? (
                        <CardMedia
                          component="img"
                          image={product.main_image_url}
                          alt={product.name}
                          sx={{
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            width: '100%',
                            height: '100%',
                            objectFit: 'cover',
                          }}
                        />
                      ) : (
                        <Box
                          sx={{
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            width: '100%',
                            height: '100%',
                            bgcolor: 'grey.200',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          <Inventory sx={{ fontSize: 60, color: 'grey.400' }} />
                        </Box>
                      )}
                      
                      {/* 상태 배지 */}
                      <Box sx={{ position: 'absolute', top: 8, left: 8, display: 'flex', gap: 0.5, flexDirection: 'column' }}>
                        {product.status === 'out_of_stock' && (
                          <Chip label="품절" size="small" color="error" />
                        )}
                        {(product.stock_quantity || 0) < 10 && (product.stock_quantity || 0) > 0 && (
                          <Chip label="재고 부족" size="small" color="warning" />
                        )}
                      </Box>

                      {/* 빠른 작업 버튼 */}
                      <Box
                        className="product-actions"
                        sx={{
                          position: 'absolute',
                          top: 8,
                          right: 8,
                          display: 'flex',
                          gap: 0.5,
                          opacity: 0,
                          transition: 'opacity 0.2s',
                        }}
                      >
                        <IconButton
                          size="small"
                          sx={{ bgcolor: 'background.paper' }}
                          onClick={(e) => {
                            e.stopPropagation()
                            handlePreview(product)
                          }}
                        >
                          <Visibility fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          sx={{ bgcolor: 'background.paper' }}
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDialogOpen('form', product)
                          }}
                        >
                          <Edit fontSize="small" />
                        </IconButton>
                      </Box>
                    </Box>

                    <CardContent sx={{ flex: 1 }}>
                      <Typography variant="body1" fontWeight="bold" gutterBottom noWrap>
                        {product.name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        {product.sku || 'SKU 없음'}
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                        <Typography variant="h6" color="primary">
                          ₩{formatNumber(product.price)}
                        </Typography>
                        {product.cost && (
                          <Chip
                            label={`마진 ${(((product.price - product.cost) / product.price) * 100).toFixed(0)}%`}
                            size="small"
                            color="success"
                            variant="outlined"
                          />
                        )}
                      </Box>
                    </CardContent>

                    <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Checkbox
                          checked={selectedRows.includes(product.id)}
                          onChange={(e) => {
                            e.stopPropagation()
                            handleSelectRow(product)
                          }}
                          onClick={(e) => e.stopPropagation()}
                        />
                        <Typography variant="caption" color="text.secondary">
                          재고: {formatNumber(product.stock_quantity || 0)}
                        </Typography>
                      </Box>
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteProduct(product)
                        }}
                        color="error"
                      >
                        <Delete fontSize="small" />
                      </IconButton>
                    </CardActions>
                  </MuiCard>
                </motion.div>
              </Grid>
            ))}
          </AnimatePresence>
        </Grid>
      ) : (
        // 리스트 보기 (테이블)
        <Paper sx={{ height: 600 }}>
          <DataGrid
            rows={filteredProducts}
            columns={columns}
            checkboxSelection
            disableRowSelectionOnClick
            rowSelectionModel={selectedRows}
            onRowSelectionModelChange={setSelectedRows}
            pageSizeOptions={[10, 25, 50, 100]}
            initialState={{
              pagination: { paginationModel: { pageSize: 25 } },
            }}
            onRowDoubleClick={(params) => handlePreview(params.row)}
            sx={{
              '& .MuiDataGrid-cell:hover': {
                cursor: 'pointer',
              },
            }}
          />
        </Paper>
      )}

      {/* 필터 사이드바 */}
      <Drawer
        anchor="right"
        open={filterDrawerOpen}
        onClose={() => setFilterDrawerOpen(false)}
        sx={{
          '& .MuiDrawer-paper': {
            width: 320,
          },
        }}
      >
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h6">필터 설정</Typography>
        </Box>
        <FilterPanel
          filters={filterGroups}
          onChange={handleFilterChange}
          onReset={() => {
            setLocalFilters({
              category: [],
              status: [],
              priceRange: [0, 1000000],
              stock: [],
              platform: [],
            })
          }}
          defaultExpanded={['category', 'status']}
        />
      </Drawer>

      {/* Speed Dial */}
      <QuickActions
        actions={[
          {
            id: 'add',
            icon: <Add />,
            name: '상품 추가',
            action: () => handleDialogOpen('form'),
            color: 'primary',
            shortcut: 'cmd+n',
          },
          {
            id: 'import',
            icon: <FileUpload />,
            name: '가져오기',
            action: () => handleDialogOpen('importExport'),
          },
          {
            id: 'sync',
            icon: <Sync />,
            name: '플랫폼 동기화',
            action: () => handleDialogOpen('platformSync'),
            badge: 3,
          },
        ]}
        variant="speedDial"
      />

      {/* Dialogs */}
      <ProductFormDialog
        open={dialogState.form}
        onClose={() => handleDialogClose('form')}
        product={selectedProduct}
      />
      <ProductDetailDialog
        open={dialogState.detail}
        onClose={() => handleDialogClose('detail')}
        product={selectedProduct}
      />
      <BulkActionsDialog
        open={dialogState.bulkActions}
        onClose={() => handleDialogClose('bulkActions')}
        selectedProducts={products.filter((p: Product) => selectedRows.includes(p.id)) as any}
      />
      <ImportExportDialog
        open={dialogState.importExport}
        onClose={() => handleDialogClose('importExport')}
      />
      <PlatformSyncDialog
        open={dialogState.platformSync}
        onClose={() => handleDialogClose('platformSync')}
      />
      
      {/* 상품 미리보기 다이얼로그 */}
      <Dialog
        open={dialogState.preview}
        onClose={() => handleDialogClose('preview')}
        maxWidth="md"
        fullWidth
        TransitionComponent={Zoom}
      >
        {previewProduct && (
          <>
            <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="h6">{previewProduct.name}</Typography>
              <IconButton onClick={() => handleDialogClose('preview')}>
                <Close />
              </IconButton>
            </DialogTitle>
            <DialogContent dividers>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  {previewProduct.main_image_url ? (
                    <Box
                      component="img"
                      src={previewProduct.main_image_url}
                      alt={previewProduct.name}
                      sx={{
                        width: '100%',
                        height: 400,
                        objectFit: 'cover',
                        borderRadius: 1,
                      }}
                    />
                  ) : (
                    <Box
                      sx={{
                        width: '100%',
                        height: 400,
                        bgcolor: 'grey.200',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        borderRadius: 1,
                      }}
                    >
                      <Inventory sx={{ fontSize: 100, color: 'grey.400' }} />
                    </Box>
                  )}
                </Grid>
                <Grid item xs={12} md={6}>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <Box>
                      <Typography variant="caption" color="text.secondary">SKU</Typography>
                      <Typography variant="body1">{previewProduct.sku || '-'}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">카테고리</Typography>
                      <Typography variant="body1">
                        <Chip
                          label={previewProduct.category || '미분류'}
                          size="small"
                          icon={<Category />}
                        />
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">가격</Typography>
                      <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 2 }}>
                        <Typography variant="h5" color="primary">
                          ₩{formatNumber(previewProduct.price)}
                        </Typography>
                        {previewProduct.cost && (
                          <>
                            <Typography variant="body2" color="text.secondary">
                              (원가: ₩{formatNumber(previewProduct.cost)})
                            </Typography>
                            <Chip
                              label={`마진 ${(((previewProduct.price - previewProduct.cost) / previewProduct.price) * 100).toFixed(0)}%`}
                              size="small"
                              color="success"
                            />
                          </>
                        )}
                      </Box>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">재고</Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="h6">
                          {formatNumber(previewProduct.stock_quantity || 0)}개
                        </Typography>
                        {(previewProduct.stock_quantity || 0) === 0 && (
                          <Chip label="품절" size="small" color="error" />
                        )}
                        {(previewProduct.stock_quantity || 0) > 0 && (previewProduct.stock_quantity || 0) < 10 && (
                          <Chip label="재고 부족" size="small" color="warning" />
                        )}
                      </Box>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">상태</Typography>
                      <Typography variant="body1">
                        <Chip
                          label={
                            previewProduct.status === 'active' ? '판매중' :
                            previewProduct.status === 'inactive' ? '판매중지' :
                            previewProduct.status === 'out_of_stock' ? '품절' : '단종'
                          }
                          size="small"
                          color={
                            previewProduct.status === 'active' ? 'success' :
                            previewProduct.status === 'inactive' ? 'warning' :
                            'error'
                          }
                        />
                      </Typography>
                    </Box>
                    {previewProduct.description && (
                      <Box>
                        <Typography variant="caption" color="text.secondary">설명</Typography>
                        <Typography variant="body2">{previewProduct.description}</Typography>
                      </Box>
                    )}
                  </Box>
                </Grid>
              </Grid>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => handleDialogClose('preview')}>닫기</Button>
              <Button
                variant="outlined"
                startIcon={<Edit />}
                onClick={() => {
                  handleDialogClose('preview')
                  handleDialogOpen('form', previewProduct)
                }}
              >
                수정
              </Button>
              <Button
                variant="contained"
                startIcon={<Analytics />}
                onClick={() => {
                  handleDialogClose('preview')
                  handleDialogOpen('detail', previewProduct)
                }}
              >
                상세보기
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  )
}

export default Products