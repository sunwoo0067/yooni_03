import { useQuery } from '@tanstack/react-query'
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert,
} from '@mui/material'
import {
  Inventory as InventoryIcon,
  CloudSync as SyncIcon,
  Store as StoreIcon,
  TrendingUp as TrendingIcon,
} from '@mui/icons-material'
import { api } from '../api/client'

interface StatCard {
  title: string
  value: string | number
  icon: React.ReactNode
  color: string
}

export default function Dashboard() {
  // 상품 통계
  const { data: productsData, isLoading: productsLoading } = useQuery({
    queryKey: ['products-stats'],
    queryFn: async () => {
      const response = await api.getProducts({ limit: 1 })
      return response.data
    },
  })

  // 공급사 정보
  const { data: suppliersData } = useQuery({
    queryKey: ['suppliers'],
    queryFn: async () => {
      const response = await api.getSuppliers()
      return response.data
    },
  })

  // 최근 수집 로그
  const { data: logsData } = useQuery({
    queryKey: ['recent-logs'],
    queryFn: async () => {
      const response = await api.getCollectionLogs({ limit: 5 })
      return response.data
    },
  })

  // 동기화 상태
  const { data: syncStatus } = useQuery({
    queryKey: ['sync-status'],
    queryFn: async () => {
      const response = await api.getSyncStatus()
      return response.data
    },
  })

  const stats: StatCard[] = [
    {
      title: '전체 상품',
      value: productsData?.total || 0,
      icon: <InventoryIcon />,
      color: '#1976d2',
    },
    {
      title: '활성 공급사',
      value: suppliersData?.length || 0,
      icon: <StoreIcon />,
      color: '#388e3c',
    },
    {
      title: '오늘 수집',
      value: logsData?.filter((log: any) => {
        const today = new Date().toDateString()
        return new Date(log.start_time).toDateString() === today
      }).length || 0,
      icon: <SyncIcon />,
      color: '#f57c00',
    },
    {
      title: '수집 성공률',
      value: logsData ? 
        `${Math.round(
          (logsData.filter((log: any) => log.status === 'completed').length / 
           logsData.length) * 100
        )}%` : '0%',
      icon: <TrendingIcon />,
      color: '#d32f2f',
    },
  ]

  if (productsLoading) {
    return (
      <Box display="flex" justifyContent="center" mt={4}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        대시보드
      </Typography>

      {/* 통계 카드 */}
      <Grid container spacing={3} mb={3}>
        {stats.map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                  <Box
                    sx={{
                      backgroundColor: stat.color,
                      color: 'white',
                      p: 1,
                      borderRadius: 1,
                      mr: 2,
                    }}
                  >
                    {stat.icon}
                  </Box>
                  <Typography color="textSecondary" variant="body2">
                    {stat.title}
                  </Typography>
                </Box>
                <Typography variant="h4">{stat.value}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* 공급사별 상품 수 */}
      {syncStatus && (
        <Grid container spacing={3} mb={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  공급사별 현황
                </Typography>
                <Grid container spacing={2}>
                  {syncStatus.suppliers?.map((supplier: any) => (
                    <Grid item xs={12} md={4} key={supplier.supplier}>
                      <Box p={2} bgcolor="grey.100" borderRadius={1}>
                        <Typography variant="subtitle1" fontWeight="bold">
                          {supplier.supplier.toUpperCase()}
                        </Typography>
                        <Typography variant="body2">
                          상품 수: {supplier.product_count}개
                        </Typography>
                        <Typography variant="body2">
                          전체 수집: {supplier.full_sync_count}회
                        </Typography>
                        <Typography variant="body2">
                          증분 수집: {supplier.incremental_sync_count}회
                        </Typography>
                        {supplier.last_full_sync && (
                          <Typography variant="caption" color="textSecondary">
                            마지막 전체 수집: {new Date(supplier.last_full_sync).toLocaleString()}
                          </Typography>
                        )}
                      </Box>
                    </Grid>
                  ))}
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* 최근 수집 로그 */}
      {logsData && logsData.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              최근 수집 활동
            </Typography>
            {logsData.map((log: any) => (
              <Box key={log.id} mb={2} p={2} bgcolor="grey.50" borderRadius={1}>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Box>
                    <Typography variant="subtitle2">
                      {log.supplier.toUpperCase()} - {log.collection_type}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      {new Date(log.start_time).toLocaleString()}
                    </Typography>
                  </Box>
                  <Box textAlign="right">
                    {log.status === 'completed' ? (
                      <Alert severity="success" sx={{ py: 0 }}>
                        성공: {log.total_count}개 처리
                      </Alert>
                    ) : log.status === 'running' ? (
                      <Alert severity="info" sx={{ py: 0 }}>
                        진행 중...
                      </Alert>
                    ) : (
                      <Alert severity="error" sx={{ py: 0 }}>
                        실패
                      </Alert>
                    )}
                  </Box>
                </Box>
              </Box>
            ))}
          </CardContent>
        </Card>
      )}
    </Box>
  )
}