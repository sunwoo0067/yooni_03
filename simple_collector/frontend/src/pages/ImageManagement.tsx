import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  LinearProgress,
  Alert,
  Chip,
  IconButton,
  ImageList,
  ImageListItem,
  ImageListItemBar,
  Tooltip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  FormControlLabel,
  Checkbox,
} from '@mui/material'
import {
  CloudUpload as UploadIcon,
  Image as ImageIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  WaterDrop as WatermarkIcon,
  Storage as StorageIcon,
} from '@mui/icons-material'
import axios from 'axios'

interface ImageData {
  product_code: string
  images: {
    main: string[]
    detail: string[]
    thumbnail: string[]
  }
}

interface StorageStats {
  total_size_mb: number
  file_count: number
  active_images: number
  total_db_records: number
}

export default function ImageManagement() {
  const [loading, setLoading] = useState(false)
  const [selectedProduct, setSelectedProduct] = useState('')
  const [imageUrls, setImageUrls] = useState('')
  const [marketplace, setMarketplace] = useState('coupang')
  const [addWatermark, setAddWatermark] = useState(false)
  const [hostedImages, setHostedImages] = useState<ImageData | null>(null)
  const [storageStats, setStorageStats] = useState<StorageStats | null>(null)
  const [processingStatus, setProcessingStatus] = useState<string>('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchStorageStats()
  }, [])

  const fetchStorageStats = async () => {
    try {
      const response = await axios.get('http://localhost:8000/images/storage/stats')
      setStorageStats(response.data.stats)
    } catch (error) {
      console.error('스토리지 통계 조회 오류:', error)
    }
  }

  const handleProcessImages = async () => {
    if (!selectedProduct || !imageUrls) {
      setError('상품 코드와 이미지 URL을 입력해주세요')
      return
    }

    setLoading(true)
    setError(null)
    setProcessingStatus('이미지 처리 중...')

    try {
      const urls = imageUrls.split('\n').filter(url => url.trim())
      
      const response = await axios.post(
        `http://localhost:8000/images/process/${selectedProduct}`,
        {
          product_code: selectedProduct,
          image_urls: urls,
          marketplace,
          add_watermark: addWatermark,
        }
      )

      setProcessingStatus('처리가 시작되었습니다. 잠시 후 결과를 확인하세요.')
      
      // 3초 후 결과 조회
      setTimeout(() => {
        fetchHostedImages(selectedProduct)
      }, 3000)

    } catch (error: any) {
      setError(error.response?.data?.detail || '이미지 처리 실패')
      setProcessingStatus('')
    } finally {
      setLoading(false)
      setDialogOpen(false)
    }
  }

  const fetchHostedImages = async (productCode: string) => {
    try {
      const response = await axios.get(
        `http://localhost:8000/images/hosted/${productCode}`
      )
      setHostedImages(response.data)
      setProcessingStatus('처리 완료!')
    } catch (error) {
      console.error('호스팅 이미지 조회 오류:', error)
    }
  }

  const handleBatchProcess = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await axios.post(
        'http://localhost:8000/images/process-wholesale-images',
        {
          limit: 50
        }
      )
      
      setProcessingStatus(response.data.message)
      fetchStorageStats()
    } catch (error: any) {
      setError(error.response?.data?.detail || '배치 처리 실패')
    } finally {
      setLoading(false)
    }
  }

  const handleCleanup = async () => {
    if (!window.confirm('30일 이상 된 이미지를 삭제하시겠습니까?')) {
      return
    }

    setLoading(true)
    
    try {
      await axios.post('http://localhost:8000/images/cleanup', { days: 30 })
      setProcessingStatus('정리 완료')
      fetchStorageStats()
    } catch (error) {
      setError('이미지 정리 실패')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        이미지 관리
      </Typography>

      {/* 스토리지 현황 */}
      {storageStats && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box display="flex" alignItems="center" mb={2}>
              <StorageIcon sx={{ mr: 1 }} />
              <Typography variant="h6">스토리지 현황</Typography>
            </Box>
            <Grid container spacing={3}>
              <Grid item xs={3}>
                <Typography variant="body2" color="text.secondary">
                  총 용량
                </Typography>
                <Typography variant="h5">
                  {storageStats.total_size_mb} MB
                </Typography>
              </Grid>
              <Grid item xs={3}>
                <Typography variant="body2" color="text.secondary">
                  파일 수
                </Typography>
                <Typography variant="h5">
                  {storageStats.file_count.toLocaleString()}
                </Typography>
              </Grid>
              <Grid item xs={3}>
                <Typography variant="body2" color="text.secondary">
                  활성 이미지
                </Typography>
                <Typography variant="h5">
                  {storageStats.active_images.toLocaleString()}
                </Typography>
              </Grid>
              <Grid item xs={3}>
                <Typography variant="body2" color="text.secondary">
                  DB 레코드
                </Typography>
                <Typography variant="h5">
                  {storageStats.total_db_records.toLocaleString()}
                </Typography>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* 액션 버튼 */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item>
          <Button
            variant="contained"
            startIcon={<ImageIcon />}
            onClick={() => setDialogOpen(true)}
          >
            이미지 처리
          </Button>
        </Grid>
        <Grid item>
          <Button
            variant="outlined"
            startIcon={<UploadIcon />}
            onClick={handleBatchProcess}
            disabled={loading}
          >
            도매 상품 일괄 처리
          </Button>
        </Grid>
        <Grid item>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchStorageStats}
          >
            새로고침
          </Button>
        </Grid>
        <Grid item>
          <Button
            variant="outlined"
            color="warning"
            startIcon={<DeleteIcon />}
            onClick={handleCleanup}
            disabled={loading}
          >
            오래된 이미지 정리
          </Button>
        </Grid>
      </Grid>

      {/* 상태 메시지 */}
      {processingStatus && (
        <Alert severity="info" sx={{ mb: 2 }}>
          {processingStatus}
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* 호스팅된 이미지 표시 */}
      {hostedImages && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              처리된 이미지 - {hostedImages.product_code}
            </Typography>
            
            {/* 메인 이미지 */}
            {hostedImages.images.main.length > 0 && (
              <Box mb={3}>
                <Typography variant="subtitle1" gutterBottom>
                  메인 이미지
                </Typography>
                <ImageList sx={{ height: 200 }} cols={4} rowHeight={180}>
                  {hostedImages.images.main.map((url, index) => (
                    <ImageListItem key={index}>
                      <img
                        src={url}
                        alt={`Main ${index}`}
                        loading="lazy"
                        style={{ height: '100%', objectFit: 'cover' }}
                      />
                      <ImageListItemBar
                        title={`메인 ${index + 1}`}
                        actionIcon={
                          <IconButton
                            sx={{ color: 'rgba(255, 255, 255, 0.54)' }}
                            onClick={() => window.open(url, '_blank')}
                          >
                            <DownloadIcon />
                          </IconButton>
                        }
                      />
                    </ImageListItem>
                  ))}
                </ImageList>
              </Box>
            )}

            {/* 상세 이미지 */}
            {hostedImages.images.detail.length > 0 && (
              <Box mb={3}>
                <Typography variant="subtitle1" gutterBottom>
                  상세 이미지
                </Typography>
                <ImageList sx={{ height: 200 }} cols={4} rowHeight={180}>
                  {hostedImages.images.detail.map((url, index) => (
                    <ImageListItem key={index}>
                      <img
                        src={url}
                        alt={`Detail ${index}`}
                        loading="lazy"
                        style={{ height: '100%', objectFit: 'cover' }}
                      />
                      <ImageListItemBar
                        title={`상세 ${index + 1}`}
                        actionIcon={
                          <IconButton
                            sx={{ color: 'rgba(255, 255, 255, 0.54)' }}
                            onClick={() => window.open(url, '_blank')}
                          >
                            <DownloadIcon />
                          </IconButton>
                        }
                      />
                    </ImageListItem>
                  ))}
                </ImageList>
              </Box>
            )}

            {/* 썸네일 */}
            {hostedImages.images.thumbnail.length > 0 && (
              <Box>
                <Typography variant="subtitle1" gutterBottom>
                  썸네일
                </Typography>
                <Box display="flex" gap={1}>
                  {hostedImages.images.thumbnail.map((url, index) => (
                    <img
                      key={index}
                      src={url}
                      alt={`Thumbnail ${index}`}
                      style={{ width: 100, height: 100, objectFit: 'cover' }}
                    />
                  ))}
                </Box>
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* 이미지 처리 다이얼로그 */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>이미지 처리</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <TextField
              fullWidth
              label="상품 코드"
              value={selectedProduct}
              onChange={(e) => setSelectedProduct(e.target.value)}
              sx={{ mb: 2 }}
            />
            
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>마켓플레이스</InputLabel>
              <Select
                value={marketplace}
                onChange={(e) => setMarketplace(e.target.value)}
                label="마켓플레이스"
              >
                <MenuItem value="coupang">쿠팡</MenuItem>
                <MenuItem value="naver">네이버</MenuItem>
                <MenuItem value="11st">11번가</MenuItem>
              </Select>
            </FormControl>

            <TextField
              fullWidth
              multiline
              rows={4}
              label="이미지 URL (줄바꿈으로 구분)"
              value={imageUrls}
              onChange={(e) => setImageUrls(e.target.value)}
              placeholder="https://example.com/image1.jpg&#10;https://example.com/image2.jpg"
              sx={{ mb: 2 }}
            />

            <FormControlLabel
              control={
                <Checkbox
                  checked={addWatermark}
                  onChange={(e) => setAddWatermark(e.target.checked)}
                />
              }
              label="워터마크 추가"
            />

            <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
              <Button onClick={() => setDialogOpen(false)}>
                취소
              </Button>
              <Button
                variant="contained"
                onClick={handleProcessImages}
                disabled={loading || !selectedProduct || !imageUrls}
              >
                처리 시작
              </Button>
            </Box>
          </Box>
        </DialogContent>
      </Dialog>
    </Box>
  )
}