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
  Card,
  CardContent,
  Tabs,
  Tab,
  Badge,
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
  FilterList,
  MoreVert,
  Visibility,
  Print,
  LocalShipping,
  CheckCircle,
  Cancel,
  AccessTime,
  ShoppingCart,
  TrendingUp,
  AttachMoney,
  Inventory,
  CalendarToday,
  Download,
  Email,
  WhatsApp,
} from '@mui/icons-material'
import { formatCurrency, formatNumber, formatDate } from '@utils/format'
import { toast } from 'react-hot-toast'
import OrderDetailDialog from './OrderDetailDialog'
import BulkOrderActionsDialog from './BulkOrderActionsDialog'
import ShippingDialog from './ShippingDialog'
import EmptyState, { OrdersEmptyState } from '@components/ui/EmptyState'
import { PageSkeleton } from '@components/ui/Skeleton'
import { useNavigate } from 'react-router-dom'

interface Order {
  id: string
  orderNumber: string
  customer: {
    name: string
    email: string
    phone: string
  }
  items: Array<{
    productId: string
    productName: string
    sku: string
    quantity: number
    price: number
    subtotal: number
  }>
  totalAmount: number
  status: 'pending' | 'confirmed' | 'processing' | 'shipped' | 'delivered' | 'cancelled' | 'refunded'
  paymentStatus: 'pending' | 'paid' | 'failed' | 'refunded'
  paymentMethod: string
  platform: string
  platformOrderId: string
  shippingAddress: {
    street: string
    city: string
    state: string
    zipCode: string
  }
  trackingNumber?: string
  shippingCarrier?: string
  orderDate: string
  shippedDate?: string
  deliveredDate?: string
  notes?: string
}

