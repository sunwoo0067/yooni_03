import React, { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Box,
  Typography,
  Tabs,
  Tab,
  Grid,
  Chip,
  Divider,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material'
import {
  Timeline,
  TimelineItem,
  TimelineSeparator,
  TimelineDot,
  TimelineConnector,
  TimelineContent,
} from '@mui/lab'
import {
  Close,
  Info,
  TrendingUp,
  History,
  Inventory,
  CloudSync,
  AttachMoney,
  Add,
  Remove,
  Edit,
} from '@mui/icons-material'
import { Product } from '@/types/product'
import { formatCurrency, formatNumber, formatDate } from '@utils/format'
import {
  LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend as RechartsLegend,
  ResponsiveContainer
} from 'recharts'

interface ProductDetailDialogProps {
  open: boolean
  onClose: () => void
  product: Product | null
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
      id={`product-tabpanel-${index}`}
      aria-labelledby={`product-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  )
}

const ProductDetailDialog: React.FC<ProductDetailDialogProps> = ({ open, onClose, product }) => {
  const [tabValue, setTabValue] = useState(0)

  if (!product) return null

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
  }

  // Mock data for charts and history
  const salesChartData = [
    { month: '1월', 판매량: 65 },
    { month: '2월', 판매량: 59 },
    { month: '3월', 판매량: 80 },
    { month: '4월', 판매량: 81 },
    { month: '5월', 판매량: 56 },
    { month: '6월', 판매량: 55 },
  ]

  const priceHistory = [
    { date: '2024-01-15', oldPrice: 25000, newPrice: 28000, changedBy: '시스템' },
    { date: '2024-01-01', oldPrice: 30000, newPrice: 25000, changedBy: '관리자' },
    { date: '2023-12-20', oldPrice: 35000, newPrice: 30000, changedBy: '자동화' },
  ]

  const stockHistory = [
    { date: '2024-01-20', type: 'add', quantity: 50, note: '재고 보충', balance: 150 },
    { date: '2024-01-18', type: 'remove', quantity: 20, note: '판매', balance: 100 },
    { date: '2024-01-15', type: 'add', quantity: 100, note: '초기 입고', balance: 120 },
    { date: '2024-01-10', type: 'remove', quantity: 30, note: '판매', balance: 20 },
  ]

  const platformStatus = [
    { platform: '쿠팡', status: 'synced', lastSync: '2024-01-20 14:30', listingId: 'CP123456' },
    { platform: '네이버', status: 'synced', lastSync: '2024-01-20 14:25', listingId: 'NV789012' },
    { platform: '11번가', status: 'pending', lastSync: '-', listingId: '-' },
    { platform: 'G마켓', status: 'error', lastSync: '2024-01-19 10:00', listingId: 'GM345678' },
  ]

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box display="flex" alignItems="center" gap={2}>
            {product.main_image_url && (
              <img
                src={product.main_image_url}
                alt={product.name}
                style={{ width: 60, height: 60, borderRadius: 8, objectFit: 'cover' }}
              />
            )}
            <Box>
              <Typography variant="h6">{product.name}</Typography>
              <Typography variant="body2" color="text.secondary">
                SKU: {product.sku || 'N/A'}
              </Typography>
            </Box>
          </Box>
          <IconButton onClick={onClose}>
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>

      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="product detail tabs">
          <Tab icon={<Info />} label="개요" />
          <Tab icon={<TrendingUp />} label="판매 통계" />
          <Tab icon={<History />} label="가격 히스토리" />
          <Tab icon={<Inventory />} label="재고 변동" />
          <Tab icon={<CloudSync />} label="플랫폼 연동" />
        </Tabs>
      </Box>

      <DialogContent>
        <TabPanel value={tabValue} index={0}>
          {/* Overview Tab */}
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                기본 정보
              </Typography>
              <Box sx={{ mb: 3 }}>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">카테고리</Typography>
                    <Typography variant="body1">{product.category || '미분류'}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">브랜드</Typography>
                    <Typography variant="body1">{product.brand || '-'}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">바코드</Typography>
                    <Typography variant="body1">{product.barcode || '-'}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">상태</Typography>
                    <Chip
                      label={
                        product.status === 'active' ? '판매중' :
                        product.status === 'inactive' ? '판매중지' :
                        product.status === 'out_of_stock' ? '품절' : '단종'
                      }
                      size="small"
                      color={
                        product.status === 'active' ? 'success' :
                        product.status === 'inactive' ? 'warning' :
                        product.status === 'out_of_stock' ? 'error' : 'default'
                      }
                    />
                  </Grid>
                </Grid>
              </Box>

              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                가격 정보
              </Typography>
              <Box sx={{ mb: 3 }}>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">원가</Typography>
                    <Typography variant="body1">{formatCurrency(product.cost || 0)}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">판매가</Typography>
                    <Typography variant="body1" fontWeight={600}>
                      {formatCurrency(product.price)}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">도매가</Typography>
                    <Typography variant="body1">
                      {formatCurrency(product.wholesale_price || 0)}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">마진율</Typography>
                    <Typography 
                      variant="body1"
                      color={
                        product.cost && product.price
                          ? ((product.price - product.cost) / product.price) * 100 >= 30
                            ? 'success.main'
                            : ((product.price - product.cost) / product.price) * 100 >= 20
                            ? 'warning.main'
                            : 'error.main'
                          : 'text.primary'
                      }
                    >
                      {product.cost && product.price
                        ? `${(((product.price - product.cost) / product.price) * 100).toFixed(1)}%`
                        : '-'}
                    </Typography>
                  </Grid>
                </Grid>
              </Box>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                재고 정보
              </Typography>
              <Box sx={{ mb: 3 }}>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">현재 재고</Typography>
                    <Typography 
                      variant="body1" 
                      fontWeight={600}
                      color={
                        product.stock_quantity === 0 ? 'error.main' :
                        product.stock_quantity < 10 ? 'warning.main' : 'text.primary'
                      }
                    >
                      {formatNumber(product.stock_quantity)}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">최소 재고</Typography>
                    <Typography variant="body1">{formatNumber(product.min_stock || 0)}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">최대 재고</Typography>
                    <Typography variant="body1">{formatNumber(product.max_stock || 1000)}</Typography>
                  </Grid>
                </Grid>
              </Box>

              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                물류 정보
              </Typography>
              <Box>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">무게</Typography>
                    <Typography variant="body1">{product.weight || 0} kg</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">크기</Typography>
                    <Typography variant="body1">
                      {product.dimensions?.length || 0} × {product.dimensions?.width || 0} × {product.dimensions?.height || 0} cm
                    </Typography>
                  </Grid>
                </Grid>
              </Box>
            </Grid>

            {product.description && (
              <Grid item xs={12}>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  상품 설명
                </Typography>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                  {product.description}
                </Typography>
              </Grid>
            )}

            {product.tags && product.tags.length > 0 && (
              <Grid item xs={12}>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  태그
                </Typography>
                <Box display="flex" gap={1} flexWrap="wrap">
                  {product.tags.map((tag) => (
                    <Chip key={tag} label={tag} size="small" />
                  ))}
                </Box>
              </Grid>
            )}
          </Grid>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          {/* Sales Statistics Tab */}
          <Box sx={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={salesChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <RechartsTooltip />
                <RechartsLegend />
                <Line 
                  type="monotone" 
                  dataKey="판매량" 
                  stroke="#4BC0C0"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </Box>
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          {/* Price History Tab */}
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>날짜</TableCell>
                  <TableCell align="right">이전 가격</TableCell>
                  <TableCell align="right">변경 가격</TableCell>
                  <TableCell align="right">변동률</TableCell>
                  <TableCell>변경자</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {priceHistory.map((history, index) => {
                  const changeRate = ((history.newPrice - history.oldPrice) / history.oldPrice) * 100
                  return (
                    <TableRow key={index}>
                      <TableCell>{history.date}</TableCell>
                      <TableCell align="right">{formatCurrency(history.oldPrice)}</TableCell>
                      <TableCell align="right">{formatCurrency(history.newPrice)}</TableCell>
                      <TableCell align="right">
                        <Chip
                          label={`${changeRate > 0 ? '+' : ''}${changeRate.toFixed(1)}%`}
                          size="small"
                          color={changeRate > 0 ? 'error' : 'success'}
                        />
                      </TableCell>
                      <TableCell>{history.changedBy}</TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          {/* Stock History Tab */}
          <Timeline>
            {stockHistory.map((history, index) => (
              <TimelineItem key={index}>
                <TimelineSeparator>
                  <TimelineDot color={history.type === 'add' ? 'success' : 'error'}>
                    {history.type === 'add' ? <Add /> : <Remove />}
                  </TimelineDot>
                  {index < stockHistory.length - 1 && <TimelineConnector />}
                </TimelineSeparator>
                <TimelineContent>
                  <Paper elevation={3} sx={{ p: 2 }}>
                    <Typography variant="body2" color="text.secondary">
                      {history.date}
                    </Typography>
                    <Typography variant="body1">
                      {history.type === 'add' ? '입고' : '출고'}: {formatNumber(history.quantity)}개
                    </Typography>
                    <Typography variant="body2">
                      사유: {history.note}
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      잔량: {formatNumber(history.balance)}개
                    </Typography>
                  </Paper>
                </TimelineContent>
              </TimelineItem>
            ))}
          </Timeline>
        </TabPanel>

        <TabPanel value={tabValue} index={4}>
          {/* Platform Sync Tab */}
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>플랫폼</TableCell>
                  <TableCell>상태</TableCell>
                  <TableCell>마지막 동기화</TableCell>
                  <TableCell>리스팅 ID</TableCell>
                  <TableCell align="right">작업</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {platformStatus.map((platform) => (
                  <TableRow key={platform.platform}>
                    <TableCell>{platform.platform}</TableCell>
                    <TableCell>
                      <Chip
                        label={
                          platform.status === 'synced' ? '동기화됨' :
                          platform.status === 'pending' ? '대기중' : '오류'
                        }
                        size="small"
                        color={
                          platform.status === 'synced' ? 'success' :
                          platform.status === 'pending' ? 'warning' : 'error'
                        }
                      />
                    </TableCell>
                    <TableCell>{platform.lastSync}</TableCell>
                    <TableCell>{platform.listingId}</TableCell>
                    <TableCell align="right">
                      <IconButton size="small">
                        <CloudSync />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>
      </DialogContent>
    </Dialog>
  )
}

export default ProductDetailDialog