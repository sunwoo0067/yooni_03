import React, { useState } from 'react'
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Alert,
  Stack,
  Divider,
  Chip,
  Grid,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  CircularProgress,
} from '@mui/material'
import {
  Storage as Database,
  Api,
  BugReport,
  DataObject,
  CheckCircle,
  Error,
  Warning,
  Cloud,
  Storage,
  Router,
} from '@mui/icons-material'
import { apiHelpers, productAPI, platformAPI, orderAPI, analyticsAPI } from '@services/api'
import { useNotification } from '@components/ui/NotificationSystem'

const DevTools: React.FC = () => {
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const [apiStatus, setApiStatus] = useState<{[key: string]: 'idle' | 'testing' | 'success' | 'error'}>({})
  const [sampleDataStatus, setSampleDataStatus] = useState<'idle' | 'creating' | 'success' | 'error'>('idle')
  const [logs, setLogs] = useState<string[]>([])
  
  const notification = useNotification()

  const addLog = (message: string) => {
    setLogs(prev => [...prev, `${new Date().toLocaleTimeString()}: ${message}`])
  }

  const testBackendConnection = async () => {
    setConnectionStatus('testing')
    addLog('백엔드 연결 테스트 시작...')

    try {
      const connected = await apiHelpers.testConnection()
      if (connected) {
        setConnectionStatus('success')
        addLog('✅ 백엔드 연결 성공!')
        notification.showSuccess(
          '백엔드 연결 성공',
          'SQLite 데이터베이스와 성공적으로 연결되었습니다.'
        )
      } else {
        setConnectionStatus('error')
        addLog('❌ 백엔드 연결 실패')
      }
    } catch (error) {
      setConnectionStatus('error')
      addLog(`❌ 백엔드 연결 오류: ${error}`)
      notification.showError(
        '백엔드 연결 실패',
        '서버가 실행 중인지 확인해주세요. (http://localhost:8000)'
      )
    }
  }

  const testAllAPIs = async () => {
    const apis = [
      { name: 'products', fn: () => productAPI.getProducts() },
      { name: 'platforms', fn: () => platformAPI.getAccounts() },
      { name: 'orders', fn: () => orderAPI.getOrders() },
      { name: 'dashboard', fn: () => analyticsAPI.getDashboard() },
    ]

    for (const api of apis) {
      setApiStatus(prev => ({ ...prev, [api.name]: 'testing' }))
      addLog(`${api.name} API 테스트 중...`)

      try {
        const response = await api.fn()
        setApiStatus(prev => ({ ...prev, [api.name]: 'success' }))
        addLog(`✅ ${api.name} API 성공 (${Array.isArray(response.data) ? response.data.length : 'N/A'}개 항목)`)
      } catch (error) {
        setApiStatus(prev => ({ ...prev, [api.name]: 'error' }))
        addLog(`❌ ${api.name} API 실패: ${error}`)
      }
    }
  }

  const createSampleData = async () => {
    setSampleDataStatus('creating')
    addLog('샘플 데이터 생성 시작...')

    try {
      const result = await apiHelpers.createSampleData()
      setSampleDataStatus('success')
      addLog(`✅ 샘플 데이터 생성 완료: ${result.created.products.length}개 상품, ${result.created.accounts.length}개 계정`)
      
      notification.showSuccess(
        '샘플 데이터 생성 완료',
        `${result.created.products.length}개 상품과 ${result.created.accounts.length}개 플랫폼 계정이 생성되었습니다.`,
        [
          {
            label: '상품 페이지로 이동',
            action: () => window.location.href = '/products',
            variant: 'contained'
          }
        ]
      )
    } catch (error) {
      setSampleDataStatus('error')
      addLog(`❌ 샘플 데이터 생성 실패: ${error}`)
      notification.showError(
        '샘플 데이터 생성 실패',
        '백엔드 서버 연결을 확인해주세요.'
      )
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success': return <CheckCircle color="success" />
      case 'error': return <Error color="error" />
      case 'testing': case 'creating': return <CircularProgress size={20} />
      default: return <Warning color="disabled" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'success'
      case 'error': return 'error'
      case 'testing': case 'creating': return 'primary'
      default: return 'default'
    }
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          🛠️ 개발자 도구 & 실제 데이터 연결
        </Typography>
        <Typography variant="body1" color="text.secondary">
          백엔드 API 연결 상태를 확인하고 실제 데이터베이스와 연동하세요
        </Typography>
      </Box>

      {/* Connection Status Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 2 }}>
                <Database color="primary" />
                <Typography variant="h6">백엔드 연결 상태</Typography>
                <Chip 
                  label={connectionStatus === 'idle' ? '테스트 필요' : connectionStatus}
                  color={getStatusColor(connectionStatus) as any}
                  icon={getStatusIcon(connectionStatus)}
                />
              </Stack>
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                SQLite 데이터베이스 (yooni_dropshipping.db)
              </Typography>
              
              <Button
                variant="contained"
                onClick={testBackendConnection}
                disabled={connectionStatus === 'testing'}
                startIcon={connectionStatus === 'testing' ? <CircularProgress size={16} /> : <Api />}
              >
                연결 테스트
              </Button>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 2 }}>
                <DataObject color="primary" />
                <Typography variant="h6">샘플 데이터</Typography>
                <Chip 
                  label={sampleDataStatus === 'idle' ? '생성 가능' : sampleDataStatus}
                  color={getStatusColor(sampleDataStatus) as any}
                  icon={getStatusIcon(sampleDataStatus)}
                />
              </Stack>
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                테스트용 상품 및 플랫폼 계정 데이터
              </Typography>
              
              <Button
                variant="contained"
                onClick={createSampleData}
                disabled={sampleDataStatus === 'creating'}
                startIcon={sampleDataStatus === 'creating' ? <CircularProgress size={16} /> : <Storage />}
              >
                샘플 데이터 생성
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* API Status */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 2 }}>
          <Router color="primary" />
          <Typography variant="h6">API 엔드포인트 테스트</Typography>
          <Button
            variant="outlined"
            onClick={testAllAPIs}
            disabled={Object.values(apiStatus).some(status => status === 'testing')}
          >
            전체 API 테스트
          </Button>
        </Stack>

        <Grid container spacing={2}>
          {['products', 'platforms', 'orders', 'dashboard'].map((apiName) => (
            <Grid item xs={6} md={3} key={apiName}>
              <Stack direction="row" alignItems="center" spacing={1}>
                {getStatusIcon(apiStatus[apiName] || 'idle')}
                <Typography variant="body2">
                  {apiName} API
                </Typography>
                <Chip 
                  size="small"
                  label={apiStatus[apiName] || 'idle'}
                  color={getStatusColor(apiStatus[apiName] || 'idle') as any}
                />
              </Stack>
            </Grid>
          ))}
        </Grid>
      </Paper>

      {/* Server Info */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          🌐 서버 정보
        </Typography>
        
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <List dense>
              <ListItem>
                <ListItemIcon><Cloud /></ListItemIcon>
                <ListItemText 
                  primary="백엔드 서버" 
                  secondary="http://localhost:8000"
                />
              </ListItem>
              <ListItem>
                <ListItemIcon><Database /></ListItemIcon>
                <ListItemText 
                  primary="데이터베이스" 
                  secondary="SQLite (yooni_dropshipping.db)"
                />
              </ListItem>
            </List>
          </Grid>
          <Grid item xs={12} md={6}>
            <List dense>
              <ListItem>
                <ListItemIcon><Api /></ListItemIcon>
                <ListItemText 
                  primary="API 문서" 
                  secondary={
                    <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">
                      http://localhost:8000/docs
                    </a>
                  }
                />
              </ListItem>
              <ListItem>
                <ListItemIcon><BugReport /></ListItemIcon>
                <ListItemText 
                  primary="헬스 체크" 
                  secondary={
                    <a href="http://localhost:8000/health" target="_blank" rel="noopener noreferrer">
                      http://localhost:8000/health
                    </a>
                  }
                />
              </ListItem>
            </List>
          </Grid>
        </Grid>
      </Paper>

      {/* Activity Logs */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          📊 활동 로그
        </Typography>
        
        <Box 
          sx={{ 
            maxHeight: 300, 
            overflow: 'auto', 
            bgcolor: 'grey.50', 
            p: 2, 
            borderRadius: 1,
            fontFamily: 'monospace',
            fontSize: '0.875rem'
          }}
        >
          {logs.length === 0 ? (
            <Typography color="text.secondary">
              아직 활동이 없습니다. 연결 테스트를 시작해보세요.
            </Typography>
          ) : (
            logs.map((log, index) => (
              <div key={index}>{log}</div>
            ))
          )}
        </Box>
        
        {logs.length > 0 && (
          <Button 
            size="small" 
            onClick={() => setLogs([])}
            sx={{ mt: 1 }}
          >
            로그 지우기
          </Button>
        )}
      </Paper>

      {/* Quick Actions */}
      <Alert severity="info" sx={{ mt: 3 }}>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          🚀 다음 단계:
        </Typography>
        <Typography variant="body2">
          1. 백엔드 연결 테스트 → 2. 샘플 데이터 생성 → 3. 실제 상품/플랫폼 페이지에서 데이터 확인
        </Typography>
      </Alert>
    </Box>
  )
}

export default DevTools