const Orders: React.FC = () => {
  const navigate = useNavigate()
  
  // States
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedRows, setSelectedRows] = useState<GridRowSelectionModel>([])
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null)
  const [tabValue, setTabValue] = useState(0)
  const [dialogState, setDialogState] = useState({
    detail: false,
    bulkActions: false,
    shipping: false,
  })
  const [filters, setFilters] = useState({
    status: 'all',
    platform: 'all',
    dateRange: 'all',
    paymentStatus: 'all',
  })

  // Mock data
  React.useEffect(() => {
    const mockOrders: Order[] = [
      {
        id: '1',
        orderNumber: 'ORD-2024-001',
        customer: {
          name: '홍길동',
          email: 'hong@example.com',
          phone: '010-1234-5678',
        },
        items: [
          {
            productId: '1',
            productName: '무선 이어폰 프로',
            sku: 'WEP-001',
            quantity: 2,
            price: 89000,
            subtotal: 178000,
          },
        ],
        totalAmount: 178000,
        status: 'pending',
        paymentStatus: 'paid',
        paymentMethod: '신용카드',
        platform: '쿠팡',
        platformOrderId: 'CP-123456',
        shippingAddress: {
          street: '강남대로 123',
          city: '서울특별시',
          state: '강남구',
          zipCode: '06123',
        },
        orderDate: '2024-01-20T10:30:00',
      },
      {
        id: '2',
        orderNumber: 'ORD-2024-002',
        customer: {
          name: '김철수',
          email: 'kim@example.com',
          phone: '010-2345-6789',
        },
        items: [
          {
            productId: '2',
            productName: '스마트워치 울트라',
            sku: 'SW-002',
            quantity: 1,
            price: 450000,
            subtotal: 450000,
          },
          {
            productId: '3',
            productName: '충전 케이블 세트',
            sku: 'CC-003',
            quantity: 3,
            price: 15000,
            subtotal: 45000,
          },
        ],
        totalAmount: 495000,
        status: 'processing',
        paymentStatus: 'paid',
        paymentMethod: '네이버페이',
        platform: '네이버',
        platformOrderId: 'NV-789012',
        shippingAddress: {
          street: '테헤란로 456',
          city: '서울특별시',
          state: '강남구',
          zipCode: '06234',
        },
        orderDate: '2024-01-19T14:20:00',
        trackingNumber: 'CJ1234567890',
        shippingCarrier: 'CJ대한통운',
      },
    ]
    setOrders(mockOrders)
  }, [])

  // Handlers
  const handleSearch = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(event.target.value)
  }, [])

  const handleFilterChange = useCallback((filterType: string) => (event: SelectChangeEvent) => {
    setFilters(prev => ({
      ...prev,
      [filterType]: event.target.value,
    }))
  }, [])

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
  }

  const handleDialogOpen = (dialog: keyof typeof dialogState, order?: Order) => {
    if (order) {
      setSelectedOrder(order)
    }
    setDialogState(prev => ({ ...prev, [dialog]: true }))
    handleMenuClose()
  }

  const handleDialogClose = (dialog: keyof typeof dialogState) => {
    setDialogState(prev => ({ ...prev, [dialog]: false }))
    if (dialog !== 'detail') {
      setSelectedOrder(null)
    }
  }

  const handleStatusUpdate = async (order: Order, newStatus: Order['status']) => {
    // Simulate API call
    toast.success(`주문 ${order.orderNumber}의 상태가 업데이트되었습니다.`)
    setOrders(prev =>
      prev.map(o => (o.id === order.id ? { ...o, status: newStatus } : o))
    )
  }

  const handlePrintInvoice = (order: Order) => {
    toast.success('송장을 인쇄합니다.')
  }

  const handleExportOrders = () => {
    toast.success('주문 목록을 내보냅니다.')
  }

  // Filtered orders
  const filteredOrders = useMemo(() => {
    return orders.filter(order => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        if (
          !order.orderNumber.toLowerCase().includes(query) &&
          !order.customer.name.toLowerCase().includes(query) &&
          !order.customer.email.toLowerCase().includes(query)
        ) {
          return false
        }
      }

      // Status filter
      if (filters.status !== 'all' && order.status !== filters.status) {
        return false
      }

      // Platform filter
      if (filters.platform !== 'all' && order.platform !== filters.platform) {
        return false
      }

      // Payment status filter
      if (filters.paymentStatus !== 'all' && order.paymentStatus !== filters.paymentStatus) {
        return false
      }

      return true
    })
  }, [orders, searchQuery, filters])

  // Statistics
  const statistics = useMemo(() => {
    const total = orders.length
    const pending = orders.filter(o => o.status === 'pending').length
    const processing = orders.filter(o => o.status === 'processing').length
    const shipped = orders.filter(o => o.status === 'shipped').length
    const totalRevenue = orders.reduce((sum, o) => sum + o.totalAmount, 0)

    return { total, pending, processing, shipped, totalRevenue }
  }, [orders])

  // Tab counts
  const tabCounts = useMemo(() => {
    const all = orders.length
    const newOrders = orders.filter(o => o.status === 'pending').length
    const preparing = orders.filter(o => o.status === 'confirmed' || o.status === 'processing').length
    const shipping = orders.filter(o => o.status === 'shipped').length
    const completed = orders.filter(o => o.status === 'delivered').length
    const cancelled = orders.filter(o => o.status === 'cancelled' || o.status === 'refunded').length

    return { all, newOrders, preparing, shipping, completed, cancelled }
  }, [orders])

  // DataGrid columns
  const columns: GridColDef[] = [
    {
      field: 'orderNumber',
      headerName: '주문번호',
      width: 130,
      renderCell: (params: GridRenderCellParams) => (
        <Box>
          <Typography variant="body2" fontWeight={500}>
            {params.value}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {params.row.platform} • {params.row.platformOrderId}
          </Typography>
        </Box>
      ),
    },
    {
      field: 'orderDate',
      headerName: '주문일시',
      width: 150,
      valueFormatter: (params) => formatDate(params.value),
    },
    {
      field: 'customer',
      headerName: '고객',
      width: 180,
      renderCell: (params: GridRenderCellParams) => (
        <Box>
          <Typography variant="body2">{params.value.name}</Typography>
          <Typography variant="caption" color="text.secondary">
            {params.value.phone}
          </Typography>
        </Box>
      ),
    },
    {
      field: 'items',
      headerName: '상품',
      width: 250,
      renderCell: (params: GridRenderCellParams) => (
        <Box>
          <Typography variant="body2" noWrap>
            {params.value[0].productName}
            {params.value.length > 1 && ` 외 ${params.value.length - 1}개`}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            총 {params.value.reduce((sum: number, item: any) => sum + item.quantity, 0)}개
          </Typography>
        </Box>
      ),
    },
    {
      field: 'totalAmount',
      headerName: '주문금액',
      width: 120,
      align: 'right',
      headerAlign: 'right',
      valueFormatter: (params) => formatCurrency(params.value),
    },
    {
      field: 'status',
      headerName: '주문상태',
      width: 120,
      renderCell: (params: GridRenderCellParams) => {
        const statusConfig = {
          pending: { label: '주문확인', color: 'warning' as const, icon: <AccessTime /> },
          confirmed: { label: '주문확정', color: 'info' as const, icon: <CheckCircle /> },
          processing: { label: '상품준비', color: 'info' as const, icon: <Inventory /> },
          shipped: { label: '배송중', color: 'primary' as const, icon: <LocalShipping /> },
          delivered: { label: '배송완료', color: 'success' as const, icon: <CheckCircle /> },
          cancelled: { label: '취소', color: 'error' as const, icon: <Cancel /> },
          refunded: { label: '환불', color: 'error' as const, icon: <Cancel /> },
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
      field: 'paymentStatus',
      headerName: '결제상태',
      width: 100,
      renderCell: (params: GridRenderCellParams) => {
        const statusConfig = {
          pending: { label: '대기', color: 'warning' as const },
          paid: { label: '완료', color: 'success' as const },
          failed: { label: '실패', color: 'error' as const },
          refunded: { label: '환불', color: 'default' as const },
        }
        const config = statusConfig[params.value as keyof typeof statusConfig]
        
        return (
          <Chip
            label={config.label}
            size="small"
            color={config.color}
            variant="outlined"
          />
        )
      },
    },
    {
      field: 'shippingInfo',
      headerName: '배송정보',
      width: 150,
      renderCell: (params: GridRenderCellParams) => {
        if (params.row.trackingNumber) {
          return (
            <Box>
              <Typography variant="caption" color="text.secondary">
                {params.row.shippingCarrier}
              </Typography>
              <Typography variant="body2" fontWeight={500}>
                {params.row.trackingNumber}
              </Typography>
            </Box>
          )
        }
        return <Typography variant="body2" color="text.disabled">-</Typography>
      },
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: '작업',
      width: 120,
      getActions: (params) => [
        <GridActionsCellItem
          icon={<Visibility />}
          label="상세보기"
          onClick={() => handleDialogOpen('detail', params.row)}
        />,
        <GridActionsCellItem
          icon={<Print />}
          label="송장 인쇄"
          onClick={() => handlePrintInvoice(params.row)}
        />,
        <GridActionsCellItem
          icon={<LocalShipping />}
          label="배송 처리"
          onClick={() => handleDialogOpen('shipping', params.row)}
          disabled={params.row.status !== 'processing'}
        />,
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
          주문 관리
        </Typography>
        <Typography variant="body1" color="text.secondary">
          주문을 확인하고 배송을 관리하세요
        </Typography>
      </Box>

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" variant="body2">
                    전체 주문
                  </Typography>
                  <Typography variant="h4">
                    {formatNumber(statistics.total)}
                  </Typography>
                </Box>
                <ShoppingCart color="primary" sx={{ fontSize: 40, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" variant="body2">
                    신규 주문
                  </Typography>
                  <Typography variant="h4" color="warning.main">
                    {formatNumber(statistics.pending)}
                  </Typography>
                </Box>
                <AccessTime color="warning" sx={{ fontSize: 40, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" variant="body2">
                    배송중
                  </Typography>
                  <Typography variant="h4" color="primary.main">
                    {formatNumber(statistics.shipped)}
                  </Typography>
                </Box>
                <LocalShipping color="primary" sx={{ fontSize: 40, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" variant="body2">
                    총 매출
                  </Typography>
                  <Typography variant="h4" color="success.main">
                    {formatCurrency(statistics.totalRevenue)}
                  </Typography>
                </Box>
                <AttachMoney color="success" sx={{ fontSize: 40, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
          <Tab label={<Badge badgeContent={tabCounts.all} color="default">전체</Badge>} />
          <Tab label={<Badge badgeContent={tabCounts.newOrders} color="warning">신규주문</Badge>} />
          <Tab label={<Badge badgeContent={tabCounts.preparing} color="info">상품준비</Badge>} />
          <Tab label={<Badge badgeContent={tabCounts.shipping} color="primary">배송중</Badge>} />
          <Tab label={<Badge badgeContent={tabCounts.completed} color="success">완료</Badge>} />
          <Tab label={<Badge badgeContent={tabCounts.cancelled} color="error">취소/환불</Badge>} />
        </Tabs>
      </Paper>

      {/* Toolbar */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              variant="outlined"
              placeholder="주문번호, 고객명, 연락처로 검색..."
              value={searchQuery}
              onChange={handleSearch}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          <Grid item xs={12} md={8}>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <Select
                  value={filters.status}
                  onChange={handleFilterChange('status')}
                  displayEmpty
                >
                  <MenuItem value="all">모든 상태</MenuItem>
                  <MenuItem value="pending">주문확인</MenuItem>
                  <MenuItem value="confirmed">주문확정</MenuItem>
                  <MenuItem value="processing">상품준비</MenuItem>
                  <MenuItem value="shipped">배송중</MenuItem>
                  <MenuItem value="delivered">배송완료</MenuItem>
                  <MenuItem value="cancelled">취소/환불</MenuItem>
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <Select
                  value={filters.platform}
                  onChange={handleFilterChange('platform')}
                  displayEmpty
                >
                  <MenuItem value="all">모든 플랫폼</MenuItem>
                  <MenuItem value="쿠팡">쿠팡</MenuItem>
                  <MenuItem value="네이버">네이버</MenuItem>
                  <MenuItem value="11번가">11번가</MenuItem>
                  <MenuItem value="G마켓">G마켓</MenuItem>
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <Select
                  value={filters.dateRange}
                  onChange={handleFilterChange('dateRange')}
                  displayEmpty
                >
                  <MenuItem value="all">전체 기간</MenuItem>
                  <MenuItem value="today">오늘</MenuItem>
                  <MenuItem value="week">이번 주</MenuItem>
                  <MenuItem value="month">이번 달</MenuItem>
                  <MenuItem value="custom">기간 설정</MenuItem>
                </Select>
              </FormControl>
              <Box sx={{ flexGrow: 1 }} />
              {selectedRows.length > 0 && (
                <Button
                  variant="outlined"
                  startIcon={<FilterList />}
                  onClick={() => handleDialogOpen('bulkActions')}
                >
                  일괄 작업 ({selectedRows.length}개)
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
                <MenuItem onClick={handleExportOrders}>
                  <Download sx={{ mr: 1 }} /> 주문 내보내기
                </MenuItem>
                <MenuItem>
                  <Email sx={{ mr: 1 }} /> 이메일 발송
                </MenuItem>
                <MenuItem>
                  <WhatsApp sx={{ mr: 1 }} /> 카톡 알림
                </MenuItem>
              </Menu>
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* Orders Grid 또는 Empty State */}
      {!loading && filteredOrders.length === 0 ? (
        orders.length === 0 ? (
          // 완전히 비어있는 경우 - 신규 사용자
          <OrdersEmptyState
            onViewProducts={() => navigate('/products')}
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
                    setFilters({
                      status: 'all',
                      platform: 'all',
                      dateRange: 'all',
                      paymentStatus: 'all',
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
      ) : (
        <Paper sx={{ height: 600 }}>
          <DataGrid
            rows={filteredOrders}
            columns={columns}
            loading={loading}
            checkboxSelection
            disableRowSelectionOnClick
            rowSelectionModel={selectedRows}
            onRowSelectionModelChange={setSelectedRows}
            pageSizeOptions={[10, 25, 50, 100]}
            initialState={{
              pagination: { paginationModel: { pageSize: 25 } },
            }}
            sx={{
              '& .MuiDataGrid-cell:hover': {
                cursor: 'pointer',
              },
            }}
          />
        </Paper>
      )}

      {/* Dialogs */}
      <OrderDetailDialog
        open={dialogState.detail}
        onClose={() => handleDialogClose('detail')}
        order={selectedOrder}
        onStatusUpdate={handleStatusUpdate}
      />
      <BulkOrderActionsDialog
        open={dialogState.bulkActions}
        onClose={() => handleDialogClose('bulkActions')}
        selectedOrders={orders.filter(o => selectedRows.includes(o.id))}
      />
      <ShippingDialog
        open={dialogState.shipping}
        onClose={() => handleDialogClose('shipping')}
        order={selectedOrder}
      />
    </Box>
  )
}

export default Orders