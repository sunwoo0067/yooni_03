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
  Card,
  CardContent,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  Tab,
  Tabs,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  ListItemSecondaryAction,
  Rating,
  Tooltip,
  Divider,
  Alert,
  SpeedDial,
  SpeedDialAction,
  SpeedDialIcon,
} from '@mui/material'
import {
  DataGrid,
  GridColDef,
  GridRowSelectionModel,
  GridActionsCellItem,
  GridRenderCellParams,
} from '@mui/x-data-grid'
import {
  Add,
  Search,
  FilterList,
  MoreVert,
  Edit,
  Delete,
  Email,
  Phone,
  LocationOn,
  Business,
  AttachMoney,
  ShoppingCart,
  LocalShipping,
  History,
  Star,
  TrendingUp,
  Groups,
  Inventory,
  FileUpload,
  Download,
  ContactMail,
  Schedule,
  CheckCircle,
  Warning,
} from '@mui/icons-material'
import { toast } from 'react-hot-toast'
import { formatCurrency, formatNumber, formatDate } from '@utils/format'

interface Contact {
  name: string
  position: string
  phone: string
  email: string
}

interface Wholesaler {
  id: string
  name: string
  businessNumber: string
  category: string
  status: 'active' | 'inactive' | 'pending'
  rating: number
  contacts: Contact[]
  address: {
    street: string
    city: string
    state: string
    zipCode: string
  }
  paymentTerms: string
  minimumOrder: number
  deliveryDays: number
  totalOrders: number
  totalAmount: number
  lastOrderDate?: string
  products: number
  notes?: string
  createdAt: string
  updatedAt: string
}

interface PurchaseOrder {
  id: string
  wholesalerId: string
  orderNumber: string
  status: 'draft' | 'sent' | 'confirmed' | 'shipped' | 'received' | 'cancelled'
  items: Array<{
    productId: string
    productName: string
    quantity: number
    unitPrice: number
    subtotal: number
  }>
  totalAmount: number
  orderDate: string
  expectedDate?: string
  receivedDate?: string
}

