import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Chip,
} from '@mui/material'
import { DataGrid, GridColDef } from '@mui/x-data-grid'
import { Download as DownloadIcon } from '@mui/icons-material'
import { api } from '../api/client'
import { format } from 'date-fns'

export default function Products() {
  const [productType, setProductType] = useState<'wholesale' | 'marketplace'>('wholesale')
  const [supplier, setSupplier] = useState<string>('')
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [page, setPage] = useState(0)
  const [pageSize, setPageSize] = useState(25)

  // 공급사 목록
  const { data: suppliersData } = useQuery({
    queryKey: ['suppliers'],
    queryFn: async () => {
      const response = await api.getSuppliers()
      return response.data
    },
  })

  // 상품 목록
  const { data: productsData, isLoading } = useQuery({
    queryKey: ['products', productType, supplier, page, pageSize],
    queryFn: async () => {
      const response = await api.getProducts({
        product_type: productType,
        supplier: supplier || undefined,
        limit: pageSize,
        offset: page * pageSize,
      })
      return response.data
    },
  })

  const handleDownload = async () => {
    try {
      const response = await api.downloadProducts(supplier || undefined)
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `products_${supplier || 'all'}_${format(new Date(), 'yyyyMMdd_HHmmss')}.xlsx`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Download failed:', error)
    }
  }

  const columns: GridColDef[] = [
    {
      field: 'product_code',
      headerName: '상품 코드',
      width: 150,
    },
    {
      field: 'supplier',
      headerName: '공급사',
      width: 100,
      renderCell: (params) => (
        <Chip label={params.value.toUpperCase()} size="small" color="primary" />
      ),
    },
    {
      field: 'product_name',
      headerName: '상품명',
      width: 300,
      valueGetter: (params) => params.row.product_info?.product_name || '-',
    },
    {
      field: 'price',
      headerName: '가격',
      width: 120,
      valueGetter: (params) => {
        const info = params.row.product_info
        return info?.sale_price || info?.price || info?.supply_price || '-'
      },
      renderCell: (params) => {
        if (params.value === '-') return '-'
        return `${Number(params.value).toLocaleString()}원`
      },
    },
    {
      field: 'stock',
      headerName: '재고',
      width: 100,
      valueGetter: (params) => {
        const info = params.row.product_info
        return info?.stock_quantity || info?.stock || '-'
      },
    },
    {
      field: 'category',
      headerName: '카테고리',
      width: 200,
      valueGetter: (params) => params.row.product_info?.category || '-',
    },
    {
      field: 'updated_at',
      headerName: '업데이트',
      width: 180,
      valueGetter: (params) => format(new Date(params.value), 'yyyy-MM-dd HH:mm'),
    },
  ]

  const filteredProducts = productsData?.products?.filter((product: any) => {
    if (!searchTerm) return true
    const term = searchTerm.toLowerCase()
    return (
      product.product_code.toLowerCase().includes(term) ||
      product.product_info?.product_name?.toLowerCase().includes(term) ||
      product.product_info?.category?.toLowerCase().includes(term)
    )
  })

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">상품 목록</Typography>
        <Button
          variant="contained"
          startIcon={<DownloadIcon />}
          onClick={handleDownload}
        >
          엑셀 다운로드
        </Button>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" gap={2}>
            <FormControl sx={{ minWidth: 200 }}>
              <InputLabel>공급사</InputLabel>
              <Select
                value={supplier}
                label="공급사"
                onChange={(e) => setSupplier(e.target.value)}
              >
                <MenuItem value="">전체</MenuItem>
                {suppliersData?.map((s: any) => (
                  <MenuItem key={s.supplier_code} value={s.supplier_code}>
                    {s.supplier_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              label="검색"
              variant="outlined"
              fullWidth
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="상품코드, 상품명, 카테고리로 검색"
            />
          </Box>
        </CardContent>
      </Card>

      <Card>
        <CardContent sx={{ height: 600 }}>
          <DataGrid
            rows={filteredProducts || []}
            columns={columns}
            rowCount={productsData?.total || 0}
            loading={isLoading}
            pageSizeOptions={[10, 25, 50, 100]}
            paginationModel={{
              page,
              pageSize,
            }}
            onPaginationModelChange={(model) => {
              setPage(model.page)
              setPageSize(model.pageSize)
            }}
            paginationMode="server"
            getRowId={(row) => row.product_code}
            disableRowSelectionOnClick
          />
        </CardContent>
      </Card>
    </Box>
  )
}