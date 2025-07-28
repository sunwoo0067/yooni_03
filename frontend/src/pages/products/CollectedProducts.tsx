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
  Tooltip,
  Badge,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Skeleton,
  useTheme,
  alpha,
  Fade,
  Card,
  CardContent,
  CardMedia,
  CardActions,
  Checkbox,
  Avatar,
  Stack,
  Alert,
  LinearProgress,
} from '@mui/material'
import {
  DataGrid,
  GridColDef,
  GridRowSelectionModel,
  GridActionsCellItem,
  GridRenderCellParams,
  GridValueGetterParams,
} from '@mui/x-data-grid'
import {
  Search,
  FilterList,
  MoreVert,
  CheckCircle,
  Cancel,
  Visibility,
  Store,
  Schedule,
  TrendingUp,
  Warning,
  Refresh,
  FileDownload,
  Delete,
  Edit,
  Check,
  Close,
  LocalShipping,
  Inventory,
} from '@mui/icons-material'
import { DatePicker } from '@mui/x-date-pickers/DatePicker'
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider'
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns'
import { ko } from 'date-fns/locale'
import { format } from 'date-fns'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'react-hot-toast'
import { formatCurrency, formatNumber } from '@utils/format'
import api, { collectedProductsAPI } from '@services/api'

// Types
interface CollectedProduct {
  id: string
  wholesaler_id: string
  wholesaler_name: string
  wholesaler_logo?: string
  product_name: string
  product_code: string
  description?: string
  category?: string
  price: number
  wholesale_price: number
  stock_quantity: number
  min_order_quantity?: number
  image_url?: string
  collection_date: string
  status: 'pending' | 'approved' | 'rejected' | 'listed'
  rejection_reason?: string
  margin_percentage?: number
  competitor_price?: number
  market_demand?: 'high' | 'medium' | 'low'
  tags?: string[]
  created_at: string
  updated_at: string
}

interface CollectedProductsFilters {
  search?: string
  wholesaler_id?: string
  status?: string
  date_from?: Date | null
  date_to?: Date | null
  category?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

interface WholesalerInfo {
  id: string
  name: string
  logo?: string
  product_count: number
}

const CollectedProducts: React.FC = () => {
  const theme = useTheme()
  const queryClient = useQueryClient()

  // States
  const [filters, setFilters] = useState<CollectedProductsFilters>({
    search: '',
    status: 'all',
    date_from: null,
    date_to: null,
    sort_by: 'collection_date',
    sort_order: 'desc',
  })
  const [selectedRows, setSelectedRows] = useState<GridRowSelectionModel>([])
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [detailDialog, setDetailDialog] = useState<{
    open: boolean
    product: CollectedProduct | null
  }>({ open: false, product: null })
  const [bulkActionDialog, setBulkActionDialog] = useState(false)

  // API Queries
  const { data: productsData, isLoading, refetch } = useQuery({
    queryKey: ['collected-products', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.search) params.append('search', filters.search)
      if (filters.wholesaler_id && filters.wholesaler_id !== 'all') {
        params.append('wholesaler_id', filters.wholesaler_id)
      }
      if (filters.status && filters.status !== 'all') {
        params.append('status', filters.status)
      }
      if (filters.date_from) {
        params.append('date_from', format(filters.date_from, 'yyyy-MM-dd'))
      }
      if (filters.date_to) {
        params.append('date_to', format(filters.date_to, 'yyyy-MM-dd'))
      }
      if (filters.category && filters.category !== 'all') {
        params.append('category', filters.category)
      }
      params.append('sort_by', filters.sort_by || 'collection_date')
      params.append('sort_order', filters.sort_order || 'desc')

      const response = await collectedProductsAPI.getProducts({ supplier: filters.wholesaler || undefined })
      // Simple Collector API 응답을 CollectedProduct 형식으로 변환
      const products = response.data.map((p: any) => ({
        id: p.product_code,
        wholesaler_id: p.supplier,
        wholesaler_name: p.supplier_name || p.supplier,
        product_name: p.product_name,
        product_code: p.product_code,
        description: p.description,
        category: p.category,
        price: p.sell_price || p.supply_price * 1.3,
        wholesale_price: p.supply_price,
        stock_quantity: p.stock_quantity || 0,
        min_order_quantity: p.moq || 1,
        image_url: p.main_image_url,
        collection_date: p.created_at,
        status: 'pending',
        margin_percentage: ((p.sell_price - p.supply_price) / p.supply_price * 100) || 30,
        created_at: p.created_at,
        updated_at: p.updated_at,
      }))
      return { items: products, total: products.length }
    },
  })

