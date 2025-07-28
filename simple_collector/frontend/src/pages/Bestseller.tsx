import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  LinearProgress,
  Chip,
  Grid,
  Paper,
} from '@mui/material'
import {
  TrendingUp as TrendingUpIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material'
import { DataGrid, GridColDef } from '@mui/x-data-grid'
import { api } from '../api/client'
import { format } from 'date-fns'
import { ko } from 'date-fns/locale'

export default function Bestseller() {
  const [marketplace, setMarketplace] = useState<string>('all')
  const [days, setDays] = useState<number>(7)
  const queryClient = useQueryClient()

  // 베스트셀러 목록 조회
  const { data: bestsellersData, isLoading } = useQuery({
    queryKey: ['bestsellers', marketplace, days],
    queryFn: async () => {
      const response = await api.get('/bestseller/list', {
        params: {
          marketplace: marketplace !== 'all' ? marketplace : undefined,
          days,
          limit: 200,
        },
      })
      return response.data
    },
  })

  // 베스트셀러 트렌드 조회
  const { data: trendsData } = useQuery({
    queryKey: ['bestseller-trends', marketplace],
    queryFn: async () => {
      const response = await api.get('/bestseller/trends', {
        params: {
          marketplace: marketplace !== 'all' ? marketplace : undefined,
          days: 30,
        },
      })
      return response.data
    },
  })

  // 수집 시작
  const collectMutation = useMutation({
    mutationFn: async (params: { marketplace: string }) => {
      const response = await api.post(`/bestseller/collect/${params.marketplace}`, {
        limit: 100,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bestsellers'] })
    },
  })

  const columns: GridColDef[] = [
    {
      field: 'rank',
      headerName: '순위',
      width: 80,
      renderCell: (params) => (
        <Chip
          label={params.value}
          size="small"
          color={params.value <= 10 ? 'error' : params.value <= 30 ? 'warning' : 'default'}
        />
      ),
    },
    {
      field: 'marketplace',
      headerName: '마켓',
      width: 100,
      renderCell: (params) => {
        const colors = {
          coupang: 'error',
          naver: 'success',
          '11st': 'warning',
        }
        return (
          <Chip
            label={params.value.toUpperCase()}
            size="small"
            color={colors[params.value] || 'default'}
          />
        )
      },
    },
    {
      field: 'product_name',
      headerName: '상품명',
      width: 400,
      renderCell: (params) => (
        <Box>
          <Typography variant="body2" noWrap>
            {params.value}
          </Typography>
          {params.row.brand && (
            <Typography variant="caption" color="text.secondary">
              {params.row.brand}
            </Typography>
          )}
        </Box>
      ),
    },
    {
      field: 'category',
      headerName: '카테고리',
      width: 150,
    },
    {
      field: 'price',
      headerName: '가격',
      width: 120,
      valueFormatter: (params) => `${params.value?.toLocaleString()}원`,
    },
    {
      field: 'review_count',
      headerName: '리뷰',
      width: 100,
      valueFormatter: (params) => params.value?.toLocaleString(),
    },
    {
      field: 'rating',
      headerName: '평점',
      width: 80,
      valueFormatter: (params) => params.value?.toFixed(1),
    },
    {
      field: 'collected_at',
      headerName: '수집시간',
      width: 180,
      valueFormatter: (params) =>
        format(new Date(params.value), 'MM/dd HH:mm', { locale: ko }),
    },
  ]

  const trendColumns: GridColDef[] = [
    {
      field: 'marketplace',
      headerName: '마켓',
      width: 100,
    },
    {
      field: 'product_name',
      headerName: '상품명',
      width: 350,
    },
    {
      field: 'avg_rank',
      headerName: '평균순위',
      width: 100,
      renderCell: (params) => (
        <Chip label={params.value} size="small" color="primary" />
      ),
    },
    {
      field: 'best_rank',
      headerName: '최고순위',
      width: 100,
    },
    {
      field: 'worst_rank',
      headerName: '최저순위',
      width: 100,
    },
    {
      field: 'appearance_count',
      headerName: '등장횟수',
      width: 100,
    },
    {
      field: 'stability_score',
      headerName: '안정성',
      width: 100,
      renderCell: (params) => {
        const score = params.value
        const color = score >= 80 ? 'success' : score >= 50 ? 'warning' : 'error'
        return <Chip label={`${score}%`} size="small" color={color} />
      },
    },
  ]

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">베스트셀러 분석</Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="contained"
            startIcon={<RefreshIcon />}
            onClick={() => collectMutation.mutate({ marketplace })}
            disabled={collectMutation.isPending}
          >
            {collectMutation.isPending ? '수집 중...' : '수집 시작'}
          </Button>
        </Box>
      </Box>

      {collectMutation.data && (
        <Alert severity="info" sx={{ mb: 2 }}>
          {collectMutation.data.message}
        </Alert>
      )}

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              전체 상품 수
            </Typography>
            <Typography variant="h3">
              {bestsellersData?.total || 0}
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              트렌드 상품
            </Typography>
            <Typography variant="h3">
              {trendsData?.total || 0}
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              수집 기간
            </Typography>
            <Typography variant="h3">
              {days}일
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" gap={2}>
            <FormControl sx={{ minWidth: 200 }}>
              <InputLabel>마켓플레이스</InputLabel>
              <Select
                value={marketplace}
                label="마켓플레이스"
                onChange={(e) => setMarketplace(e.target.value)}
              >
                <MenuItem value="all">전체</MenuItem>
                <MenuItem value="coupang">쿠팡</MenuItem>
                <MenuItem value="naver">네이버</MenuItem>
              </Select>
            </FormControl>
            <FormControl sx={{ minWidth: 150 }}>
              <InputLabel>기간</InputLabel>
              <Select
                value={days}
                label="기간"
                onChange={(e) => setDays(Number(e.target.value))}
              >
                <MenuItem value={1}>1일</MenuItem>
                <MenuItem value={7}>7일</MenuItem>
                <MenuItem value={30}>30일</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </CardContent>
      </Card>

      <Box sx={{ mb: 3 }}>
        <Typography variant="h5" gutterBottom>
          베스트셀러 목록
        </Typography>
        <Card>
          <CardContent sx={{ height: 600 }}>
            {isLoading && <LinearProgress />}
            <DataGrid
              rows={bestsellersData?.bestsellers || []}
              columns={columns}
              pageSize={25}
              rowsPerPageOptions={[25, 50, 100]}
              disableSelectionOnClick
              loading={isLoading}
            />
          </CardContent>
        </Card>
      </Box>

      <Box>
        <Typography variant="h5" gutterBottom>
          <TrendingUpIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          트렌드 분석
        </Typography>
        <Card>
          <CardContent sx={{ height: 400 }}>
            <DataGrid
              rows={trendsData?.trends || []}
              columns={trendColumns}
              pageSize={10}
              rowsPerPageOptions={[10, 25, 50]}
              disableSelectionOnClick
              getRowId={(row) => `${row.marketplace}_${row.product_id}`}
            />
          </CardContent>
        </Card>
      </Box>
    </Box>
  )
}