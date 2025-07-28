import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Alert,
  LinearProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  FormControlLabel,
  Switch,
} from '@mui/material'
import {
  PlayArrow as PlayIcon,
  Sync as SyncIcon,
  Refresh as RefreshIcon,
  Api as ApiIcon,
  Science as TestIcon,
} from '@mui/icons-material'
import { api } from '../api/client'
import { format } from 'date-fns'

interface Supplier {
  supplier_code: string
  supplier_name: string
  is_active: boolean
  api_config?: any
}

export default function Collection() {
  const queryClient = useQueryClient()
  const [alerts, setAlerts] = useState<{ type: 'success' | 'error'; message: string }[]>([])
  const [testMode, setTestMode] = useState(true)

  // 공급사 목록
  const { data: suppliers } = useQuery({
    queryKey: ['suppliers'],
    queryFn: async () => {
      const response = await api.getSuppliers()
      return response.data
    },
  })

  // 수집 로그
  const { data: logs, refetch: refetchLogs } = useQuery({
    queryKey: ['collection-logs'],
    queryFn: async () => {
      const response = await api.getCollectionLogs({ limit: 20 })
      return response.data
    },
    refetchInterval: 5000, // 5초마다 자동 갱신
  })

  // 전체 수집 mutation
  const fullCollectionMutation = useMutation({
    mutationFn: (supplier: string) => api.startCollection(supplier, testMode),
    onSuccess: (_, supplier) => {
      queryClient.invalidateQueries({ queryKey: ['collection-logs'] })
      setAlerts([...alerts, {
        type: 'success',
        message: `${supplier} 전체 수집이 시작되었습니다. (${testMode ? '테스트' : '실제'} 모드)`
      }])
    },
    onError: (error: any, supplier) => {
      setAlerts([...alerts, {
        type: 'error',
        message: `${supplier} 수집 시작 실패: ${error.response?.data?.detail || error.message}`
      }])
    },
  })

  // 증분 수집 mutation
  const incrementalSyncMutation = useMutation({
    mutationFn: (supplier: string) => api.startIncrementalSync(supplier, testMode),
    onSuccess: (_, supplier) => {
      queryClient.invalidateQueries({ queryKey: ['collection-logs'] })
      setAlerts([...alerts, {
        type: 'success',
        message: `${supplier} 증분 수집이 시작되었습니다. (${testMode ? '테스트' : '실제'} 모드)`
      }])
    },
    onError: (error: any, supplier) => {
      setAlerts([...alerts, {
        type: 'error',
        message: `${supplier} 증분 수집 실패: ${error.response?.data?.detail || error.message}`
      }])
    },
  })

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success'
      case 'running':
        return 'info'
      case 'failed':
        return 'error'
      default:
        return 'default'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return '완료'
      case 'running':
        return '진행 중'
      case 'failed':
        return '실패'
      default:
        return status
    }
  }

  const hasApiCredentials = (supplier: Supplier) => {
    return supplier.api_config && Object.keys(supplier.api_config).length > 0
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        상품 수집
      </Typography>

      {/* 테스트 모드 스위치 */}
      <Box mb={2}>
        <FormControlLabel
          control={
            <Switch
              checked={testMode}
              onChange={(e) => setTestMode(e.target.checked)}
              color="primary"
            />
          }
          label={
            <Box display="flex" alignItems="center" gap={1}>
              {testMode ? <TestIcon /> : <ApiIcon />}
              <Typography>
                {testMode ? '테스트 모드 (더미 데이터)' : '실제 API 모드'}
              </Typography>
            </Box>
          }
        />
      </Box>

      {/* 알림 메시지 */}
      {alerts.map((alert, index) => (
        <Alert
          key={index}
          severity={alert.type}
          onClose={() => setAlerts(alerts.filter((_, i) => i !== index))}
          sx={{ mb: 2 }}
        >
          {alert.message}
        </Alert>
      ))}

      {/* 도매사이트 수집 */}
      <Typography variant="h5" gutterBottom sx={{ mt: 2 }}>
        도매사이트
      </Typography>
      <Grid container spacing={3} mb={3}>
        {suppliers?.filter((s: Supplier) => !s.api_config?.marketplace).map((supplier: Supplier) => (
          <Grid item xs={12} md={4} key={supplier.supplier_code}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="start" mb={1}>
                  <Typography variant="h6">
                    {supplier.supplier_name}
                  </Typography>
                  {hasApiCredentials(supplier) && !testMode && (
                    <Chip
                      icon={<ApiIcon />}
                      label="API 설정됨"
                      size="small"
                      color="success"
                      variant="outlined"
                    />
                  )}
                </Box>
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  {supplier.supplier_code.toUpperCase()}
                </Typography>
                {!hasApiCredentials(supplier) && !testMode && (
                  <Alert severity="warning" sx={{ mb: 1, py: 0 }}>
                    <Typography variant="caption">
                      API 키가 설정되지 않았습니다. 설정에서 API 키를 등록하세요.
                    </Typography>
                  </Alert>
                )}
                <Box display="flex" gap={1} mt={2}>
                  <Button
                    variant="contained"
                    size="small"
                    startIcon={<PlayIcon />}
                    onClick={() => fullCollectionMutation.mutate(supplier.supplier_code)}
                    disabled={!supplier.is_active || (!testMode && !hasApiCredentials(supplier))}
                  >
                    전체 수집
                  </Button>
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<SyncIcon />}
                    onClick={() => incrementalSyncMutation.mutate(supplier.supplier_code)}
                    disabled={
                      !supplier.is_active ||
                      supplier.supplier_code === 'zentrade' ||
                      (!testMode && !hasApiCredentials(supplier))
                    }
                  >
                    증분 수집
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* 마켓플레이스 수집 */}
      <Typography variant="h5" gutterBottom sx={{ mt: 3 }}>
        마켓플레이스
      </Typography>
      <Grid container spacing={3} mb={3}>
        {suppliers?.filter((s: Supplier) => s.api_config?.marketplace).map((supplier: Supplier) => (
          <Grid item xs={12} md={4} key={supplier.supplier_code}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="start" mb={1}>
                  <Typography variant="h6">
                    {supplier.supplier_name}
                  </Typography>
                  {hasApiCredentials(supplier) && !testMode && (
                    <Chip
                      icon={<ApiIcon />}
                      label="API 설정됨"
                      size="small"
                      color="success"
                      variant="outlined"
                    />
                  )}
                </Box>
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  {supplier.supplier_code.toUpperCase()}
                </Typography>
                {!hasApiCredentials(supplier) && !testMode && (
                  <Alert severity="warning" sx={{ mb: 1, py: 0 }}>
                    <Typography variant="caption">
                      API 키가 설정되지 않았습니다. 설정에서 API 키를 등록하세요.
                    </Typography>
                  </Alert>
                )}
                <Box display="flex" gap={1} mt={2}>
                  <Button
                    variant="contained"
                    size="small"
                    startIcon={<PlayIcon />}
                    onClick={() => fullCollectionMutation.mutate(supplier.supplier_code)}
                    disabled={!supplier.is_active || (!testMode && !hasApiCredentials(supplier))}
                  >
                    상품 수집
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* 수집 로그 */}
      <Card>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">수집 기록</Typography>
            <Tooltip title="새로고침">
              <IconButton onClick={() => refetchLogs()}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Box>

          {logs?.some((log: any) => log.status === 'running') && (
            <LinearProgress sx={{ mb: 2 }} />
          )}

          <Table>
            <TableHead>
              <TableRow>
                <TableCell>공급사</TableCell>
                <TableCell>수집 유형</TableCell>
                <TableCell>상태</TableCell>
                <TableCell>처리 건수</TableCell>
                <TableCell>시작 시간</TableCell>
                <TableCell>소요 시간</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {logs?.map((log: any) => (
                <TableRow key={log.id}>
                  <TableCell>
                    <Chip
                      label={log.supplier.toUpperCase()}
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>{log.collection_type === 'full' ? '전체' : '증분'}</TableCell>
                  <TableCell>
                    <Chip
                      label={getStatusText(log.status)}
                      size="small"
                      color={getStatusColor(log.status) as any}
                    />
                  </TableCell>
                  <TableCell>
                    {log.total_count || 0}개
                    {log.new_count > 0 && ` (신규: ${log.new_count})`}
                    {log.updated_count > 0 && ` (업데이트: ${log.updated_count})`}
                    {log.error_count > 0 && (
                      <Chip
                        label={`오류: ${log.error_count}`}
                        size="small"
                        color="error"
                        sx={{ ml: 1 }}
                      />
                    )}
                  </TableCell>
                  <TableCell>
                    {format(new Date(log.start_time), 'yyyy-MM-dd HH:mm:ss')}
                  </TableCell>
                  <TableCell>
                    {log.end_time
                      ? `${Math.round(
                          (new Date(log.end_time).getTime() -
                            new Date(log.start_time).getTime()) /
                            1000
                        )}초`
                      : '-'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </Box>
  )
}