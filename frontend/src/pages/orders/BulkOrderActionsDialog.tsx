import React, { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  FormControl,
  Select,
  MenuItem,
  TextField,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Chip,
  CircularProgress,
} from '@mui/material'
import {
  Receipt,
  LocalShipping,
  Print,
  Email,
  Cancel,
  CheckCircle,
  Download,
} from '@mui/icons-material'
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
}

interface BulkOrderActionsDialogProps {
  open: boolean
  onClose: () => void
  selectedOrders: Order[]
}

const BulkOrderActionsDialog: React.FC<BulkOrderActionsDialogProps> = ({
  open,
  onClose,
  selectedOrders,
}) => {
  const [action, setAction] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [statusUpdate, setStatusUpdate] = useState<Order['status'] | ''>('')
  const [emailTemplate, setEmailTemplate] = useState('')
  const [cancelReason, setCancelReason] = useState('')

  const handleExecuteAction = async () => {
    if (!action) {
      toast.error('작업을 선택해주세요.')
      return
    }

    setLoading(true)

    try {
      switch (action) {
        case 'updateStatus':
          if (!statusUpdate) {
            toast.error('변경할 상태를 선택해주세요.')
            return
          }
          // Simulate API call
          await new Promise(resolve => setTimeout(resolve, 1000))
          toast.success(`${selectedOrders.length}개 주문의 상태가 업데이트되었습니다.`)
          break

        case 'printInvoices':
          // Simulate printing
          await new Promise(resolve => setTimeout(resolve, 1000))
          toast.success(`${selectedOrders.length}개 주문의 송장을 인쇄합니다.`)
          break

        case 'sendEmails':
          if (!emailTemplate) {
            toast.error('이메일 내용을 입력해주세요.')
            return
          }
          // Simulate email sending
          await new Promise(resolve => setTimeout(resolve, 1500))
          toast.success(`${selectedOrders.length}명의 고객에게 이메일을 발송했습니다.`)
          break

        case 'exportOrders':
          // Simulate export
          await new Promise(resolve => setTimeout(resolve, 800))
          toast.success('주문 목록을 내보냈습니다.')
          break

        case 'cancelOrders':
          if (!cancelReason) {
            toast.error('취소 사유를 입력해주세요.')
            return
          }
          // Simulate cancellation
          await new Promise(resolve => setTimeout(resolve, 1200))
          toast.success(`${selectedOrders.length}개 주문이 취소되었습니다.`)
          break

        case 'processShipping':
          // Simulate shipping process
          await new Promise(resolve => setTimeout(resolve, 1000))
          toast.success(`${selectedOrders.length}개 주문의 배송 처리를 시작합니다.`)
          break
      }

      onClose()
    } catch (error) {
      toast.error('작업 처리 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const getActionContent = () => {
    switch (action) {
      case 'updateStatus':
        return (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              선택한 주문들의 상태를 일괄 변경합니다.
            </Typography>
            <FormControl fullWidth sx={{ mt: 2 }}>
              <Select
                value={statusUpdate}
                onChange={(e) => setStatusUpdate(e.target.value as Order['status'])}
                displayEmpty
              >
                <MenuItem value="">상태 선택</MenuItem>
                <MenuItem value="confirmed">주문확정</MenuItem>
                <MenuItem value="processing">상품준비</MenuItem>
                <MenuItem value="shipped">배송중</MenuItem>
                <MenuItem value="delivered">배송완료</MenuItem>
                <MenuItem value="cancelled">취소</MenuItem>
                <MenuItem value="refunded">환불</MenuItem>
              </Select>
            </FormControl>
          </Box>
        )

      case 'printInvoices':
        return (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              선택한 {selectedOrders.length}개 주문의 송장을 인쇄합니다.
            </Typography>
            <Alert severity="info" sx={{ mt: 2 }}>
              프린터가 연결되어 있는지 확인해주세요.
            </Alert>
          </Box>
        )

      case 'sendEmails':
        return (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              고객에게 발송할 이메일을 작성하세요.
            </Typography>
            <TextField
              fullWidth
              multiline
              rows={4}
              placeholder="이메일 내용을 입력하세요..."
              value={emailTemplate}
              onChange={(e) => setEmailTemplate(e.target.value)}
              sx={{ mt: 2 }}
            />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              {selectedOrders.length}명의 고객에게 발송됩니다.
            </Typography>
          </Box>
        )

      case 'exportOrders':
        return (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              선택한 주문을 Excel 파일로 내보냅니다.
            </Typography>
            <Alert severity="success" sx={{ mt: 2 }}>
              주문번호, 고객정보, 상품정보, 배송정보가 포함됩니다.
            </Alert>
          </Box>
        )

      case 'cancelOrders':
        return (
          <Box sx={{ mt: 2 }}>
            <Alert severity="warning" sx={{ mb: 2 }}>
              주문 취소는 되돌릴 수 없습니다. 신중하게 진행해주세요.
            </Alert>
            <TextField
              fullWidth
              multiline
              rows={3}
              placeholder="취소 사유를 입력하세요..."
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
            />
          </Box>
        )

      case 'processShipping':
        return (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              선택한 주문들의 배송 처리를 시작합니다.
            </Typography>
            <Alert severity="info" sx={{ mt: 2 }}>
              배송 정보 입력 화면으로 이동합니다.
            </Alert>
          </Box>
        )

      default:
        return null
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Typography variant="h6">일괄 작업</Typography>
        <Typography variant="body2" color="text.secondary">
          {selectedOrders.length}개 주문 선택됨
        </Typography>
      </DialogTitle>

      <DialogContent dividers>
        {/* Selected Orders Summary */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            선택된 주문
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {selectedOrders.slice(0, 5).map((order) => (
              <Chip
                key={order.id}
                label={order.orderNumber}
                size="small"
                variant="outlined"
              />
            ))}
            {selectedOrders.length > 5 && (
              <Chip
                label={`+${selectedOrders.length - 5}개`}
                size="small"
                color="primary"
              />
            )}
          </Box>
        </Box>

        <Divider sx={{ mb: 3 }} />

        {/* Action Selection */}
        <Typography variant="subtitle2" gutterBottom>
          작업 선택
        </Typography>
        <List>
          <ListItem
            button
            selected={action === 'updateStatus'}
            onClick={() => setAction('updateStatus')}
          >
            <ListItemIcon>
              <CheckCircle color={action === 'updateStatus' ? 'primary' : 'inherit'} />
            </ListItemIcon>
            <ListItemText
              primary="상태 일괄 변경"
              secondary="주문 상태를 한번에 변경합니다"
            />
          </ListItem>

          <ListItem
            button
            selected={action === 'printInvoices'}
            onClick={() => setAction('printInvoices')}
          >
            <ListItemIcon>
              <Print color={action === 'printInvoices' ? 'primary' : 'inherit'} />
            </ListItemIcon>
            <ListItemText
              primary="송장 일괄 인쇄"
              secondary="선택한 주문의 송장을 인쇄합니다"
            />
          </ListItem>

          <ListItem
            button
            selected={action === 'sendEmails'}
            onClick={() => setAction('sendEmails')}
          >
            <ListItemIcon>
              <Email color={action === 'sendEmails' ? 'primary' : 'inherit'} />
            </ListItemIcon>
            <ListItemText
              primary="이메일 일괄 발송"
              secondary="고객에게 이메일을 발송합니다"
            />
          </ListItem>

          <ListItem
            button
            selected={action === 'exportOrders'}
            onClick={() => setAction('exportOrders')}
          >
            <ListItemIcon>
              <Download color={action === 'exportOrders' ? 'primary' : 'inherit'} />
            </ListItemIcon>
            <ListItemText
              primary="주문 내보내기"
              secondary="Excel 파일로 내보냅니다"
            />
          </ListItem>

          <ListItem
            button
            selected={action === 'processShipping'}
            onClick={() => setAction('processShipping')}
          >
            <ListItemIcon>
              <LocalShipping color={action === 'processShipping' ? 'primary' : 'inherit'} />
            </ListItemIcon>
            <ListItemText
              primary="배송 일괄 처리"
              secondary="배송 정보를 입력합니다"
            />
          </ListItem>

          <ListItem
            button
            selected={action === 'cancelOrders'}
            onClick={() => setAction('cancelOrders')}
          >
            <ListItemIcon>
              <Cancel color={action === 'cancelOrders' ? 'error' : 'inherit'} />
            </ListItemIcon>
            <ListItemText
              primary="주문 일괄 취소"
              secondary="선택한 주문을 취소합니다"
              primaryTypographyProps={{
                color: action === 'cancelOrders' ? 'error' : 'inherit',
              }}
            />
          </ListItem>
        </List>

        {/* Action Content */}
        {getActionContent()}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          취소
        </Button>
        <Button
          variant="contained"
          onClick={handleExecuteAction}
          disabled={!action || loading}
          color={action === 'cancelOrders' ? 'error' : 'primary'}
          startIcon={loading ? <CircularProgress size={20} /> : null}
        >
          {loading ? '처리중...' : '실행'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default BulkOrderActionsDialog