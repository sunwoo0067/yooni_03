import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  CircularProgress,
  Alert,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  Divider,
  Paper,
  IconButton,
  TextField,
  InputAdornment,
  Skeleton,
} from '@mui/material'
import {
  CloudSync,
  Schedule,
  CheckCircle,
  Error,
  Warning,
  Refresh,
  Storage,
  Sync,
  FilterList,
  Delete,
} from '@mui/icons-material'
import { DatePicker } from '@mui/x-date-pickers/DatePicker'
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider'
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns'
import { ko } from 'date-fns/locale'
import { format } from 'date-fns'
import { useNotification } from '@components/ui/NotificationSystem'
import { wholesalerAPI } from '@services/api'

// Types
interface WholesalerSource {
  id: string
  name: string
  description: string
  api_available: boolean
  sync_supported: boolean
}

interface SyncStatus {
  is_running: boolean
  running_sources: string[]
  last_sync?: {
    batch_id: string
    source: string
    status: string
    completed_at: string
    total_collected: number
  }
  statistics: {
    total_products: number
    by_source: Record<string, number>
    by_status: Record<string, number>
    recent_batches: Array<{
      batch_id: string
      source: string
      status: string
      started_at: string
      completed_at?: string
      total_collected: number
      error_message?: string
    }>
  }
}

interface SyncFilters {
  categories: string[]
  price_min?: number
  price_max?: number
  keywords?: string
  exclude_keywords?: string
  date_from?: Date | null
  date_to?: Date | null
  stock_only: boolean
}

const CATEGORIES = [
  '전자제품',
  '패션',
  '생활용품',
  '스포츠',
  '뷰티',
  '건강식품',
  '가구',
  '완구',
  '자동차용품',
  '기타'
]

