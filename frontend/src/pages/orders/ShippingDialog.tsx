import React, { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  TextField,
  Grid,
  FormControl,
  Select,
  MenuItem,
  InputLabel,
  Alert,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Checkbox,
  Divider,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material'
import {
  LocalShipping,
  Inventory,
  Print,
  QrCode,
  ContentCopy,
  CheckCircle,
  Warning,
  Info,
} from '@mui/icons-material'
import { toast } from 'react-hot-toast'
import { formatCurrency } from '@utils/format'

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
  shippingAddress: {
    street: string
    city: string
    state: string
    zipCode: string
  }
}

interface ShippingDialogProps {
  open: boolean
  onClose: () => void
  order: Order | null
}

const ShippingDialog: React.FC<ShippingDialogProps> = ({
  open,
  onClose,
  order,
}) => {
  const [activeStep, setActiveStep] = useState(0)
  const [shippingData, setShippingData] = useState({
    carrier: '',
    trackingNumber: '',
    shippingMethod: '',
    packageWeight: '',
    packageDimensions: {
      length: '',
      width: '',
      height: '',
    },
    shippingCost: '',
    notes: '',
  })
  const [checkedItems, setCheckedItems] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  if (!order) return null

  const steps = [
    '상품 확인',
    '배송 정보 입력',
    '송장 출력',
    '배송 완료',
  ]

  const carriers = [
    { value: 'cj', label: 'CJ대한통운' },
    { value: 'hanjin', label: '한진택배' },
    { value: 'lotte', label: '롯데택배' },
    { value: 'post', label: '우체국택배' },
    { value: 'logen', label: '로젠택배' },
    { value: 'cvsnet', label: 'GS편의점택배' },
    { value: 'cupost', label: 'CU편의점택배' },
  ]

  const shippingMethods = [
    { value: 'standard', label: '일반배송' },
    { value: 'express', label: '특급배송' },
    { value: 'overnight', label: '익일배송' },
    { value: 'sameday', label: '당일배송' },
  ]

  React.useEffect(() => {
    if (order) {
      setCheckedItems(order.items.map(item => item.productId))
    }
  }, [order])

  const handleNext = () => {
    if (activeStep === 0 && checkedItems.length === 0) {
      toast.error('배송할 상품을 선택해주세요.')
      return
    }
    if (activeStep === 1 && (!shippingData.carrier || !shippingData.trackingNumber)) {
      toast.error('택배사와 운송장번호를 입력해주세요.')
      return
    }
    setActiveStep((prevActiveStep) => prevActiveStep + 1)
  }

  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1)
  }

  const handleComplete = async () => {
    setLoading(true)
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1500))
      toast.success('배송 처리가 완료되었습니다.')
      onClose()
    } catch (error) {
      toast.error('배송 처리 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const handleItemToggle = (productId: string) => {
    setCheckedItems(prev => {
      if (prev.includes(productId)) {
        return prev.filter(id => id !== productId)
      }
      return [...prev, productId]
    })
  }

  const handleCopyTrackingNumber = () => {
    navigator.clipboard.writeText(shippingData.trackingNumber)
    toast.success('운송장번호가 복사되었습니다.')
  }

  const handlePrintLabel = () => {
    toast.success('배송 라벨을 인쇄합니다.')
  }

  const getStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <Box>
            <Alert severity="info" sx={{ mb: 2 }}>
              배송할 상품을 선택하세요. 일부 상품만 배송할 수 있습니다.
            </Alert>
            <List>
              {order.items.map((item) => (
                <ListItem key={item.productId} divider>
                  <ListItemIcon>
                    <Checkbox
                      checked={checkedItems.includes(item.productId)}
                      onChange={() => handleItemToggle(item.productId)}
                    />
                  </ListItemIcon>
                  <ListItemText
                    primary={item.productName}
                    secondary={`SKU: ${item.sku} | 수량: ${item.quantity}개`}
                  />
                  <Typography variant="body2" color="text.secondary">
                    {formatCurrency(item.subtotal)}
                  </Typography>
                </ListItem>
              ))}
            </List>
            <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
              <Typography variant="subtitle2">
                선택된 상품: {checkedItems.length}개 / {order.items.length}개
              </Typography>
            </Box>
          </Box>
        )

      case 1:
        return (
          <Box>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth required>
                  <InputLabel>택배사</InputLabel>
                  <Select
                    value={shippingData.carrier}
                    onChange={(e) => setShippingData({ ...shippingData, carrier: e.target.value })}
                    label="택배사"
                  >
                    {carriers.map((carrier) => (
                      <MenuItem key={carrier.value} value={carrier.value}>
                        {carrier.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  required
                  label="운송장번호"
                  value={shippingData.trackingNumber}
                  onChange={(e) => setShippingData({ ...shippingData, trackingNumber: e.target.value })}
                  placeholder="123456789012"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>배송방법</InputLabel>
                  <Select
                    value={shippingData.shippingMethod}
                    onChange={(e) => setShippingData({ ...shippingData, shippingMethod: e.target.value })}
                    label="배송방법"
                  >
                    {shippingMethods.map((method) => (
                      <MenuItem key={method.value} value={method.value}>
                        {method.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="배송비"
                  type="number"
                  value={shippingData.shippingCost}
                  onChange={(e) => setShippingData({ ...shippingData, shippingCost: e.target.value })}
                  InputProps={{
                    startAdornment: '₩',
                  }}
                />
              </Grid>
              <Grid item xs={12}>
                <Typography variant="subtitle2" gutterBottom>
                  포장 정보 (선택)
                </Typography>
              </Grid>
              <Grid item xs={12} md={3}>
                <TextField
                  fullWidth
                  label="무게(kg)"
                  type="number"
                  value={shippingData.packageWeight}
                  onChange={(e) => setShippingData({ ...shippingData, packageWeight: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <TextField
                  fullWidth
                  label="길이(cm)"
                  type="number"
                  value={shippingData.packageDimensions.length}
                  onChange={(e) => setShippingData({
                    ...shippingData,
                    packageDimensions: { ...shippingData.packageDimensions, length: e.target.value }
                  })}
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <TextField
                  fullWidth
                  label="너비(cm)"
                  type="number"
                  value={shippingData.packageDimensions.width}
                  onChange={(e) => setShippingData({
                    ...shippingData,
                    packageDimensions: { ...shippingData.packageDimensions, width: e.target.value }
                  })}
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <TextField
                  fullWidth
                  label="높이(cm)"
                  type="number"
                  value={shippingData.packageDimensions.height}
                  onChange={(e) => setShippingData({
                    ...shippingData,
                    packageDimensions: { ...shippingData.packageDimensions, height: e.target.value }
                  })}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={2}
                  label="배송 메모"
                  value={shippingData.notes}
                  onChange={(e) => setShippingData({ ...shippingData, notes: e.target.value })}
                  placeholder="배송 시 주의사항이나 메모를 입력하세요"
                />
              </Grid>
            </Grid>
          </Box>
        )

      case 2:
        return (
          <Box>
            <Paper sx={{ p: 3, mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                배송 정보 확인
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <LocalShipping color="primary" />
                    <Typography variant="subtitle1">
                      {carriers.find(c => c.value === shippingData.carrier)?.label}
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      운송장번호:
                    </Typography>
                    <Typography variant="h6">
                      {shippingData.trackingNumber}
                    </Typography>
                    <Tooltip title="복사">
                      <IconButton size="small" onClick={handleCopyTrackingNumber}>
                        <ContentCopy fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </Grid>
                <Grid item xs={12}>
                  <Divider sx={{ my: 1 }} />
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="subtitle2" gutterBottom>
                    받는 사람
                  </Typography>
                  <Typography variant="body2">
                    {order.customer.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {order.shippingAddress.street}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {order.shippingAddress.city} {order.shippingAddress.state} {order.shippingAddress.zipCode}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {order.customer.phone}
                  </Typography>
                </Grid>
              </Grid>
            </Paper>

            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
              <Button
                variant="outlined"
                startIcon={<Print />}
                onClick={handlePrintLabel}
                size="large"
              >
                송장 출력
              </Button>
              <Button
                variant="outlined"
                startIcon={<QrCode />}
                size="large"
              >
                QR코드 출력
              </Button>
            </Box>

            <Alert severity="warning" sx={{ mt: 2 }}>
              송장을 출력하여 상품에 부착한 후 다음 단계로 진행하세요.
            </Alert>
          </Box>
        )

      case 3:
        return (
          <Box sx={{ textAlign: 'center', py: 3 }}>
            <CheckCircle color="success" sx={{ fontSize: 80, mb: 2 }} />
            <Typography variant="h5" gutterBottom>
              배송 처리 완료!
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
              주문번호 {order.orderNumber}의 배송 처리가 완료되었습니다.
            </Typography>
            <Paper sx={{ p: 2, mt: 3, bgcolor: 'grey.50' }}>
              <Typography variant="subtitle2" gutterBottom>
                다음 단계
              </Typography>
              <List dense>
                <ListItem>
                  <ListItemIcon>
                    <Info color="primary" />
                  </ListItemIcon>
                  <ListItemText
                    primary="고객에게 배송 시작 알림이 발송되었습니다"
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <LocalShipping color="primary" />
                  </ListItemIcon>
                  <ListItemText
                    primary="택배사에 픽업 요청이 전달되었습니다"
                  />
                </ListItem>
              </List>
            </Paper>
          </Box>
        )

      default:
        return null
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={2}>
          <LocalShipping color="primary" />
          <Box>
            <Typography variant="h6">배송 처리</Typography>
            <Typography variant="body2" color="text.secondary">
              주문번호: {order.orderNumber}
            </Typography>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        <Stepper activeStep={activeStep} orientation="vertical">
          {steps.map((label, index) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
              <StepContent>
                {getStepContent(index)}
                <Box sx={{ mt: 3, display: 'flex', gap: 1 }}>
                  <Button
                    disabled={index === 0}
                    onClick={handleBack}
                  >
                    이전
                  </Button>
                  {index === steps.length - 1 ? (
                    <Button
                      variant="contained"
                      onClick={handleComplete}
                      disabled={loading}
                    >
                      완료
                    </Button>
                  ) : (
                    <Button
                      variant="contained"
                      onClick={handleNext}
                    >
                      다음
                    </Button>
                  )}
                </Box>
              </StepContent>
            </Step>
          ))}
        </Stepper>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          닫기
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default ShippingDialog