const Wholesalers: React.FC = () => {
  const [wholesalers, setWholesalers] = useState<Wholesaler[]>([])
  const [selectedWholesaler, setSelectedWholesaler] = useState<Wholesaler | null>(null)
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedRows, setSelectedRows] = useState<GridRowSelectionModel>([])
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [tabValue, setTabValue] = useState(0)
  const [speedDialOpen, setSpeedDialOpen] = useState(false)
  const [dialogState, setDialogState] = useState({
    wholesaler: false,
    purchaseOrder: false,
    import: false,
  })
  const [editMode, setEditMode] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    businessNumber: '',
    category: '',
    contactName: '',
    contactPosition: '',
    contactPhone: '',
    contactEmail: '',
    street: '',
    city: '',
    state: '',
    zipCode: '',
    paymentTerms: '',
    minimumOrder: 0,
    deliveryDays: 0,
    notes: '',
  })
  const [filters, setFilters] = useState({
    status: 'all',
    category: 'all',
    rating: 'all',
  })

  // Mock data
  React.useEffect(() => {
    const mockWholesalers: Wholesaler[] = [
      {
        id: '1',
        name: '글로벌 전자상사',
        businessNumber: '123-45-67890',
        category: '전자기기',
        status: 'active',
        rating: 4.5,
        contacts: [
          {
            name: '김대표',
            position: '대표이사',
            phone: '010-1234-5678',
            email: 'kim@global-elec.com',
          },
          {
            name: '박과장',
            position: '영업과장',
            phone: '010-2345-6789',
            email: 'park@global-elec.com',
          },
        ],
        address: {
          street: '전자상가로 123',
          city: '서울특별시',
          state: '용산구',
          zipCode: '04379',
        },
        paymentTerms: '월말결제',
        minimumOrder: 1000000,
        deliveryDays: 3,
        totalOrders: 156,
        totalAmount: 458000000,
        lastOrderDate: '2024-01-18T00:00:00',
        products: 89,
        notes: '주요 공급처, 긴급주문 가능',
        createdAt: '2023-05-10T00:00:00',
        updatedAt: '2024-01-18T00:00:00',
      },
      {
        id: '2',
        name: '패션플러스',
        businessNumber: '234-56-78901',
        category: '의류/패션',
        status: 'active',
        rating: 4.0,
        contacts: [
          {
            name: '이실장',
            position: '영업실장',
            phone: '010-3456-7890',
            email: 'lee@fashionplus.co.kr',
          },
        ],
        address: {
          street: '패션타운로 456',
          city: '서울특별시',
          state: '중구',
          zipCode: '04564',
        },
        paymentTerms: '선결제',
        minimumOrder: 500000,
        deliveryDays: 5,
        totalOrders: 98,
        totalAmount: 234000000,
        lastOrderDate: '2024-01-15T00:00:00',
        products: 234,
        createdAt: '2023-07-20T00:00:00',
        updatedAt: '2024-01-15T00:00:00',
      },
      {
        id: '3',
        name: '생활용품마트',
        businessNumber: '345-67-89012',
        category: '생활용품',
        status: 'inactive',
        rating: 3.5,
        contacts: [
          {
            name: '최과장',
            position: '구매과장',
            phone: '010-4567-8901',
            email: 'choi@livingmart.com',
          },
        ],
        address: {
          street: '도매시장로 789',
          city: '경기도',
          state: '성남시',
          zipCode: '13487',
        },
        paymentTerms: '현금결제',
        minimumOrder: 300000,
        deliveryDays: 2,
        totalOrders: 45,
        totalAmount: 67000000,
        lastOrderDate: '2023-12-20T00:00:00',
        products: 156,
        createdAt: '2023-09-05T00:00:00',
        updatedAt: '2023-12-20T00:00:00',
      },
    ]
    setWholesalers(mockWholesalers)

    const mockOrders: PurchaseOrder[] = [
      {
        id: '1',
        wholesalerId: '1',
        orderNumber: 'PO-2024-001',
        status: 'confirmed',
        items: [
          {
            productId: '1',
            productName: '무선 이어폰 프로',
            quantity: 50,
            unitPrice: 45000,
            subtotal: 2250000,
          },
          {
            productId: '2',
            productName: '스마트워치 울트라',
            quantity: 20,
            unitPrice: 280000,
            subtotal: 5600000,
          },
        ],
        totalAmount: 7850000,
        orderDate: '2024-01-18T00:00:00',
        expectedDate: '2024-01-21T00:00:00',
      },
    ]
    setPurchaseOrders(mockOrders)
  }, [])

  // Handlers
  const handleSearch = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(event.target.value)
  }, [])

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, wholesaler: Wholesaler) => {
    setAnchorEl(event.currentTarget)
    setSelectedWholesaler(wholesaler)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
  }

  const handleAddWholesaler = () => {
    setEditMode(false)
    setFormData({
      name: '',
      businessNumber: '',
      category: '',
      contactName: '',
      contactPosition: '',
      contactPhone: '',
      contactEmail: '',
      street: '',
      city: '',
      state: '',
      zipCode: '',
      paymentTerms: '',
      minimumOrder: 0,
      deliveryDays: 0,
      notes: '',
    })
    setDialogState({ ...dialogState, wholesaler: true })
  }

  const handleEditWholesaler = () => {
    if (selectedWholesaler) {
      setEditMode(true)
      setFormData({
        name: selectedWholesaler.name,
        businessNumber: selectedWholesaler.businessNumber,
        category: selectedWholesaler.category,
        contactName: selectedWholesaler.contacts[0]?.name || '',
        contactPosition: selectedWholesaler.contacts[0]?.position || '',
        contactPhone: selectedWholesaler.contacts[0]?.phone || '',
        contactEmail: selectedWholesaler.contacts[0]?.email || '',
        street: selectedWholesaler.address.street,
        city: selectedWholesaler.address.city,
        state: selectedWholesaler.address.state,
        zipCode: selectedWholesaler.address.zipCode,
        paymentTerms: selectedWholesaler.paymentTerms,
        minimumOrder: selectedWholesaler.minimumOrder,
        deliveryDays: selectedWholesaler.deliveryDays,
        notes: selectedWholesaler.notes || '',
      })
      setDialogState({ ...dialogState, wholesaler: true })
      handleMenuClose()
    }
  }

  const handleDeleteWholesaler = () => {
    if (selectedWholesaler && window.confirm(`${selectedWholesaler.name}을(를) 삭제하시겠습니까?`)) {
      setWholesalers(prev => prev.filter(w => w.id !== selectedWholesaler.id))
      toast.success('도매처가 삭제되었습니다.')
      handleMenuClose()
    }
  }

  const handleSaveWholesaler = () => {
    if (!formData.name || !formData.businessNumber) {
      toast.error('필수 정보를 입력해주세요.')
      return
    }

    if (editMode && selectedWholesaler) {
      // Update existing wholesaler
      setWholesalers(prev => prev.map(w => 
        w.id === selectedWholesaler.id
          ? {
              ...w,
              name: formData.name,
              businessNumber: formData.businessNumber,
              category: formData.category,
              contacts: [{
                name: formData.contactName,
                position: formData.contactPosition,
                phone: formData.contactPhone,
                email: formData.contactEmail,
              }],
              address: {
                street: formData.street,
                city: formData.city,
                state: formData.state,
                zipCode: formData.zipCode,
              },
              paymentTerms: formData.paymentTerms,
              minimumOrder: formData.minimumOrder,
              deliveryDays: formData.deliveryDays,
              notes: formData.notes,
              updatedAt: new Date().toISOString(),
            }
          : w
      ))
      toast.success('도매처 정보가 업데이트되었습니다.')
    } else {
      // Add new wholesaler
      const newWholesaler: Wholesaler = {
        id: Date.now().toString(),
        name: formData.name,
        businessNumber: formData.businessNumber,
        category: formData.category,
        status: 'pending',
        rating: 0,
        contacts: [{
          name: formData.contactName,
          position: formData.contactPosition,
          phone: formData.contactPhone,
          email: formData.contactEmail,
        }],
        address: {
          street: formData.street,
          city: formData.city,
          state: formData.state,
          zipCode: formData.zipCode,
        },
        paymentTerms: formData.paymentTerms,
        minimumOrder: formData.minimumOrder,
        deliveryDays: formData.deliveryDays,
        totalOrders: 0,
        totalAmount: 0,
        products: 0,
        notes: formData.notes,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }
      setWholesalers(prev => [...prev, newWholesaler])
      toast.success('새 도매처가 추가되었습니다.')
    }

    setDialogState({ ...dialogState, wholesaler: false })
  }

  const handleCreatePurchaseOrder = () => {
    setDialogState({ ...dialogState, purchaseOrder: true })
  }

  const handleImportWholesalers = () => {
    // Simulate import
    toast.success('도매처 목록을 가져왔습니다.')
    setDialogState({ ...dialogState, import: false })
  }

  const handleExportWholesalers = () => {
    toast.success('도매처 목록을 내보냈습니다.')
  }

  // Filtered wholesalers
  const filteredWholesalers = useMemo(() => {
    return wholesalers.filter(wholesaler => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        if (
          !wholesaler.name.toLowerCase().includes(query) &&
          !wholesaler.businessNumber.includes(query) &&
          !wholesaler.category.toLowerCase().includes(query)
        ) {
          return false
        }
      }

      // Status filter
      if (filters.status !== 'all' && wholesaler.status !== filters.status) {
        return false
      }

      // Category filter
      if (filters.category !== 'all' && wholesaler.category !== filters.category) {
        return false
      }

      // Rating filter
      if (filters.rating !== 'all') {
        const minRating = parseInt(filters.rating)
        if (wholesaler.rating < minRating) {
          return false
        }
      }

      return true
    })
  }, [wholesalers, searchQuery, filters])

  // Statistics
  const statistics = useMemo(() => {
    const active = wholesalers.filter(w => w.status === 'active').length
    const totalAmount = wholesalers.reduce((sum, w) => sum + w.totalAmount, 0)
    const totalOrders = wholesalers.reduce((sum, w) => sum + w.totalOrders, 0)
    const avgRating = wholesalers.reduce((sum, w) => sum + w.rating, 0) / wholesalers.length || 0

    return { total: wholesalers.length, active, totalAmount, totalOrders, avgRating }
  }, [wholesalers])

  // DataGrid columns
  const columns: GridColDef[] = [
    {
      field: 'name',
      headerName: '도매처명',
      width: 200,
      renderCell: (params: GridRenderCellParams) => (
        <Box>
          <Typography variant="body2" fontWeight={500}>
            {params.value}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {params.row.businessNumber}
          </Typography>
        </Box>
      ),
    },
    {
      field: 'category',
      headerName: '카테고리',
      width: 120,
      renderCell: (params: GridRenderCellParams) => (
        <Chip label={params.value} size="small" />
      ),
    },
    {
      field: 'contacts',
      headerName: '담당자',
      width: 180,
      renderCell: (params: GridRenderCellParams) => {
        const contact = params.value[0]
        return contact ? (
          <Box>
            <Typography variant="body2">{contact.name} {contact.position}</Typography>
            <Typography variant="caption" color="text.secondary">
              {contact.phone}
            </Typography>
          </Box>
        ) : null
      },
    },
    {
      field: 'paymentTerms',
      headerName: '결제조건',
      width: 100,
    },
    {
      field: 'minimumOrder',
      headerName: '최소주문',
      width: 120,
      align: 'right',
      headerAlign: 'right',
      valueFormatter: (params) => formatCurrency(params.value),
    },
    {
      field: 'rating',
      headerName: '평점',
      width: 120,
      renderCell: (params: GridRenderCellParams) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Rating value={params.value} readOnly size="small" precision={0.5} />
          <Typography variant="caption" color="text.secondary">
            ({params.value})
          </Typography>
        </Box>
      ),
    },
    {
      field: 'totalOrders',
      headerName: '총 주문',
      width: 100,
      align: 'center',
      headerAlign: 'center',
      renderCell: (params: GridRenderCellParams) => (
        <Chip label={`${params.value}건`} size="small" variant="outlined" />
      ),
    },
    {
      field: 'totalAmount',
      headerName: '총 거래액',
      width: 130,
      align: 'right',
      headerAlign: 'right',
      valueFormatter: (params) => formatCurrency(params.value),
    },
    {
      field: 'status',
      headerName: '상태',
      width: 100,
      renderCell: (params: GridRenderCellParams) => {
        const statusConfig = {
          active: { label: '활성', color: 'success' as const, icon: <CheckCircle /> },
          inactive: { label: '비활성', color: 'warning' as const, icon: <Warning /> },
          pending: { label: '대기', color: 'default' as const, icon: <Schedule /> },
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
      field: 'lastOrderDate',
      headerName: '최근 주문',
      width: 130,
      valueFormatter: (params) => params.value ? formatDate(params.value) : '-',
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: '작업',
      width: 100,
      getActions: (params) => [
        <GridActionsCellItem
          icon={<Email />}
          label="이메일"
          onClick={() => toast.success('이메일을 발송합니다.')}
        />,
        <GridActionsCellItem
          icon={<ShoppingCart />}
          label="주문하기"
          onClick={handleCreatePurchaseOrder}
        />,
        <GridActionsCellItem
          icon={<MoreVert />}
          label="더보기"
          onClick={(e) => handleMenuOpen(e, params.row)}
        />,
      ],
    },
  ]

  const categories = ['전자기기', '의류/패션', '생활용품', '식품', '화장품', '스포츠용품']

  const speedDialActions = [
    { icon: <Add />, name: '도매처 추가', onClick: handleAddWholesaler },
    { icon: <ShoppingCart />, name: '구매 주문', onClick: handleCreatePurchaseOrder },
    { icon: <FileUpload />, name: '가져오기', onClick: () => setDialogState({ ...dialogState, import: true }) },
    { icon: <Download />, name: '내보내기', onClick: handleExportWholesalers },
  ]

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          도매처 관리
        </Typography>
        <Typography variant="body1" color="text.secondary">
          도매처 정보를 관리하고 구매 주문을 생성하세요
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
                    전체 도매처
                  </Typography>
                  <Typography variant="h4">
                    {formatNumber(statistics.total)}
                  </Typography>
                </Box>
                <Groups color="primary" sx={{ fontSize: 40, opacity: 0.3 }} />
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
                    활성 도매처
                  </Typography>
                  <Typography variant="h4" color="success.main">
                    {formatNumber(statistics.active)}
                  </Typography>
                </Box>
                <CheckCircle color="success" sx={{ fontSize: 40, opacity: 0.3 }} />
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
                    총 거래액
                  </Typography>
                  <Typography variant="h4">
                    ₩{(statistics.totalAmount / 100000000).toFixed(1)}억
                  </Typography>
                </Box>
                <AttachMoney color="primary" sx={{ fontSize: 40, opacity: 0.3 }} />
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
                    평균 평점
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="h4">
                      {statistics.avgRating.toFixed(1)}
                    </Typography>
                    <Star color="warning" />
                  </Box>
                </Box>
                <Star color="warning" sx={{ fontSize: 40, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
          <Tab label="전체 도매처" />
          <Tab label="구매 주문" />
          <Tab label="가격 비교" />
          <Tab label="거래 내역" />
        </Tabs>
      </Paper>

      {/* Tab Content */}
      {tabValue === 0 && (
        <>
          {/* Toolbar */}
          <Paper sx={{ p: 2, mb: 3 }}>
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  variant="outlined"
                  placeholder="도매처명, 사업자번호로 검색..."
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
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <FormControl size="small" sx={{ minWidth: 120 }}>
                    <InputLabel>상태</InputLabel>
                    <Select
                      value={filters.status}
                      onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                      label="상태"
                    >
                      <MenuItem value="all">전체</MenuItem>
                      <MenuItem value="active">활성</MenuItem>
                      <MenuItem value="inactive">비활성</MenuItem>
                      <MenuItem value="pending">대기</MenuItem>
                    </Select>
                  </FormControl>
                  <FormControl size="small" sx={{ minWidth: 120 }}>
                    <InputLabel>카테고리</InputLabel>
                    <Select
                      value={filters.category}
                      onChange={(e) => setFilters({ ...filters, category: e.target.value })}
                      label="카테고리"
                    >
                      <MenuItem value="all">전체</MenuItem>
                      {categories.map((cat) => (
                        <MenuItem key={cat} value={cat}>{cat}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <FormControl size="small" sx={{ minWidth: 120 }}>
                    <InputLabel>평점</InputLabel>
                    <Select
                      value={filters.rating}
                      onChange={(e) => setFilters({ ...filters, rating: e.target.value })}
                      label="평점"
                    >
                      <MenuItem value="all">전체</MenuItem>
                      <MenuItem value="4">4점 이상</MenuItem>
                      <MenuItem value="3">3점 이상</MenuItem>
                      <MenuItem value="2">2점 이상</MenuItem>
                    </Select>
                  </FormControl>
                </Box>
              </Grid>
            </Grid>
          </Paper>

          {/* Wholesalers Grid */}
          <Paper sx={{ height: 600 }}>
            <DataGrid
              rows={filteredWholesalers}
              columns={columns}
              checkboxSelection
              disableRowSelectionOnClick
              rowSelectionModel={selectedRows}
              onRowSelectionModelChange={setSelectedRows}
              pageSizeOptions={[10, 25, 50]}
              initialState={{
                pagination: { paginationModel: { pageSize: 25 } },
              }}
            />
          </Paper>
        </>
      )}

      {tabValue === 1 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            구매 주문 관리
          </Typography>
          <Alert severity="info">
            구매 주문 기능은 준비 중입니다.
          </Alert>
        </Paper>
      )}

      {tabValue === 2 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            가격 비교
          </Typography>
          <Alert severity="info">
            도매처별 가격 비교 기능은 준비 중입니다.
          </Alert>
        </Paper>
      )}

      {tabValue === 3 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            거래 내역
          </Typography>
          <Alert severity="info">
            거래 내역 조회 기능은 준비 중입니다.
          </Alert>
        </Paper>
      )}

      {/* Speed Dial */}
      <SpeedDial
        ariaLabel="작업 메뉴"
        sx={{ position: 'fixed', bottom: 16, right: 16 }}
        icon={<SpeedDialIcon />}
        open={speedDialOpen}
        onClose={() => setSpeedDialOpen(false)}
        onOpen={() => setSpeedDialOpen(true)}
      >
        {speedDialActions.map((action) => (
          <SpeedDialAction
            key={action.name}
            icon={action.icon}
            tooltipTitle={action.name}
            onClick={() => {
              action.onClick()
              setSpeedDialOpen(false)
            }}
          />
        ))}
      </SpeedDial>

      {/* Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleEditWholesaler}>
          <Edit sx={{ mr: 1 }} /> 수정
        </MenuItem>
        <MenuItem onClick={() => {
          toast.success('거래 내역을 조회합니다.')
          handleMenuClose()
        }}>
          <History sx={{ mr: 1 }} /> 거래 내역
        </MenuItem>
        <MenuItem onClick={() => {
          toast.success('가격표를 요청합니다.')
          handleMenuClose()
        }}>
          <AttachMoney sx={{ mr: 1 }} /> 가격표 요청
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleDeleteWholesaler} sx={{ color: 'error.main' }}>
          <Delete sx={{ mr: 1 }} /> 삭제
        </MenuItem>
      </Menu>

      {/* Add/Edit Wholesaler Dialog */}
      <Dialog open={dialogState.wholesaler} onClose={() => setDialogState({ ...dialogState, wholesaler: false })} maxWidth="md" fullWidth>
        <DialogTitle>
          {editMode ? '도매처 수정' : '새 도매처 추가'}
        </DialogTitle>
        <DialogContent dividers>
          <Grid container spacing={2}>
            {/* Basic Info */}
            <Grid item xs={12}>
              <Typography variant="subtitle2" gutterBottom>
                기본 정보
              </Typography>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                required
                label="도매처명"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                required
                label="사업자번호"
                value={formData.businessNumber}
                onChange={(e) => setFormData({ ...formData, businessNumber: e.target.value })}
                placeholder="123-45-67890"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>카테고리</InputLabel>
                <Select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  label="카테고리"
                >
                  {categories.map((cat) => (
                    <MenuItem key={cat} value={cat}>{cat}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="결제조건"
                value={formData.paymentTerms}
                onChange={(e) => setFormData({ ...formData, paymentTerms: e.target.value })}
                placeholder="예: 월말결제, 선결제"
              />
            </Grid>

            {/* Contact Info */}
            <Grid item xs={12}>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle2" gutterBottom>
                담당자 정보
              </Typography>
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="담당자명"
                value={formData.contactName}
                onChange={(e) => setFormData({ ...formData, contactName: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="직급"
                value={formData.contactPosition}
                onChange={(e) => setFormData({ ...formData, contactPosition: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="연락처"
                value={formData.contactPhone}
                onChange={(e) => setFormData({ ...formData, contactPhone: e.target.value })}
                placeholder="010-1234-5678"
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="이메일"
                type="email"
                value={formData.contactEmail}
                onChange={(e) => setFormData({ ...formData, contactEmail: e.target.value })}
              />
            </Grid>

            {/* Address */}
            <Grid item xs={12}>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle2" gutterBottom>
                주소
              </Typography>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="상세주소"
                value={formData.street}
                onChange={(e) => setFormData({ ...formData, street: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="시/도"
                value={formData.city}
                onChange={(e) => setFormData({ ...formData, city: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="구/군"
                value={formData.state}
                onChange={(e) => setFormData({ ...formData, state: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="우편번호"
                value={formData.zipCode}
                onChange={(e) => setFormData({ ...formData, zipCode: e.target.value })}
              />
            </Grid>

            {/* Trade Terms */}
            <Grid item xs={12}>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle2" gutterBottom>
                거래 조건
              </Typography>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="최소주문금액"
                type="number"
                value={formData.minimumOrder}
                onChange={(e) => setFormData({ ...formData, minimumOrder: parseInt(e.target.value) })}
                InputProps={{
                  startAdornment: '₩',
                }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="배송 소요일"
                type="number"
                value={formData.deliveryDays}
                onChange={(e) => setFormData({ ...formData, deliveryDays: parseInt(e.target.value) })}
                InputProps={{
                  endAdornment: '일',
                }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={3}
                label="메모"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="특이사항이나 메모를 입력하세요"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogState({ ...dialogState, wholesaler: false })}>
            취소
          </Button>
          <Button variant="contained" onClick={handleSaveWholesaler}>
            {editMode ? '수정' : '추가'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Purchase Order Dialog */}
      <Dialog open={dialogState.purchaseOrder} onClose={() => setDialogState({ ...dialogState, purchaseOrder: false })} maxWidth="lg" fullWidth>
        <DialogTitle>
          구매 주문 생성
        </DialogTitle>
        <DialogContent dividers>
          <Alert severity="info">
            구매 주문 기능은 준비 중입니다.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogState({ ...dialogState, purchaseOrder: false })}>
            닫기
          </Button>
        </DialogActions>
      </Dialog>

      {/* Import Dialog */}
      <Dialog open={dialogState.import} onClose={() => setDialogState({ ...dialogState, import: false })} maxWidth="sm" fullWidth>
        <DialogTitle>
          도매처 가져오기
        </DialogTitle>
        <DialogContent dividers>
          <Box sx={{ textAlign: 'center', py: 3 }}>
            <FileUpload sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              Excel 파일 업로드
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              도매처 정보가 포함된 Excel 파일을 업로드하세요.
            </Typography>
            <Button variant="contained" component="label">
              파일 선택
              <input type="file" hidden accept=".xlsx,.xls" onChange={handleImportWholesalers} />
            </Button>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogState({ ...dialogState, import: false })}>
            취소
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default Wholesalers