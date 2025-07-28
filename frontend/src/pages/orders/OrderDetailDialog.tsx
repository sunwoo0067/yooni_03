import React, { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Box,
  Typography,
  Grid,
  Divider,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Chip,
  Alert,
  FormControl,
  Select,
  MenuItem,
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
  Receipt,
  LocalShipping,
  Person,
  LocationOn,
  Payment,
  Print,
  Email,
  CheckCircle,
  AccessTime,
  Cancel,
} from '@mui/icons-material'
import { formatCurrency, formatDate } from '@utils/format'
import { toast } from 'react-hot-toast'

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

interface OrderDetailDialogProps {
  open: boolean
  onClose: () => void
  order: Order | null
  onStatusUpdate: (order: Order, status: Order['status']) => void
}

const OrderDetailDialog: React.FC<OrderDetailDialogProps> = ({
  open,
  onClose,
  order,
  onStatusUpdate,
}) => {
  const [newStatus, setNewStatus] = useState<Order['status'] | ''>('')

  if (!order) return null

  const handleStatusChange = () => {
    if (newStatus && newStatus !== order.status) {
      onStatusUpdate(order, newStatus)
      toast.success('주문 상태가 업데이트되었습니다.')
      setNewStatus('')
    }
  }

  const handlePrint = () => {
    window.print()
  }

  const handleSendEmail = () => {
    toast.success('고객에게 이메일을 발송했습니다.')
  }

  const getStatusColor = (status: Order['status']) => {
    const colors = {
      pending: 'warning',
      confirmed: 'info',
      processing: 'info',
      shipped: 'primary',
      delivered: 'success',
      cancelled: 'error',
      refunded: 'error',
    }
    return colors[status] as any
  }

  const getStatusIcon = (status: Order['status']) => {
    const icons = {
      pending: <AccessTime />,
      confirmed: <CheckCircle />,
      processing: <Receipt />,
      shipped: <LocalShipping />,
      delivered: <CheckCircle />,
      cancelled: <Cancel />,
      refunded: <Cancel />,
    }
    return icons[status]
  }

  const statusHistory = [
    { status: 'pending', label: '주문 접수', date: order.orderDate },
    ...(order.status !== 'pending' ? [{ status: 'confirmed', label: '주문 확정', date: order.orderDate }] : []),
    ...(order.status === 'processing' || order.status === 'shipped' || order.status === 'delivered' 
      ? [{ status: 'processing', label: '상품 준비', date: order.orderDate }] : []),
    ...(order.shippedDate ? [{ status: 'shipped', label: '배송 시작', date: order.shippedDate }] : []),
    ...(order.deliveredDate ? [{ status: 'delivered', label: '배송 완료', date: order.deliveredDate }] : []),
  ]

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box display="flex" alignItems="center" gap={2}>
            <Typography variant="h6">주문 상세</Typography>
            <Chip
              label={order.orderNumber}
              color="primary"
              variant="outlined"
            />
          </Box>
          <Box display="flex" gap={1}>
            <Button
              startIcon={<Print />}
              onClick={handlePrint}
              size="small"
            >
              인쇄
            </Button>
            <Button
              startIcon={<Email />}
              onClick={handleSendEmail}
              size="small"
            >
              이메일
            </Button>
            <IconButton onClick={onClose} size="small">
              <Close />
            </IconButton>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        <Grid container spacing={3}>
          {/* Status Update */}
          <Grid item xs={12}>
            <Alert severity="info" icon={getStatusIcon(order.status)}>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="subtitle2">
                    현재 상태: {order.status === 'pending' ? '주문확인' :
                      order.status === 'confirmed' ? '주문확정' :
                      order.status === 'processing' ? '상품준비' :
                      order.status === 'shipped' ? '배송중' :
                      order.status === 'delivered' ? '배송완료' :
                      order.status === 'cancelled' ? '취소' : '환불'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    마지막 업데이트: {formatDate(order.orderDate)}
                  </Typography>
                </Box>
                <Box display="flex" gap={1} alignItems="center">
                  <FormControl size="small" sx={{ minWidth: 120 }}>
                    <Select
                      value={newStatus}
                      onChange={(e) => setNewStatus(e.target.value as Order['status'])}
                      displayEmpty
                    >
                      <MenuItem value="">상태 변경</MenuItem>
                      <MenuItem value="confirmed">주문확정</MenuItem>
                      <MenuItem value="processing">상품준비</MenuItem>
                      <MenuItem value="shipped">배송중</MenuItem>
                      <MenuItem value="delivered">배송완료</MenuItem>
                      <MenuItem value="cancelled">취소</MenuItem>
                      <MenuItem value="refunded">환불</MenuItem>
                    </Select>
                  </FormControl>
                  <Button
                    variant="contained"
                    size="small"
                    onClick={handleStatusChange}
                    disabled={!newStatus || newStatus === order.status}
                  >
                    업데이트
                  </Button>
                </Box>
              </Box>
            </Alert>
          </Grid>

          {/* Order Info */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2 }}>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <Receipt color="primary" />
                <Typography variant="h6">주문 정보</Typography>
              </Box>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">주문일시</Typography>
                  <Typography variant="body2">{formatDate(order.orderDate)}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">플랫폼</Typography>
                  <Typography variant="body2">{order.platform}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">플랫폼 주문번호</Typography>
                  <Typography variant="body2">{order.platformOrderId}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">결제 방법</Typography>
                  <Typography variant="body2">{order.paymentMethod}</Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="caption" color="text.secondary">결제 상태</Typography>
                  <Box mt={0.5}>
                    <Chip
                      label={
                        order.paymentStatus === 'pending' ? '대기' :
                        order.paymentStatus === 'paid' ? '완료' :
                        order.paymentStatus === 'failed' ? '실패' : '환불'
                      }
                      size="small"
                      color={
                        order.paymentStatus === 'paid' ? 'success' :
                        order.paymentStatus === 'pending' ? 'warning' : 'error'
                      }
                    />
                  </Box>
                </Grid>
              </Grid>
            </Paper>
          </Grid>

          {/* Customer Info */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2 }}>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <Person color="primary" />
                <Typography variant="h6">고객 정보</Typography>
              </Box>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <Typography variant="caption" color="text.secondary">이름</Typography>
                  <Typography variant="body2">{order.customer.name}</Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="caption" color="text.secondary">연락처</Typography>
                  <Typography variant="body2">{order.customer.phone}</Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="caption" color="text.secondary">이메일</Typography>
                  <Typography variant="body2">{order.customer.email}</Typography>
                </Grid>
              </Grid>
            </Paper>
          </Grid>

          {/* Shipping Info */}
          <Grid item xs={12}>
            <Paper sx={{ p: 2 }}>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <LocationOn color="primary" />
                <Typography variant="h6">배송 정보</Typography>
              </Box>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="caption" color="text.secondary">배송지</Typography>
                  <Typography variant="body2">
                    {order.shippingAddress.street}<br />
                    {order.shippingAddress.city} {order.shippingAddress.state} {order.shippingAddress.zipCode}
                  </Typography>
                </Grid>
                {order.trackingNumber && (
                  <>
                    <Grid item xs={12} md={3}>
                      <Typography variant="caption" color="text.secondary">택배사</Typography>
                      <Typography variant="body2">{order.shippingCarrier}</Typography>
                    </Grid>
                    <Grid item xs={12} md={3}>
                      <Typography variant="caption" color="text.secondary">운송장번호</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {order.trackingNumber}
                      </Typography>
                    </Grid>
                  </>
                )}
              </Grid>
            </Paper>
          </Grid>

          {/* Order Items */}
          <Grid item xs={12}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" mb={2}>주문 상품</Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>상품명</TableCell>
                      <TableCell>SKU</TableCell>
                      <TableCell align="right">단가</TableCell>
                      <TableCell align="center">수량</TableCell>
                      <TableCell align="right">소계</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {order.items.map((item, index) => (
                      <TableRow key={index}>
                        <TableCell>{item.productName}</TableCell>
                        <TableCell>{item.sku}</TableCell>
                        <TableCell align="right">{formatCurrency(item.price)}</TableCell>
                        <TableCell align="center">{item.quantity}</TableCell>
                        <TableCell align="right">{formatCurrency(item.subtotal)}</TableCell>
                      </TableRow>
                    ))}
                    <TableRow>
                      <TableCell colSpan={4} align="right">
                        <Typography variant="subtitle1" fontWeight={600}>
                          총 금액
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="subtitle1" fontWeight={600} color="primary">
                          {formatCurrency(order.totalAmount)}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>

          {/* Order Timeline */}
          <Grid item xs={12}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" mb={2}>주문 처리 내역</Typography>
              <Timeline>
                {statusHistory.map((item, index) => (
                  <TimelineItem key={index}>
                    <TimelineSeparator>
                      <TimelineDot color={getStatusColor(item.status as Order['status'])}>
                        {getStatusIcon(item.status as Order['status'])}
                      </TimelineDot>
                      {index < statusHistory.length - 1 && <TimelineConnector />}
                    </TimelineSeparator>
                    <TimelineContent>
                      <Typography variant="body2" fontWeight={500}>
                        {item.label}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {formatDate(item.date)}
                      </Typography>
                    </TimelineContent>
                  </TimelineItem>
                ))}
              </Timeline>
            </Paper>
          </Grid>

          {/* Notes */}
          {order.notes && (
            <Grid item xs={12}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" mb={2}>메모</Typography>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                  {order.notes}
                </Typography>
              </Paper>
            </Grid>
          )}
        </Grid>
      </DialogContent>
    </Dialog>
  )
}

export default OrderDetailDialog