const WholesalerSync: React.FC = () => {
  const notification = useNotification()
  
  // State
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const [availableSources, setAvailableSources] = useState<WholesalerSource[]>([])
  const [selectedSource, setSelectedSource] = useState<string>('all')
  const [filters, setFilters] = useState<SyncFilters>({
    categories: [],
    date_from: null,
    date_to: null,
    stock_only: true,
  })
  
  // Loading states
  const [isLoadingStatus, setIsLoadingStatus] = useState(true)
  const [isLoadingSources, setIsLoadingSources] = useState(true)
  const [isSyncing, setIsSyncing] = useState(false)
  const [isCleaningUp, setIsCleaningUp] = useState(false)
  
  // Load initial data
  useEffect(() => {
    loadSources()
    loadSyncStatus()
    
    // Refresh status every 5 seconds
    const interval = setInterval(loadSyncStatus, 5000)
    return () => clearInterval(interval)
  }, [])
  
  const loadSources = async () => {
    setIsLoadingSources(true)
    try {
      const response = await wholesalerAPI.getSources()
      if (response.data) {
        // Simple Collector API 형식에 맞게 변환
        // 마켓플레이스를 제외한 도매처만 필터링
        const sources = response.data
          .filter((supplier: any) => !supplier.api_config?.marketplace)
          .map((supplier: any) => ({
            id: supplier.supplier_code,
            name: supplier.supplier_name,
            description: supplier.api_config?.base_url || '',
            api_available: supplier.is_active || false,
            sync_supported: true
          }))
        setAvailableSources(sources)
      }
    } catch (error: any) {
      console.error('도매처 목록 로드 오류:', error)
      notification.error('도매처 목록을 불러오는데 실패했습니다')
    } finally {
      setIsLoadingSources(false)
    }
  }
  
  const loadSyncStatus = async () => {
    try {
      const [statusResponse, logsResponse] = await Promise.all([
        wholesalerAPI.getSyncStatus(),
        wholesalerAPI.getCollectionLogs()
      ])
      
      // Simple Collector API 형식에 맞게 변환
      const supplierStats = statusResponse.data.suppliers || []
      const totalProducts = supplierStats.reduce((sum: number, s: any) => sum + (s.product_count || 0), 0)
      const bySource = supplierStats.reduce((acc: any, s: any) => {
        acc[s.supplier] = s.product_count || 0
        return acc
      }, {})
      
      const status: SyncStatus = {
        is_running: false, // Simple API는 실시간 상태 제공 안함
        running_sources: [],
        last_sync: supplierStats[0]?.last_full_sync ? {
          batch_id: 'latest',
          source: supplierStats[0].supplier,
          status: 'completed',
          completed_at: supplierStats[0].last_full_sync,
          total_collected: supplierStats[0].product_count
        } : undefined,
        statistics: {
          total_products: totalProducts,
          by_source: bySource,
          by_status: { completed: totalProducts },
          recent_batches: logsResponse.data.map((log: any) => ({
            batch_id: String(log.id),
            source: log.supplier,
            status: log.status || 'completed',
            started_at: log.start_time,
            completed_at: log.end_time,
            total_collected: log.total_count || 0,
            error_message: log.error_message
          })).slice(0, 10)
        }
      }
      setSyncStatus(status)
    } catch (error: any) {
      console.error('상태 조회 오류:', error)
    } finally {
      setIsLoadingStatus(false)
    }
  }
  
  const handleStartSync = async () => {
    if (selectedSource === '' || selectedSource === 'all') {
      notification.error('구체적인 도매처를 선택해주세요')
      return
    }
    
    setIsSyncing(true)
    
    try {
      // 필터 정보를 쿼리 파라미터로 구성
      const queryParams = new URLSearchParams()
      queryParams.append('test_mode', 'false')
      
      if (filters.date_from) {
        queryParams.append('date_from', format(filters.date_from, 'yyyy-MM-dd'))
      }
      if (filters.date_to) {
        queryParams.append('date_to', format(filters.date_to, 'yyyy-MM-dd'))
      }
      if (filters.categories.length > 0) {
        queryParams.append('categories', filters.categories.join(','))
      }
      if (filters.price_min !== undefined && filters.price_min > 0) {
        queryParams.append('price_min', filters.price_min.toString())
      }
      if (filters.price_max !== undefined && filters.price_max > 0) {
        queryParams.append('price_max', filters.price_max.toString())
      }
      if (filters.keywords) {
        queryParams.append('keywords', filters.keywords)
      }
      if (filters.exclude_keywords) {
        queryParams.append('exclude_keywords', filters.exclude_keywords)
      }
      queryParams.append('stock_only', filters.stock_only.toString())
      
      // API 엔드포인트 직접 호출 (필터 지원)
      const url = `http://localhost:8000/collection/full/${selectedSource}?${queryParams.toString()}`
      const response = await fetch(url, { method: 'POST' })
      const data = await response.json()
      
      if (response.ok) {
        notification.success(
          data.message || '동기화가 시작되었습니다'
        )
        // Reload status after a short delay
        setTimeout(() => {
          loadSyncStatus()
        }, 2000)
      } else {
        throw new Error(data.detail || '동기화 시작 실패')
      }
    } catch (error: any) {
      console.error('동기화 시작 오류:', error)
      const errorMessage = error.message || '동기화 시작 중 오류가 발생했습니다'
      notification.error(errorMessage)
    } finally {
      setIsSyncing(false)
    }
  }
  
  // Simple Collector API에는 cleanup 엔드포인트가 없으므로 제거
  const handleCleanupExpired = async () => {
    notification.info('이 기능은 현재 지원되지 않습니다')
  }
  
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle color="success" />
      case 'running':
        return <CircularProgress size={20} />
      case 'failed':
        return <Error color="error" />
      default:
        return <Warning color="warning" />
    }
  }
  
  const formatNumber = (num: number) => {
    return num?.toLocaleString('ko-KR') || '0'
  }
  
  const formatDate = (dateStr: string) => {
    if (!dateStr) return 'N/A'
    return new Date(dateStr).toLocaleString('ko-KR')
  }
  
  return (
    <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={ko}>
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h4" gutterBottom>
            도매처 상품 동기화
          </Typography>
          <Typography variant="body1" color="text.secondary">
            도매처의 상품 카탈로그를 데이터베이스에 동기화합니다
          </Typography>
        </Box>
      
      <Grid container spacing={3}>
        {/* 동기화 설정 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                동기화 설정
              </Typography>
              
              {/* 도매처 선택 */}
              <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel>도매처 선택</InputLabel>
                <Select
                  value={selectedSource}
                  onChange={(e) => setSelectedSource(e.target.value)}
                  label="도매처 선택"
                  disabled={isLoadingSources}
                >
                  <MenuItem value="all">
                    <Typography variant="body1">모든 도매처</Typography>
                  </MenuItem>
                  <Divider />
                  {availableSources.map((source) => (
                    <MenuItem 
                      key={source.id} 
                      value={source.id}
                      disabled={!source.sync_supported}
                    >
                      <Box>
                        <Typography variant="body1">{source.name}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {source.description}
                          {!source.sync_supported && ' (동기화 미지원)'}
                        </Typography>
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              {/* 카테고리 필터 */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  카테고리 필터 (선택사항)
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {CATEGORIES.map((category) => (
                    <Chip
                      key={category}
                      label={category}
                      onClick={() => {
                        setFilters(prev => ({
                          ...prev,
                          categories: prev.categories.includes(category)
                            ? prev.categories.filter(c => c !== category)
                            : [...prev.categories, category]
                        }))
                      }}
                      color={filters.categories.includes(category) ? 'primary' : 'default'}
                      variant={filters.categories.includes(category) ? 'filled' : 'outlined'}
                    />
                  ))}
                </Box>
              </Box>
              
              {/* 가격 범위 */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  가격 범위 (선택사항)
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <TextField
                      fullWidth
                      label="최소 가격"
                      type="number"
                      value={filters.price_min || ''}
                      onChange={(e) => setFilters(prev => ({ 
                        ...prev, 
                        price_min: e.target.value ? Number(e.target.value) : undefined 
                      }))}
                      InputProps={{
                        startAdornment: <InputAdornment position="start">₩</InputAdornment>,
                      }}
                    />
                  </Grid>
                  <Grid item xs={6}>
                    <TextField
                      fullWidth
                      label="최대 가격"
                      type="number"
                      value={filters.price_max || ''}
                      onChange={(e) => setFilters(prev => ({ 
                        ...prev, 
                        price_max: e.target.value ? Number(e.target.value) : undefined 
                      }))}
                      InputProps={{
                        startAdornment: <InputAdornment position="start">₩</InputAdornment>,
                      }}
                    />
                  </Grid>
                </Grid>
              </Box>
              
              {/* 키워드 필터 */}
              <TextField
                fullWidth
                label="포함 키워드 (선택사항)"
                value={filters.keywords || ''}
                onChange={(e) => setFilters(prev => ({ ...prev, keywords: e.target.value }))}
                placeholder="예: 무선, 블루투스"
                sx={{ mb: 2 }}
                helperText="쉼표로 구분하여 여러 키워드 입력 가능"
              />
              
              <TextField
                fullWidth
                label="제외 키워드 (선택사항)"
                value={filters.exclude_keywords || ''}
                onChange={(e) => setFilters(prev => ({ ...prev, exclude_keywords: e.target.value }))}
                placeholder="예: 중고, B급"
                sx={{ mb: 3 }}
                helperText="쉼표로 구분하여 여러 키워드 입력 가능"
              />
              
              {/* 날짜 범위 필터 */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  수집 기간 (선택사항)
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <DatePicker
                      label="시작일"
                      value={filters.date_from}
                      onChange={(date) => setFilters(prev => ({ 
                        ...prev, 
                        date_from: date 
                      }))}
                      slotProps={{ textField: { fullWidth: true } }}
                    />
                  </Grid>
                  <Grid item xs={6}>
                    <DatePicker
                      label="종료일"
                      value={filters.date_to}
                      onChange={(date) => setFilters(prev => ({ 
                        ...prev, 
                        date_to: date 
                      }))}
                      slotProps={{ textField: { fullWidth: true } }}
                    />
                  </Grid>
                </Grid>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  지정된 기간 내에 등록된 상품만 수집합니다
                </Typography>
              </Box>
              
              {/* 동기화 버튼 */}
              <Button
                fullWidth
                variant="contained"
                size="large"
                onClick={handleStartSync}
                disabled={isSyncing || syncStatus?.is_running || !selectedSource}
                startIcon={isSyncing ? <CircularProgress size={20} /> : <CloudSync />}
              >
                {isSyncing ? '동기화 시작 중...' : 
                 syncStatus?.is_running ? '동기화 실행 중...' : 
                 '동기화 시작'}
              </Button>
              
              {/* 진행 상태 */}
              {syncStatus?.is_running && (
                <Box sx={{ mt: 2 }}>
                  <Alert severity="info">
                    {syncStatus.running_sources.join(', ')} 동기화가 진행 중입니다
                    <LinearProgress sx={{ mt: 1 }} />
                  </Alert>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
        
        {/* 현재 상태 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  동기화 상태
                </Typography>
                <IconButton onClick={loadSyncStatus} disabled={isLoadingStatus}>
                  <Refresh />
                </IconButton>
              </Box>
              
              {isLoadingStatus ? (
                <>
                  <Skeleton variant="rectangular" height={100} sx={{ mb: 2 }} />
                  <Skeleton variant="rectangular" height={60} sx={{ mb: 1 }} />
                  <Skeleton variant="rectangular" height={60} />
                </>
              ) : syncStatus ? (
                <>
                  {/* 현재 상태 */}
                  <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      {syncStatus.is_running ? (
                        <CircularProgress size={20} sx={{ mr: 1 }} />
                      ) : (
                        <CheckCircle color="success" sx={{ mr: 1 }} />
                      )}
                      <Typography variant="subtitle1">
                        {syncStatus.is_running ? '동기화 실행 중' : '대기 중'}
                      </Typography>
                    </Box>
                    
                    {syncStatus.last_sync && (
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          마지막 동기화: {formatDate(syncStatus.last_sync.completed_at)}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          수집 상품: {formatNumber(syncStatus.last_sync.total_collected)}개
                        </Typography>
                      </Box>
                    )}
                  </Paper>
                  
                  {/* 통계 */}
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Paper sx={{ p: 2, textAlign: 'center' }}>
                        <Storage sx={{ fontSize: 32, color: 'primary.main', mb: 1 }} />
                        <Typography variant="h6">
                          {formatNumber(syncStatus.statistics.total_products)}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          총 수집 상품
                        </Typography>
                      </Paper>
                    </Grid>
                    <Grid item xs={6}>
                      <Paper sx={{ p: 2, textAlign: 'center' }}>
                        <Sync sx={{ fontSize: 32, color: 'success.main', mb: 1 }} />
                        <Typography variant="h6">
                          {Object.keys(syncStatus.statistics.by_source || {}).length}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          연동 도매처
                        </Typography>
                      </Paper>
                    </Grid>
                  </Grid>
                </>
              ) : (
                <Alert severity="error">
                  상태 정보를 불러올 수 없습니다
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>
        
        {/* 최근 동기화 기록 */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  최근 동기화 기록
                </Typography>
                <Button
                  startIcon={isCleaningUp ? <CircularProgress size={16} /> : <Delete />}
                  onClick={handleCleanupExpired}
                  disabled={isCleaningUp}
                  size="small"
                >
                  만료 상품 정리
                </Button>
              </Box>
              
              {syncStatus?.statistics.recent_batches?.length ? (
                <List>
                  {syncStatus.statistics.recent_batches.slice(0, 10).map((batch, index) => (
                    <React.Fragment key={batch.batch_id}>
                      <ListItem>
                        <Box sx={{ display: 'flex', alignItems: 'flex-start', width: '100%' }}>
                          <Box sx={{ mr: 2 }}>
                            {getStatusIcon(batch.status)}
                          </Box>
                          <Box sx={{ flexGrow: 1 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                              <Chip size="small" label={batch.source} />
                              <Typography variant="body2">
                                {formatNumber(batch.total_collected)}개 상품
                              </Typography>
                            </Box>
                            <Typography variant="caption" color="text.secondary" display="block">
                              시작: {formatDate(batch.started_at)}
                            </Typography>
                            {batch.completed_at && (
                              <Typography variant="caption" color="text.secondary" display="block">
                                완료: {formatDate(batch.completed_at)}
                              </Typography>
                            )}
                            {batch.error_message && (
                              <Alert severity="error" sx={{ mt: 1 }}>
                                {batch.error_message}
                              </Alert>
                            )}
                          </Box>
                        </Box>
                      </ListItem>
                      {index < syncStatus.statistics.recent_batches.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <Schedule sx={{ fontSize: 48, color: 'grey.400', mb: 2 }} />
                  <Typography variant="body1" color="text.secondary">
                    아직 동기화 기록이 없습니다
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      </Box>
    </LocalizationProvider>
  )
}

export default WholesalerSync