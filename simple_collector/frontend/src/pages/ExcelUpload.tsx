import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Chip,
  LinearProgress,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material'
import {
  CloudUpload as UploadIcon,
  Download as DownloadIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
} from '@mui/icons-material'
import { api } from '../api/client'
import { format } from 'date-fns'

export default function ExcelUpload() {
  const [selectedSupplier, setSelectedSupplier] = useState<string>('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [alert, setAlert] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // 공급사 목록
  const { data: suppliers } = useQuery({
    queryKey: ['suppliers'],
    queryFn: async () => {
      const response = await api.getSuppliers()
      return response.data
    },
  })

  // 업로드 기록
  const { data: uploadHistory, refetch: refetchHistory } = useQuery({
    queryKey: ['upload-history'],
    queryFn: async () => {
      const response = await api.getUploadHistory()
      return response.data
    },
  })

  // 파일 업로드 mutation
  const uploadMutation = useMutation({
    mutationFn: async ({ supplier, file }: { supplier: string; file: File }) => {
      setUploadProgress(30)
      const response = await api.uploadExcel(supplier, file)
      setUploadProgress(100)
      return response.data
    },
    onSuccess: (data) => {
      setAlert({
        type: 'success',
        message: `업로드 완료: ${data.processed_rows}개 중 ${data.new_products}개 신규, ${data.updated_products}개 업데이트`,
      })
      setSelectedFile(null)
      setUploadProgress(0)
      refetchHistory()
    },
    onError: (error: any) => {
      setAlert({
        type: 'error',
        message: `업로드 실패: ${error.response?.data?.detail || error.message}`,
      })
      setUploadProgress(0)
    },
  })

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0])
    }
  }

  const handleUpload = () => {
    if (!selectedSupplier || !selectedFile) {
      setAlert({ type: 'error', message: '공급사와 파일을 선택해주세요.' })
      return
    }

    uploadMutation.mutate({ supplier: selectedSupplier, file: selectedFile })
  }

  const downloadTemplate = async (supplier: string) => {
    try {
      const response = await api.getExcelTemplate(supplier)
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${supplier}_template.xlsx`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Template download failed:', error)
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        엑셀 업로드
      </Typography>

      {alert && (
        <Alert
          severity={alert.type}
          onClose={() => setAlert(null)}
          sx={{ mb: 2 }}
        >
          {alert.message}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* 업로드 섹션 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                파일 업로드
              </Typography>

              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>공급사 선택</InputLabel>
                <Select
                  value={selectedSupplier}
                  label="공급사 선택"
                  onChange={(e) => setSelectedSupplier(e.target.value)}
                >
                  {suppliers?.map((supplier: any) => (
                    <MenuItem key={supplier.supplier_code} value={supplier.supplier_code}>
                      {supplier.supplier_name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Box
                sx={{
                  border: '2px dashed #ccc',
                  borderRadius: 2,
                  p: 3,
                  textAlign: 'center',
                  mb: 2,
                  backgroundColor: selectedFile ? '#f5f5f5' : 'transparent',
                }}
              >
                <input
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                  id="file-upload"
                />
                <label htmlFor="file-upload">
                  <Button
                    component="span"
                    variant="outlined"
                    startIcon={<UploadIcon />}
                  >
                    파일 선택
                  </Button>
                </label>
                {selectedFile && (
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    선택된 파일: {selectedFile.name}
                  </Typography>
                )}
              </Box>

              {uploadProgress > 0 && (
                <LinearProgress
                  variant="determinate"
                  value={uploadProgress}
                  sx={{ mb: 2 }}
                />
              )}

              <Button
                variant="contained"
                fullWidth
                onClick={handleUpload}
                disabled={!selectedSupplier || !selectedFile || uploadMutation.isPending}
                startIcon={<UploadIcon />}
              >
                업로드
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* 템플릿 다운로드 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                엑셀 템플릿
              </Typography>
              <Typography variant="body2" color="textSecondary" paragraph>
                각 공급사에 맞는 엑셀 템플릿을 다운로드하여 사용하세요.
              </Typography>
              <Grid container spacing={1}>
                {suppliers?.map((supplier: any) => (
                  <Grid item xs={12} key={supplier.supplier_code}>
                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={<DownloadIcon />}
                      onClick={() => downloadTemplate(supplier.supplier_code)}
                    >
                      {supplier.supplier_name} 템플릿
                    </Button>
                  </Grid>
                ))}
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* 업로드 기록 */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                업로드 기록
              </Typography>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>파일명</TableCell>
                    <TableCell>공급사</TableCell>
                    <TableCell>상태</TableCell>
                    <TableCell>처리 결과</TableCell>
                    <TableCell>업로드 시간</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {uploadHistory?.map((upload: any) => (
                    <TableRow key={upload.id}>
                      <TableCell>{upload.filename}</TableCell>
                      <TableCell>
                        <Chip
                          label={upload.supplier.toUpperCase()}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        {upload.status === 'completed' ? (
                          <Chip
                            icon={<CheckIcon />}
                            label="완료"
                            size="small"
                            color="success"
                          />
                        ) : upload.status === 'failed' ? (
                          <Chip
                            icon={<ErrorIcon />}
                            label="실패"
                            size="small"
                            color="error"
                          />
                        ) : (
                          <Chip label="처리 중" size="small" />
                        )}
                      </TableCell>
                      <TableCell>
                        총 {upload.total_rows}행 / 처리 {upload.processed_rows}행
                        {upload.new_products > 0 && ` (신규: ${upload.new_products})`}
                        {upload.updated_products > 0 && ` (업데이트: ${upload.updated_products})`}
                        {upload.error_rows > 0 && (
                          <Chip
                            label={`오류: ${upload.error_rows}`}
                            size="small"
                            color="error"
                            sx={{ ml: 1 }}
                          />
                        )}
                      </TableCell>
                      <TableCell>
                        {format(new Date(upload.upload_time), 'yyyy-MM-dd HH:mm:ss')}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}