  const { data: wholesalersData } = useQuery({
    queryKey: ['wholesalers-info'],
    queryFn: async () => {
      const response = await api.get('http://localhost:8000/suppliers')
      // Simple Collector API 형식 변환
      return response.data.filter((s: any) => !s.api_config?.marketplace).map((s: any) => ({
        id: s.supplier_code,
        name: s.supplier_name,
        logo: null,
      }))
    },
  })

  // Mutations
  const approveProductMutation = useMutation({
    mutationFn: async (productIds: string[]) => {
      const response = await api.post('/products/collected/approve', {
        product_ids: productIds,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collected-products'] })
      toast.success('상품이 승인되었습니다.')
      setSelectedRows([])
    },
    onError: () => {
      toast.error('상품 승인 중 오류가 발생했습니다.')
    },
  })

  const rejectProductMutation = useMutation({
    mutationFn: async ({ productIds, reason }: { productIds: string[]; reason: string }) => {
      const response = await api.post('/products/collected/reject', {
        product_ids: productIds,
        rejection_reason: reason,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collected-products'] })
      toast.success('상품이 거부되었습니다.')
      setSelectedRows([])
    },
    onError: () => {
      toast.error('상품 거부 중 오류가 발생했습니다.')
    },
  })

  const deleteProductMutation = useMutation({
    mutationFn: async (productIds: string[]) => {
      const response = await api.post('/products/collected/delete', {
        product_ids: productIds,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collected-products'] })
      toast.success('상품이 삭제되었습니다.')
      setSelectedRows([])
    },
    onError: () => {
      toast.error('상품 삭제 중 오류가 발생했습니다.')
    },
  })

  const collectedProducts = productsData?.products || []
  const statistics = productsData?.statistics || {
    total: 0,
    pending: 0,
    approved: 0,
    rejected: 0,
    listed: 0,
  }
  const wholesalers = wholesalersData?.wholesalers || []

  // Handlers
  const handleFilterChange = useCallback((key: keyof CollectedProductsFilters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }, [])

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
  }

  const handleApproveSelected = () => {
    const selectedIds = selectedRows as string[]
    if (selectedIds.length > 0) {
      approveProductMutation.mutate(selectedIds)
    }
  }

  const handleRejectSelected = () => {
    const selectedIds = selectedRows as string[]
    if (selectedIds.length > 0) {
      const reason = window.prompt('거부 사유를 입력하세요:')
      if (reason) {
        rejectProductMutation.mutate({ productIds: selectedIds, reason })
      }
    }
  }

  const handleDeleteSelected = () => {
    const selectedIds = selectedRows as string[]
    if (selectedIds.length > 0 && window.confirm('선택한 상품을 삭제하시겠습니까?')) {
      deleteProductMutation.mutate(selectedIds)
    }
  }

  const handleExport = async () => {
    try {
      const response = await api.get('/products/collected/export', {
        responseType: 'blob',
      })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `collected_products_${format(new Date(), 'yyyyMMdd')}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      toast.success('파일이 다운로드되었습니다.')
    } catch (error) {
      toast.error('파일 다운로드 중 오류가 발생했습니다.')
    }
  }

  // DataGrid columns
  const columns: GridColDef[] = [
    {
      field: 'product_name',
      headerName: '상품명',
      flex: 1,
      minWidth: 250,
      renderCell: (params: GridRenderCellParams) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {params.row.image_url ? (
            <Avatar
              src={params.row.image_url}
              variant="rounded"
              sx={{ width: 48, height: 48 }}
            />
          ) : (
            <Avatar variant="rounded" sx={{ width: 48, height: 48, bgcolor: 'grey.300' }}>
              <Inventory />
            </Avatar>
          )}
          <Box>
            <Typography variant="body2" fontWeight={500}>
              {params.row.product_name}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {params.row.product_code}
            </Typography>
          </Box>
        </Box>
      ),
    },
    {
      field: 'wholesaler_name',
      headerName: '도매처',
      width: 150,
      renderCell: (params: GridRenderCellParams) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {params.row.wholesaler_logo && (
            <Avatar src={params.row.wholesaler_logo} sx={{ width: 24, height: 24 }} />
          )}
          <Typography variant="body2">{params.row.wholesaler_name}</Typography>
        </Box>
      ),
    },
    {
      field: 'wholesale_price',
      headerName: '도매가',
      width: 120,
      align: 'right',
      headerAlign: 'right',
      valueFormatter: (params) => formatCurrency(params.value),
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
      field: 'margin_percentage',
      headerName: '마진율',
      width: 100,
      align: 'center',
      headerAlign: 'center',
      renderCell: (params: GridRenderCellParams) => {
        const margin = params.value || 
          ((params.row.price - params.row.wholesale_price) / params.row.price * 100)
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
      align: 'center',
      headerAlign: 'center',
      renderCell: (params: GridRenderCellParams) => {
        const stock = params.value || 0
        return (
          <Chip
            label={formatNumber(stock)}
            size="small"
            color={stock > 50 ? 'success' : stock > 10 ? 'warning' : 'error'}
            icon={stock === 0 ? <Cancel fontSize="small" /> : undefined}
          />
        )
      },
    },
    {
      field: 'market_demand',
      headerName: '시장 수요',
      width: 100,
      align: 'center',
      headerAlign: 'center',
      renderCell: (params: GridRenderCellParams) => {
        const demandConfig = {
          high: { label: '높음', color: 'success' as const, icon: <TrendingUp /> },
          medium: { label: '보통', color: 'warning' as const },
          low: { label: '낮음', color: 'default' as const },
        }
        const config = demandConfig[params.value as keyof typeof demandConfig] || demandConfig.medium
        return (
          <Chip
            label={config.label}
            size="small"
            color={config.color}
            icon={config.icon}
          />
        )
      },
    },
    {
      field: 'collection_date',
      headerName: '수집일',
      width: 120,
      valueFormatter: (params) => format(new Date(params.value), 'yyyy-MM-dd'),
    },
    {
      field: 'status',
      headerName: '상태',
      width: 120,
      renderCell: (params: GridRenderCellParams) => {
        const statusConfig = {
          pending: { label: '검토중', color: 'warning' as const, icon: <Schedule /> },
          approved: { label: '승인됨', color: 'success' as const, icon: <CheckCircle /> },
          rejected: { label: '거부됨', color: 'error' as const, icon: <Cancel /> },
          listed: { label: '등록됨', color: 'info' as const, icon: <Store /> },
        }
        const config = statusConfig[params.value as keyof typeof statusConfig]
        return (
          <Chip
            label={config.label}
            size="small"
            color={config.color}
            icon={config.icon}
          />
        )
      },
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: '작업',
      width: 100,
      getActions: (params) => {
        const actions = [
          <GridActionsCellItem
            icon={<Visibility />}
            label="상세보기"
            onClick={() => setDetailDialog({ open: true, product: params.row })}
          />,
        ]

        if (params.row.status === 'pending') {
          actions.push(
            <GridActionsCellItem
              icon={<Check />}
              label="승인"
              onClick={() => approveProductMutation.mutate([params.row.id])}
              color="success"
            />,
            <GridActionsCellItem
              icon={<Close />}
              label="거부"
              onClick={() => {
                const reason = window.prompt('거부 사유를 입력하세요:')
                if (reason) {
                  rejectProductMutation.mutate({ productIds: [params.row.id], reason })
                }
              }}
              color="error"
            />
          )
        }

        return actions
      },
    },
  ]

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={ko}>
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h4" gutterBottom>
            수집된 상품
          </Typography>
          <Typography variant="body1" color="text.secondary">
            도매처에서 수집된 상품을 검토하고 승인하세요
          </Typography>
        </Box>

        {/* Statistics Cards */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={2.4}>
            <Card>
              <CardContent>
                <Stack spacing={1}>
                  <Typography variant="body2" color="text.secondary">
                    전체 수집
                  </Typography>
                  <Typography variant="h4">{formatNumber(statistics.total)}</Typography>
                  <Chip label="전체" size="small" />
                </Stack>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={2.4}>
            <Card>
              <CardContent>
                <Stack spacing={1}>
                  <Typography variant="body2" color="text.secondary">
                    검토 대기
                  </Typography>
                  <Typography variant="h4" color="warning.main">
                    {formatNumber(statistics.pending)}
                  </Typography>
                  <Chip label="검토중" size="small" color="warning" />
                </Stack>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={2.4}>
            <Card>
              <CardContent>
                <Stack spacing={1}>
                  <Typography variant="body2" color="text.secondary">
                    승인됨
                  </Typography>
                  <Typography variant="h4" color="success.main">
                    {formatNumber(statistics.approved)}
                  </Typography>
                  <Chip label="승인" size="small" color="success" />
                </Stack>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={2.4}>
            <Card>
              <CardContent>
                <Stack spacing={1}>
                  <Typography variant="body2" color="text.secondary">
                    거부됨
                  </Typography>
                  <Typography variant="h4" color="error.main">
                    {formatNumber(statistics.rejected)}
                  </Typography>
                  <Chip label="거부" size="small" color="error" />
                </Stack>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={2.4}>
            <Card>
              <CardContent>
                <Stack spacing={1}>
                  <Typography variant="body2" color="text.secondary">
                    등록됨
                  </Typography>
                  <Typography variant="h4" color="info.main">
                    {formatNumber(statistics.listed)}
                  </Typography>
                  <Chip label="등록" size="small" color="info" />
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Filters */}
        <Paper sx={{ p: 2, mb: 3 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                placeholder="상품명, 코드로 검색..."
                value={filters.search}
                onChange={(e) => handleFilterChange('search', e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search />
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>
            <Grid item xs={12} md={2}>
              <FormControl fullWidth>
                <Select
                  value={filters.wholesaler_id || 'all'}
                  onChange={(e) => handleFilterChange('wholesaler_id', e.target.value)}
                >
                  <MenuItem value="all">모든 도매처</MenuItem>
                  {wholesalers.map((wholesaler: WholesalerInfo) => (
                    <MenuItem key={wholesaler.id} value={wholesaler.id}>
                      {wholesaler.name} ({wholesaler.product_count})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={2}>
              <FormControl fullWidth>
                <Select
                  value={filters.status || 'all'}
                  onChange={(e) => handleFilterChange('status', e.target.value)}
                >
                  <MenuItem value="all">모든 상태</MenuItem>
                  <MenuItem value="pending">검토중</MenuItem>
                  <MenuItem value="approved">승인됨</MenuItem>
                  <MenuItem value="rejected">거부됨</MenuItem>
                  <MenuItem value="listed">등록됨</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={2}>
              <DatePicker
                label="시작일"
                value={filters.date_from}
                onChange={(date) => handleFilterChange('date_from', date)}
                slotProps={{ textField: { fullWidth: true } }}
              />
            </Grid>
            <Grid item xs={12} md={2}>
              <DatePicker
                label="종료일"
                value={filters.date_to}
                onChange={(date) => handleFilterChange('date_to', date)}
                slotProps={{ textField: { fullWidth: true } }}
              />
            </Grid>
            <Grid item xs={12} md={1}>
              <Tooltip title="새로고침">
                <IconButton onClick={() => refetch()}>
                  <Refresh />
                </IconButton>
              </Tooltip>
              <Tooltip title="더보기">
                <IconButton onClick={handleMenuOpen}>
                  <MoreVert />
                </IconButton>
              </Tooltip>
              <Menu
                anchorEl={anchorEl}
                open={Boolean(anchorEl)}
                onClose={handleMenuClose}
              >
                <MenuItem onClick={handleExport}>
                  <FileDownload sx={{ mr: 1 }} /> 내보내기
                </MenuItem>
              </Menu>
            </Grid>
          </Grid>

          {/* Bulk Actions */}
          {selectedRows.length > 0 && (
            <Box sx={{ mt: 2, display: 'flex', gap: 1, alignItems: 'center' }}>
              <Chip
                label={`${selectedRows.length}개 선택`}
                color="primary"
                onDelete={() => setSelectedRows([])}
              />
              <Button
                variant="contained"
                color="success"
                startIcon={<Check />}
                onClick={handleApproveSelected}
                disabled={approveProductMutation.isPending}
              >
                일괄 승인
              </Button>
              <Button
                variant="outlined"
                color="error"
                startIcon={<Close />}
                onClick={handleRejectSelected}
                disabled={rejectProductMutation.isPending}
              >
                일괄 거부
              </Button>
              <Button
                variant="outlined"
                color="error"
                startIcon={<Delete />}
                onClick={handleDeleteSelected}
                disabled={deleteProductMutation.isPending}
              >
                삭제
              </Button>
            </Box>
          )}
        </Paper>

        {/* Loading */}
        {isLoading && <LinearProgress sx={{ mb: 2 }} />}

        {/* Data Grid */}
        {!isLoading && collectedProducts.length === 0 ? (
          <Paper sx={{ p: 8, textAlign: 'center' }}>
            <Store sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              수집된 상품이 없습니다
            </Typography>
            <Typography variant="body2" color="text.secondary">
              도매처에서 상품을 수집하거나 수집 일정을 설정하세요
            </Typography>
          </Paper>
        ) : (
          <Paper sx={{ height: 600 }}>
            <DataGrid
              rows={collectedProducts}
              columns={columns}
              pageSizeOptions={[10, 25, 50]}
              checkboxSelection
              disableRowSelectionOnClick
              rowSelectionModel={selectedRows}
              onRowSelectionModelChange={setSelectedRows}
              loading={isLoading}
              sx={{
                '& .MuiDataGrid-row:hover': {
                  backgroundColor: alpha(theme.palette.primary.main, 0.04),
                },
              }}
            />
          </Paper>
        )}

        {/* Product Detail Dialog */}
        <Dialog
          open={detailDialog.open}
          onClose={() => setDetailDialog({ open: false, product: null })}
          maxWidth="md"
          fullWidth
        >
          {detailDialog.product && (
            <>
              <DialogTitle>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="h6">{detailDialog.product.product_name}</Typography>
                  <IconButton onClick={() => setDetailDialog({ open: false, product: null })}>
                    <Close />
                  </IconButton>
                </Box>
              </DialogTitle>
              <DialogContent dividers>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    {detailDialog.product.image_url ? (
                      <Box
                        component="img"
                        src={detailDialog.product.image_url}
                        alt={detailDialog.product.product_name}
                        sx={{
                          width: '100%',
                          height: 300,
                          objectFit: 'contain',
                          borderRadius: 1,
                          bgcolor: 'grey.100',
                        }}
                      />
                    ) : (
                      <Box
                        sx={{
                          width: '100%',
                          height: 300,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          bgcolor: 'grey.100',
                          borderRadius: 1,
                        }}
                      >
                        <Inventory sx={{ fontSize: 80, color: 'grey.400' }} />
                      </Box>
                    )}
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Stack spacing={2}>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          상품 코드
                        </Typography>
                        <Typography variant="body1">
                          {detailDialog.product.product_code}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          도매처
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {detailDialog.product.wholesaler_logo && (
                            <Avatar
                              src={detailDialog.product.wholesaler_logo}
                              sx={{ width: 24, height: 24 }}
                            />
                          )}
                          <Typography variant="body1">
                            {detailDialog.product.wholesaler_name}
                          </Typography>
                        </Box>
                      </Box>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          가격 정보
                        </Typography>
                        <Box sx={{ pl: 2 }}>
                          <Typography variant="body2">
                            도매가: {formatCurrency(detailDialog.product.wholesale_price)}
                          </Typography>
                          <Typography variant="body2">
                            판매가: {formatCurrency(detailDialog.product.price)}
                          </Typography>
                          <Typography variant="body2" color="success.main">
                            마진율: {detailDialog.product.margin_percentage || 
                              ((detailDialog.product.price - detailDialog.product.wholesale_price) / 
                                detailDialog.product.price * 100).toFixed(1)}%
                          </Typography>
                        </Box>
                      </Box>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          재고
                        </Typography>
                        <Typography variant="body1">
                          {formatNumber(detailDialog.product.stock_quantity)}개
                        </Typography>
                      </Box>
                      {detailDialog.product.min_order_quantity && (
                        <Box>
                          <Typography variant="caption" color="text.secondary">
                            최소 주문 수량
                          </Typography>
                          <Typography variant="body1">
                            {formatNumber(detailDialog.product.min_order_quantity)}개
                          </Typography>
                        </Box>
                      )}
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          수집일
                        </Typography>
                        <Typography variant="body1">
                          {format(new Date(detailDialog.product.collection_date), 'yyyy-MM-dd HH:mm')}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          상태
                        </Typography>
                        <Box sx={{ mt: 0.5 }}>
                          {detailDialog.product.status === 'pending' && (
                            <Chip label="검토중" color="warning" icon={<Schedule />} />
                          )}
                          {detailDialog.product.status === 'approved' && (
                            <Chip label="승인됨" color="success" icon={<CheckCircle />} />
                          )}
                          {detailDialog.product.status === 'rejected' && (
                            <Chip label="거부됨" color="error" icon={<Cancel />} />
                          )}
                          {detailDialog.product.status === 'listed' && (
                            <Chip label="등록됨" color="info" icon={<Store />} />
                          )}
                        </Box>
                      </Box>
                      {detailDialog.product.rejection_reason && (
                        <Alert severity="error">
                          <Typography variant="body2">
                            거부 사유: {detailDialog.product.rejection_reason}
                          </Typography>
                        </Alert>
                      )}
                    </Stack>
                  </Grid>
                  {detailDialog.product.description && (
                    <Grid item xs={12}>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          상품 설명
                        </Typography>
                        <Typography variant="body2" sx={{ mt: 1 }}>
                          {detailDialog.product.description}
                        </Typography>
                      </Box>
                    </Grid>
                  )}
                </Grid>
              </DialogContent>
              <DialogActions>
                <Button onClick={() => setDetailDialog({ open: false, product: null })}>
                  닫기
                </Button>
                {detailDialog.product.status === 'pending' && (
                  <>
                    <Button
                      variant="outlined"
                      color="error"
                      startIcon={<Close />}
                      onClick={() => {
                        const reason = window.prompt('거부 사유를 입력하세요:')
                        if (reason) {
                          rejectProductMutation.mutate({
                            productIds: [detailDialog.product!.id],
                            reason,
                          })
                          setDetailDialog({ open: false, product: null })
                        }
                      }}
                    >
                      거부
                    </Button>
                    <Button
                      variant="contained"
                      color="success"
                      startIcon={<Check />}
                      onClick={() => {
                        approveProductMutation.mutate([detailDialog.product!.id])
                        setDetailDialog({ open: false, product: null })
                      }}
                    >
                      승인
                    </Button>
                  </>
                )}
              </DialogActions>
            </>
          )}
        </Dialog>
      </Box>
    </LocalizationProvider>
  )
}

export default CollectedProducts