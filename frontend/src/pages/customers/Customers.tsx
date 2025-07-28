import React, { useState, useMemo } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  IconButton,
  Chip,
  Avatar,
  TextField,
  InputAdornment,
  Tooltip,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  Card,
  CardContent,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  ListItemIcon,
  FormControl,
  InputLabel,
  Select,
  ButtonGroup,
  Badge,
  LinearProgress,
  Alert,
  Divider,
  Rating,
  FormControlLabel,
  Checkbox,
  Radio,
  RadioGroup,
} from '@mui/material'
import {
  Search,
  Add,
  FilterList,
  MoreVert,
  Email,
  Phone,
  LocationOn,
  Edit,
  Delete,
  ShoppingCart,
  AttachMoney,
  CalendarToday,
  Star,
  Group,
  PersonAdd,
  Download,
  Upload,
  Send,
  Label,
  TrendingUp,
  TrendingDown,
  History,
  LocalOffer,
  Loyalty,
  CardGiftcard,
  Person,
  Business,
  Cake,
  Male,
  Female,
  Block,
  CheckCircle,
  Warning,
  Info,
} from '@mui/icons-material'
import { formatCurrency, formatDate, formatPercentage } from '@utils/format'
import { toast } from 'react-hot-toast'
import { DatePicker } from '@mui/x-date-pickers/DatePicker'
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider'
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns'
import { ko } from 'date-fns/locale'

// Types
interface Customer {
  id: string
  name: string
  email: string
  phone: string
  gender: 'male' | 'female' | 'other'
  birthDate: string
  registeredDate: string
  status: 'active' | 'inactive' | 'blocked'
  grade: 'vip' | 'gold' | 'silver' | 'bronze' | 'normal'
  totalOrders: number
  totalSpent: number
  lastOrderDate: string
  address: {
    street: string
    city: string
    state: string
    zipCode: string
  }
  tags: string[]
  note: string
  points: number
  coupons: number
}

