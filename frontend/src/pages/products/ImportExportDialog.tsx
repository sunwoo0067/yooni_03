import React, { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Tabs,
  Tab,
  Alert,
  LinearProgress,
} from '@mui/material'
import { FileUpload, FileDownload } from '@mui/icons-material'
import { toast } from 'react-hot-toast'

interface ImportExportDialogProps {
  open: boolean
  onClose: () => void
}

const ImportExportDialog: React.FC<ImportExportDialogProps> = ({ open, onClose }) => {
  const [tabValue, setTabValue] = useState(0)
  const [importing, setImporting] = useState(false)

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      setImporting(true)
      // Simulate import
      setTimeout(() => {
        setImporting(false)
        toast.success('상품 가져오기가 완료되었습니다.')
        onClose()
      }, 2000)
    }
  }

  const handleExport = () => {
    // Simulate export
    toast.success('상품 내보내기를 시작합니다.')
    onClose()
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>상품 가져오기/내보내기</DialogTitle>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
          <Tab label="가져오기" icon={<FileUpload />} />
          <Tab label="내보내기" icon={<FileDownload />} />
        </Tabs>
      </Box>
      <DialogContent>
        {tabValue === 0 && (
          <Box sx={{ py: 2 }}>
            <Alert severity="info" sx={{ mb: 3 }}>
              CSV 또는 Excel 파일을 업로드하여 상품을 일괄 등록할 수 있습니다.
            </Alert>
            <Button
              variant="contained"
              component="label"
              fullWidth
              disabled={importing}
              startIcon={<FileUpload />}
            >
              파일 선택
              <input
                type="file"
                hidden
                accept=".csv,.xlsx,.xls"
                onChange={handleFileUpload}
              />
            </Button>
            {importing && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" gutterBottom>
                  상품을 가져오는 중...
                </Typography>
                <LinearProgress />
              </Box>
            )}
          </Box>
        )}
        {tabValue === 1 && (
          <Box sx={{ py: 2 }}>
            <Alert severity="info" sx={{ mb: 3 }}>
              현재 등록된 모든 상품을 CSV 파일로 내보낼 수 있습니다.
            </Alert>
            <Button
              variant="contained"
              fullWidth
              onClick={handleExport}
              startIcon={<FileDownload />}
            >
              CSV로 내보내기
            </Button>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>닫기</Button>
      </DialogActions>
    </Dialog>
  )
}

export default ImportExportDialog