interface CustomerGroup {
  id: string
  name: string
  description: string
  memberCount: number
  conditions: string[]
  benefits: string[]
}

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`customer-tabpanel-${index}`}
      aria-labelledby={`customer-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  )
}

const Customers: React.FC = () => {
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCustomers, setSelectedCustomers] = useState<string[]>([])
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null)
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)
  const [groupDialogOpen, setGroupDialogOpen] = useState(false)
  const [messageDialogOpen, setMessageDialogOpen] = useState(false)
  const [filterDialogOpen, setFilterDialogOpen] = useState(false)
  const [tabValue, setTabValue] = useState(0)
  const [selectedGroup, setSelectedGroup] = useState<string>('all')
  const [selectedGrade, setSelectedGrade] = useState<string>('all')
  const [selectedStatus, setSelectedStatus] = useState<string>('all')
  const [dateRange, setDateRange] = useState({
    start: null as Date | null,
    end: null as Date | null,
  })

  // Mock data
  const mockCustomers: Customer[] = [
    {
      id: '1',
      name: '김민수',
      email: 'minsu.kim@example.com',
      phone: '010-1234-5678',
      gender: 'male',
      birthDate: '1990-05-15',
      registeredDate: '2023-01-15',
      status: 'active',
      grade: 'vip',
      totalOrders: 45,
      totalSpent: 3500000,
      lastOrderDate: '2024-01-10',
      address: {
        street: '서울특별시 강남구 테헤란로 123',
        city: '서울',
        state: '서울특별시',
        zipCode: '06234',
      },
      tags: ['단골고객', '빠른배송선호', '전자제품'],
      note: 'VIP 고객으로 특별 관리 필요',
      points: 35000,
      coupons: 5,
    },
    {
      id: '2',
      name: '이영희',
      email: 'younghee.lee@example.com',
      phone: '010-2345-6789',
      gender: 'female',
      birthDate: '1985-08-22',
      registeredDate: '2023-03-20',
      status: 'active',
      grade: 'gold',
      totalOrders: 28,
      totalSpent: 1850000,
      lastOrderDate: '2024-01-08',
      address: {
        street: '서울특별시 마포구 월드컵로 123',
        city: '서울',
        state: '서울특별시',
        zipCode: '04123',
      },
      tags: ['화장품선호', '이벤트참여'],
      note: '',
      points: 18500,
      coupons: 3,
    },
    {
      id: '3',
      name: '박철수',
      email: 'chulsoo.park@example.com',
      phone: '010-3456-7890',
      gender: 'male',
      birthDate: '1978-12-05',
      registeredDate: '2023-06-10',
      status: 'active',
      grade: 'silver',
      totalOrders: 15,
      totalSpent: 850000,
      lastOrderDate: '2024-01-05',
      address: {
        street: '경기도 성남시 분당구 판교로 123',
        city: '성남',
        state: '경기도',
        zipCode: '13529',
      },
      tags: ['가전제품', '주말구매'],
      note: '배송 시 부재가 많음',
      points: 8500,
      coupons: 2,
    },
    {
      id: '4',
      name: '최수진',
      email: 'sujin.choi@example.com',
      phone: '010-4567-8901',
      gender: 'female',
      birthDate: '1995-03-18',
      registeredDate: '2023-09-15',
      status: 'inactive',
      grade: 'bronze',
      totalOrders: 8,
      totalSpent: 420000,
      lastOrderDate: '2023-11-20',
      address: {
        street: '부산광역시 해운대구 해운대로 456',
        city: '부산',
        state: '부산광역시',
        zipCode: '48099',
      },
      tags: ['패션', '시즌할인'],
      note: '3개월 이상 미구매',
      points: 4200,
      coupons: 1,
    },
    {
      id: '5',
      name: '정대현',
      email: 'daehyun.jung@example.com',
      phone: '010-5678-9012',
      gender: 'male',
      birthDate: '1992-07-30',
      registeredDate: '2023-11-01',
      status: 'active',
      grade: 'normal',
      totalOrders: 3,
      totalSpent: 180000,
      lastOrderDate: '2024-01-02',
      address: {
        street: '대구광역시 중구 동성로 789',
        city: '대구',
        state: '대구광역시',
        zipCode: '41943',
      },
      tags: ['신규고객'],
      note: '',
      points: 1800,
      coupons: 0,
    },
  ]

  const customerGroups: CustomerGroup[] = [
    {
      id: '1',
      name: 'VIP 고객',
      description: '연간 300만원 이상 구매 고객',
      memberCount: 45,
      conditions: ['연간 구매액 300만원 이상', '주문 횟수 30회 이상'],
      benefits: ['15% 추가 할인', '무료 배송', '전용 고객센터'],
    },
    {
      id: '2',
      name: '신규 고객',
      description: '가입 후 3개월 이내 고객',
      memberCount: 128,
      conditions: ['가입일로부터 90일 이내'],
      benefits: ['첫 구매 10% 할인', '웰컴 쿠폰 3장'],
    },
    {
      id: '3',
      name: '휴면 고객',
      description: '3개월 이상 미구매 고객',
      memberCount: 89,
      conditions: ['최근 구매일로부터 90일 경과'],
      benefits: ['복귀 쿠폰 20% 할인', '무료 배송 쿠폰'],
    },
  ]

  // Filter customers based on search and filters
  const filteredCustomers = useMemo(() => {
    return mockCustomers.filter((customer) => {
      const matchesSearch = customer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        customer.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        customer.phone.includes(searchTerm)
      
      const matchesGrade = selectedGrade === 'all' || customer.grade === selectedGrade
      const matchesStatus = selectedStatus === 'all' || customer.status === selectedStatus
      
      return matchesSearch && matchesGrade && matchesStatus
    })
  }, [searchTerm, selectedGrade, selectedStatus])

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage)
  }

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10))
    setPage(0)
  }

  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      setSelectedCustomers(filteredCustomers.map(c => c.id))
    } else {
      setSelectedCustomers([])
    }
  }

  const handleSelectCustomer = (customerId: string) => {
    setSelectedCustomers(prev => {
      if (prev.includes(customerId)) {
        return prev.filter(id => id !== customerId)
      }
      return [...prev, customerId]
    })
  }

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, customer: Customer) => {
    setAnchorEl(event.currentTarget)
    setSelectedCustomer(customer)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
  }

  const handleViewDetails = () => {
    setDetailDialogOpen(true)
    handleMenuClose()
  }

  const handleSendMessage = () => {
    setMessageDialogOpen(true)
  }

  const handleExportCustomers = () => {
    toast.success('고객 목록을 내보냈습니다.')
  }

  const handleImportCustomers = () => {
    toast.success('고객 목록을 가져왔습니다.')
  }

  const getGradeColor = (grade: Customer['grade']) => {
    switch (grade) {
      case 'vip': return 'error'
      case 'gold': return 'warning'
      case 'silver': return 'default'
      case 'bronze': return 'default'
      case 'normal': return 'default'
    }
  }

  const getGradeLabel = (grade: Customer['grade']) => {
    switch (grade) {
      case 'vip': return 'VIP'
      case 'gold': return 'GOLD'
      case 'silver': return 'SILVER'
      case 'bronze': return 'BRONZE'
      case 'normal': return '일반'
    }
  }

  const getStatusColor = (status: Customer['status']) => {
    switch (status) {
      case 'active': return 'success'
      case 'inactive': return 'warning'
      case 'blocked': return 'error'
    }
  }

  const getStatusLabel = (status: Customer['status']) => {
    switch (status) {
      case 'active': return '활성'
      case 'inactive': return '휴면'
      case 'blocked': return '차단'
    }
  }

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={ko}>
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h4" gutterBottom>
              고객 관리
            </Typography>
            <Typography variant="body1" color="text.secondary">
              고객 정보를 관리하고 관계를 구축하세요
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="outlined"
              startIcon={<Upload />}
              onClick={handleImportCustomers}
            >
              가져오기
            </Button>
            <Button
              variant="outlined"
              startIcon={<Download />}
              onClick={handleExportCustomers}
            >
              내보내기
            </Button>
            <Button
              variant="contained"
              startIcon={<PersonAdd />}
              onClick={() => setDetailDialogOpen(true)}
            >
              고객 추가
            </Button>
          </Box>
        </Box>

        {/* Statistics Cards */}
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography color="text.secondary" variant="body2">
                      전체 고객
                    </Typography>
                    <Typography variant="h4" sx={{ mt: 1 }}>
                      1,250
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 1 }}>
                      <TrendingUp color="success" fontSize="small" />
                      <Typography variant="body2" color="success.main">
                        +8.5%
                      </Typography>
                    </Box>
                  </Box>
                  <Avatar sx={{ bgcolor: 'primary.light', width: 56, height: 56 }}>
                    <Group />
                  </Avatar>
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
                      활성 고객
                    </Typography>
                    <Typography variant="h4" sx={{ mt: 1 }}>
                      892
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 1 }}>
                      <TrendingUp color="success" fontSize="small" />
                      <Typography variant="body2" color="success.main">
                        +12.3%
                      </Typography>
                    </Box>
                  </Box>
                  <Avatar sx={{ bgcolor: 'success.light', width: 56, height: 56 }}>
                    <CheckCircle />
                  </Avatar>
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
                      평균 구매액
                    </Typography>
                    <Typography variant="h5" sx={{ mt: 1 }}>
                      {formatCurrency(156000)}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 1 }}>
                      <TrendingDown color="error" fontSize="small" />
                      <Typography variant="body2" color="error.main">
                        -2.1%
                      </Typography>
                    </Box>
                  </Box>
                  <Avatar sx={{ bgcolor: 'warning.light', width: 56, height: 56 }}>
                    <AttachMoney />
                  </Avatar>
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
                      재구매율
                    </Typography>
                    <Typography variant="h4" sx={{ mt: 1 }}>
                      45%
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 1 }}>
                      <TrendingUp color="success" fontSize="small" />
                      <Typography variant="body2" color="success.main">
                        +5.2%
                      </Typography>
                    </Box>
                  </Box>
                  <Avatar sx={{ bgcolor: 'info.light', width: 56, height: 56 }}>
                    <Loyalty />
                  </Avatar>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Tabs */}
        <Paper sx={{ mb: 3 }}>
          <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
            <Tab label="고객 목록" />
            <Tab label="고객 그룹" />
            <Tab label="마케팅 활동" />
          </Tabs>
        </Paper>

        {/* Tab Content */}
        <TabPanel value={tabValue} index={0}>
          {/* Search and Filters */}
          <Paper sx={{ p: 2, mb: 3 }}>
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  size="small"
                  placeholder="이름, 이메일, 전화번호로 검색"
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
              <Grid item xs={12} md={2}>
                <FormControl fullWidth size="small">
                  <InputLabel>등급</InputLabel>
                  <Select
                    value={selectedGrade}
                    onChange={(e) => setSelectedGrade(e.target.value)}
                    label="등급"
                  >
                    <MenuItem value="all">전체</MenuItem>
                    <MenuItem value="vip">VIP</MenuItem>
                    <MenuItem value="gold">GOLD</MenuItem>
                    <MenuItem value="silver">SILVER</MenuItem>
                    <MenuItem value="bronze">BRONZE</MenuItem>
                    <MenuItem value="normal">일반</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={2}>
                <FormControl fullWidth size="small">
                  <InputLabel>상태</InputLabel>
                  <Select
                    value={selectedStatus}
                    onChange={(e) => setSelectedStatus(e.target.value)}
                    label="상태"
                  >
                    <MenuItem value="all">전체</MenuItem>
                    <MenuItem value="active">활성</MenuItem>
                    <MenuItem value="inactive">휴면</MenuItem>
                    <MenuItem value="blocked">차단</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={2}>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<FilterList />}
                  onClick={() => setFilterDialogOpen(true)}
                >
                  상세 필터
                </Button>
              </Grid>
              <Grid item xs={12} md={2}>
                {selectedCustomers.length > 0 && (
                  <Button
                    fullWidth
                    variant="contained"
                    startIcon={<Send />}
                    onClick={handleSendMessage}
                  >
                    메시지 보내기 ({selectedCustomers.length})
                  </Button>
                )}
              </Grid>
            </Grid>
          </Paper>

          {/* Customer Table */}
          <Paper>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell padding="checkbox">
                      <Checkbox
                        indeterminate={selectedCustomers.length > 0 && selectedCustomers.length < filteredCustomers.length}
                        checked={selectedCustomers.length === filteredCustomers.length}
                        onChange={handleSelectAll}
                      />
                    </TableCell>
                    <TableCell>고객명</TableCell>
                    <TableCell>연락처</TableCell>
                    <TableCell>등급</TableCell>
                    <TableCell>상태</TableCell>
                    <TableCell align="right">총 구매액</TableCell>
                    <TableCell align="center">주문 수</TableCell>
                    <TableCell>최근 구매</TableCell>
                    <TableCell>태그</TableCell>
                    <TableCell align="center">작업</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredCustomers
                    .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                    .map((customer) => (
                      <TableRow
                        key={customer.id}
                        hover
                        selected={selectedCustomers.includes(customer.id)}
                      >
                        <TableCell padding="checkbox">
                          <Checkbox
                            checked={selectedCustomers.includes(customer.id)}
                            onChange={() => handleSelectCustomer(customer.id)}
                          />
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                            <Avatar sx={{ width: 40, height: 40 }}>
                              {customer.name[0]}
                            </Avatar>
                            <Box>
                              <Typography variant="body2" fontWeight={500}>
                                {customer.name}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {customer.email}
                              </Typography>
                            </Box>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box>
                            <Typography variant="body2">{customer.phone}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {customer.address.city}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={getGradeLabel(customer.grade)}
                            color={getGradeColor(customer.grade)}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={getStatusLabel(customer.status)}
                            color={getStatusColor(customer.status)}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2" fontWeight={500}>
                            {formatCurrency(customer.totalSpent)}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Typography variant="body2">
                            {customer.totalOrders}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {formatDate(customer.lastOrderDate)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                            {customer.tags.slice(0, 2).map((tag, index) => (
                              <Chip
                                key={index}
                                label={tag}
                                size="small"
                                variant="outlined"
                              />
                            ))}
                            {customer.tags.length > 2 && (
                              <Chip
                                label={`+${customer.tags.length - 2}`}
                                size="small"
                                variant="outlined"
                              />
                            )}
                          </Box>
                        </TableCell>
                        <TableCell align="center">
                          <IconButton
                            size="small"
                            onClick={(e) => handleMenuOpen(e, customer)}
                          >
                            <MoreVert />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination
              rowsPerPageOptions={[5, 10, 25]}
              component="div"
              count={filteredCustomers.length}
              rowsPerPage={rowsPerPage}
              page={page}
              onPageChange={handleChangePage}
              onRowsPerPageChange={handleChangeRowsPerPage}
            />
          </Paper>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          {/* Customer Groups */}
          <Grid container spacing={3}>
            {customerGroups.map((group) => (
              <Grid item xs={12} md={4} key={group.id}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                      <Box>
                        <Typography variant="h6" gutterBottom>
                          {group.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {group.description}
                        </Typography>
                      </Box>
                      <Chip label={`${group.memberCount}명`} color="primary" />
                    </Box>
                    <Divider sx={{ my: 2 }} />
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        조건
                      </Typography>
                      <List dense>
                        {group.conditions.map((condition, index) => (
                          <ListItem key={index} sx={{ px: 0 }}>
                            <ListItemText
                              primary={
                                <Typography variant="body2" color="text.secondary">
                                  • {condition}
                                </Typography>
                              }
                            />
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                    <Box>
                      <Typography variant="subtitle2" gutterBottom>
                        혜택
                      </Typography>
                      <List dense>
                        {group.benefits.map((benefit, index) => (
                          <ListItem key={index} sx={{ px: 0 }}>
                            <ListItemText
                              primary={
                                <Typography variant="body2" color="primary">
                                  • {benefit}
                                </Typography>
                              }
                            />
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                  </CardContent>
                  <Box sx={{ px: 2, pb: 2 }}>
                    <Button fullWidth variant="outlined" onClick={() => setGroupDialogOpen(true)}>
                      그룹 편집
                    </Button>
                  </Box>
                </Card>
              </Grid>
            ))}
            <Grid item xs={12} md={4}>
              <Card sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 300 }}>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Button
                    variant="outlined"
                    size="large"
                    startIcon={<Add />}
                    onClick={() => setGroupDialogOpen(true)}
                  >
                    새 그룹 만들기
                  </Button>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          {/* Marketing Activities */}
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    최근 캠페인
                  </Typography>
                  <List>
                    <ListItem>
                      <ListItemAvatar>
                        <Avatar sx={{ bgcolor: 'primary.light' }}>
                          <Email />
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary="신년 특별 할인 이벤트"
                        secondary="2024-01-01 • 이메일 • 전송 1,200 / 오픈 456 (38%)"
                      />
                      <Chip label="진행중" color="success" size="small" />
                    </ListItem>
                    <ListItem>
                      <ListItemAvatar>
                        <Avatar sx={{ bgcolor: 'warning.light' }}>
                          <CardGiftcard />
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary="VIP 고객 감사 쿠폰"
                        secondary="2023-12-25 • 쿠폰 • 발급 45 / 사용 38 (84%)"
                      />
                      <Chip label="완료" color="default" size="small" />
                    </ListItem>
                    <ListItem>
                      <ListItemAvatar>
                        <Avatar sx={{ bgcolor: 'info.light' }}>
                          <LocalOffer />
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary="휴면 고객 복귀 캠페인"
                        secondary="2023-12-15 • SMS • 전송 89 / 반응 12 (13%)"
                      />
                      <Chip label="완료" color="default" size="small" />
                    </ListItem>
                  </List>
                  <Box sx={{ mt: 2 }}>
                    <Button fullWidth variant="contained" startIcon={<Add />}>
                      새 캠페인 만들기
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    캠페인 성과
                  </Typography>
                  <Box sx={{ mt: 3 }}>
                    <Box sx={{ mb: 3 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">이메일 오픈율</Typography>
                        <Typography variant="body2" fontWeight={500}>38%</Typography>
                      </Box>
                      <LinearProgress variant="determinate" value={38} sx={{ height: 8, borderRadius: 4 }} />
                    </Box>
                    <Box sx={{ mb: 3 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">클릭률</Typography>
                        <Typography variant="body2" fontWeight={500}>12%</Typography>
                      </Box>
                      <LinearProgress variant="determinate" value={12} sx={{ height: 8, borderRadius: 4 }} color="secondary" />
                    </Box>
                    <Box sx={{ mb: 3 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">전환율</Typography>
                        <Typography variant="body2" fontWeight={500}>5.2%</Typography>
                      </Box>
                      <LinearProgress variant="determinate" value={5.2} sx={{ height: 8, borderRadius: 4 }} color="success" />
                    </Box>
                    <Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">쿠폰 사용률</Typography>
                        <Typography variant="body2" fontWeight={500}>84%</Typography>
                      </Box>
                      <LinearProgress variant="determinate" value={84} sx={{ height: 8, borderRadius: 4 }} color="warning" />
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>

        {/* Context Menu */}
        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleMenuClose}
        >
          <MenuItem onClick={handleViewDetails}>
            <ListItemIcon>
              <Info fontSize="small" />
            </ListItemIcon>
            상세 정보
          </MenuItem>
          <MenuItem onClick={() => {
            setMessageDialogOpen(true)
            handleMenuClose()
          }}>
            <ListItemIcon>
              <Email fontSize="small" />
            </ListItemIcon>
            메시지 보내기
          </MenuItem>
          <MenuItem onClick={handleMenuClose}>
            <ListItemIcon>
              <History fontSize="small" />
            </ListItemIcon>
            구매 이력
          </MenuItem>
          <MenuItem onClick={handleMenuClose}>
            <ListItemIcon>
              <Edit fontSize="small" />
            </ListItemIcon>
            정보 수정
          </MenuItem>
          <Divider />
          <MenuItem onClick={handleMenuClose} sx={{ color: 'error.main' }}>
            <ListItemIcon>
              <Block fontSize="small" color="error" />
            </ListItemIcon>
            차단
          </MenuItem>
        </Menu>

        {/* Customer Detail Dialog */}
        <Dialog open={detailDialogOpen} onClose={() => setDetailDialogOpen(false)} maxWidth="md" fullWidth>
          <DialogTitle>
            {selectedCustomer ? '고객 상세 정보' : '새 고객 추가'}
          </DialogTitle>
          <DialogContent dividers>
            {selectedCustomer && (
              <Grid container spacing={3}>
                {/* Basic Info */}
                <Grid item xs={12}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, mb: 3 }}>
                    <Avatar sx={{ width: 80, height: 80 }}>
                      {selectedCustomer.name[0]}
                    </Avatar>
                    <Box>
                      <Typography variant="h5">{selectedCustomer.name}</Typography>
                      <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                        <Chip label={getGradeLabel(selectedCustomer.grade)} color={getGradeColor(selectedCustomer.grade)} size="small" />
                        <Chip label={getStatusLabel(selectedCustomer.status)} color={getStatusColor(selectedCustomer.status)} size="small" variant="outlined" />
                      </Box>
                    </Box>
                  </Box>
                </Grid>

                {/* Contact Info */}
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>연락처 정보</Typography>
                  <List dense>
                    <ListItem>
                      <ListItemIcon>
                        <Email />
                      </ListItemIcon>
                      <ListItemText primary={selectedCustomer.email} />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <Phone />
                      </ListItemIcon>
                      <ListItemText primary={selectedCustomer.phone} />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <LocationOn />
                      </ListItemIcon>
                      <ListItemText
                        primary={selectedCustomer.address.street}
                        secondary={`${selectedCustomer.address.city} ${selectedCustomer.address.state} ${selectedCustomer.address.zipCode}`}
                      />
                    </ListItem>
                  </List>
                </Grid>

                {/* Purchase Info */}
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>구매 정보</Typography>
                  <List dense>
                    <ListItem>
                      <ListItemText
                        primary="총 구매액"
                        secondary={formatCurrency(selectedCustomer.totalSpent)}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="총 주문 수"
                        secondary={`${selectedCustomer.totalOrders}건`}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="최근 구매일"
                        secondary={formatDate(selectedCustomer.lastOrderDate)}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="가입일"
                        secondary={formatDate(selectedCustomer.registeredDate)}
                      />
                    </ListItem>
                  </List>
                </Grid>

                {/* Points & Coupons */}
                <Grid item xs={12}>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Card variant="outlined">
                        <CardContent>
                          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <Box>
                              <Typography variant="body2" color="text.secondary">
                                보유 포인트
                              </Typography>
                              <Typography variant="h5">
                                {selectedCustomer.points.toLocaleString()}P
                              </Typography>
                            </Box>
                            <Loyalty color="primary" />
                          </Box>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid item xs={6}>
                      <Card variant="outlined">
                        <CardContent>
                          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <Box>
                              <Typography variant="body2" color="text.secondary">
                                보유 쿠폰
                              </Typography>
                              <Typography variant="h5">
                                {selectedCustomer.coupons}장
                              </Typography>
                            </Box>
                            <LocalOffer color="secondary" />
                          </Box>
                        </CardContent>
                      </Card>
                    </Grid>
                  </Grid>
                </Grid>

                {/* Tags & Notes */}
                <Grid item xs={12}>
                  <Typography variant="subtitle2" gutterBottom>태그</Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
                    {selectedCustomer.tags.map((tag, index) => (
                      <Chip key={index} label={tag} onDelete={() => {}} />
                    ))}
                    <Chip label="+ 태그 추가" variant="outlined" onClick={() => {}} />
                  </Box>
                  {selectedCustomer.note && (
                    <Alert severity="info" icon={<Info />}>
                      {selectedCustomer.note}
                    </Alert>
                  )}
                </Grid>
              </Grid>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDetailDialogOpen(false)}>닫기</Button>
            <Button variant="contained" onClick={() => {
              toast.success('고객 정보가 저장되었습니다.')
              setDetailDialogOpen(false)
            }}>
              저장
            </Button>
          </DialogActions>
        </Dialog>

        {/* Send Message Dialog */}
        <Dialog open={messageDialogOpen} onClose={() => setMessageDialogOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle>메시지 보내기</DialogTitle>
          <DialogContent dividers>
            <Box sx={{ mb: 3 }}>
              <Alert severity="info">
                {selectedCustomers.length > 0 ? `${selectedCustomers.length}명의 고객에게 메시지를 보냅니다.` : '선택된 고객이 없습니다.'}
              </Alert>
            </Box>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <FormControl component="fieldset">
                  <Typography variant="subtitle2" gutterBottom>
                    메시지 유형
                  </Typography>
                  <RadioGroup row defaultValue="email">
                    <FormControlLabel value="email" control={<Radio />} label="이메일" />
                    <FormControlLabel value="sms" control={<Radio />} label="SMS" />
                    <FormControlLabel value="push" control={<Radio />} label="푸시 알림" />
                  </RadioGroup>
                </FormControl>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="제목"
                  placeholder="메시지 제목을 입력하세요"
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={6}
                  label="내용"
                  placeholder="메시지 내용을 입력하세요"
                />
              </Grid>
              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>템플릿 선택</InputLabel>
                  <Select label="템플릿 선택">
                    <MenuItem value="">직접 입력</MenuItem>
                    <MenuItem value="welcome">환영 메시지</MenuItem>
                    <MenuItem value="promotion">프로모션 안내</MenuItem>
                    <MenuItem value="dormant">휴면 고객 복귀</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setMessageDialogOpen(false)}>취소</Button>
            <Button variant="contained" startIcon={<Send />} onClick={() => {
              toast.success('메시지가 전송되었습니다.')
              setMessageDialogOpen(false)
            }}>
              전송
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </LocalizationProvider>
  )
}

export default Customers