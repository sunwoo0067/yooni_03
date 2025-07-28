/**
 * 에러 바운더리 및 에러 UI 컴포넌트
 * React 에러를 포착하고 사용자 친화적인 에러 UI 제공
 */

import React, { Component, ErrorInfo, ReactNode } from 'react'
import {
  Box,
  Typography,
  Button,
  Stack,
  Card,
  CardContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Alert,
  useTheme,
  Divider,
} from '@mui/material'
import {
  ErrorOutline,
  Refresh,
  Home,
  ExpandMore,
  BugReport,
  ContentCopy,
  CheckCircle,
} from '@mui/icons-material'
import { motion } from 'framer-motion'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
  errorId: string
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: '',
    }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
      errorId: Date.now().toString(36) + Math.random().toString(36).substr(2, 5),
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
      errorInfo,
    })

    // 에러 로깅
    console.error('ErrorBoundary caught an error:', error, errorInfo)

    // 사용자 정의 에러 핸들러 호출
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }

    // 개발 환경에서 에러 리포팅 (실제로는 Sentry 등 사용)
    if (process.env.NODE_ENV === 'development') {
      console.group('🐛 Error Details')
      console.error('Error:', error)
      console.error('Error Info:', errorInfo)
      console.error('Component Stack:', errorInfo.componentStack)
      console.groupEnd()
    }
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: '',
    })
  }

  handleReload = () => {
    window.location.reload()
  }

  handleGoHome = () => {
    window.location.href = '/'
  }

  handleCopyError = async () => {
    const errorDetails = {
      errorId: this.state.errorId,
      message: this.state.error?.message,
      stack: this.state.error?.stack,
      componentStack: this.state.errorInfo?.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
    }

    try {
      await navigator.clipboard.writeText(JSON.stringify(errorDetails, null, 2))
      // TODO: 성공 알림 표시
    } catch (err) {
      console.error('Failed to copy error details:', err)
    }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return <ErrorFallback
        error={this.state.error}
        errorInfo={this.state.errorInfo}
        errorId={this.state.errorId}
        onRetry={this.handleRetry}
        onReload={this.handleReload}
        onGoHome={this.handleGoHome}
        onCopyError={this.handleCopyError}
      />
    }

    return this.props.children
  }
}

// 에러 폴백 UI 컴포넌트
interface ErrorFallbackProps {
  error: Error | null
  errorInfo: ErrorInfo | null
  errorId: string
  onRetry: () => void
  onReload: () => void
  onGoHome: () => void
  onCopyError: () => void
}

const ErrorFallback: React.FC<ErrorFallbackProps> = ({
  error,
  errorInfo,
  errorId,
  onRetry,
  onReload,
  onGoHome,
  onCopyError,
}) => {
  const theme = useTheme()
  const [copied, setCopied] = React.useState(false)

  const handleCopyWithFeedback = async () => {
    await onCopyError()
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const getErrorSeverity = () => {
    if (error?.message.includes('ChunkLoadError')) return 'warning'
    if (error?.message.includes('Network')) return 'info'
    return 'error'
  }

  const getErrorSolution = () => {
    if (error?.message.includes('ChunkLoadError')) {
      return {
        title: '새로운 업데이트가 있습니다',
        description: '페이지를 새로고침하면 최신 버전으로 업데이트됩니다.',
        action: '새로고침',
        handler: onReload,
      }
    }
    if (error?.message.includes('Network')) {
      return {
        title: '네트워크 연결 문제',
        description: '인터넷 연결을 확인하고 다시 시도해주세요.',
        action: '재시도',
        handler: onRetry,
      }
    }
    return {
      title: '예상치 못한 오류',
      description: '일시적인 문제일 수 있습니다. 다시 시도해주세요.',
      action: '재시도',
      handler: onRetry,
    }
  }

  const solution = getErrorSolution()
  const severity = getErrorSeverity()

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        minHeight="60vh"
        px={4}
        py={8}
      >
        <Card sx={{ maxWidth: 600, width: '100%' }}>
          <CardContent sx={{ p: 4 }}>
            {/* 에러 아이콘 */}
            <Box display="flex" justifyContent="center" mb={3}>
              <Box
                sx={{
                  p: 2,
                  borderRadius: '50%',
                  backgroundColor: `${severity}.light`,
                  color: `${severity}.main`,
                }}
              >
                <ErrorOutline sx={{ fontSize: 64 }} />
              </Box>
            </Box>

            {/* 에러 제목 */}
            <Typography 
              variant="h5" 
              fontWeight={600} 
              textAlign="center" 
              gutterBottom
            >
              {solution.title}
            </Typography>

            {/* 에러 설명 */}
            <Typography 
              variant="body1" 
              color="text.secondary" 
              textAlign="center" 
              sx={{ mb: 3 }}
            >
              {solution.description}
            </Typography>

            {/* 에러 ID */}
            <Box display="flex" justifyContent="center" mb={4}>
              <Chip 
                label={`오류 ID: ${errorId}`} 
                size="small" 
                variant="outlined"
                color={severity}
              />
            </Box>

            {/* 액션 버튼들 */}
            <Stack spacing={2} direction="column" alignItems="center">
              <Button
                variant="contained"
                size="large"
                startIcon={<Refresh />}
                onClick={solution.handler}
                sx={{ minWidth: 200 }}
              >
                {solution.action}
              </Button>

              <Stack spacing={1} direction="row">
                <Button
                  variant="outlined"
                  startIcon={<Home />}
                  onClick={onGoHome}
                >
                  홈으로 가기
                </Button>
                <Button
                  variant="outlined"
                  onClick={onReload}
                >
                  페이지 새로고침
                </Button>
              </Stack>
            </Stack>

            <Divider sx={{ my: 3 }} />

            {/* 개발자 정보 */}
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography variant="body2" color="text.secondary">
                  개발자 정보 (문제 신고용)
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Stack spacing={2}>
                  <Alert severity="info" variant="outlined">
                    문제가 지속되면 아래 정보를 복사하여 개발팀에 문의해주세요.
                  </Alert>
                  
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      에러 메시지:
                    </Typography>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace', p: 1, bgcolor: 'grey.100', borderRadius: 1 }}>
                      {error?.message || 'Unknown error'}
                    </Typography>
                  </Box>

                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={copied ? <CheckCircle /> : <ContentCopy />}
                    onClick={handleCopyWithFeedback}
                    color={copied ? 'success' : 'primary'}
                  >
                    {copied ? '복사됨!' : '에러 정보 복사'}
                  </Button>
                </Stack>
              </AccordionDetails>
            </Accordion>
          </CardContent>
        </Card>
      </Box>
    </motion.div>
  )
}

export default ErrorBoundary

// 특화된 에러 바운더리들
export const RouteErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ErrorBoundary
    onError={(error, errorInfo) => {
      console.error('Route error:', error, errorInfo)
      // 라우트 에러 추적
    }}
  >
    {children}
  </ErrorBoundary>
)

export const ComponentErrorBoundary: React.FC<{ children: ReactNode; componentName?: string }> = ({ 
  children, 
  componentName 
}) => (
  <ErrorBoundary
    onError={(error, errorInfo) => {
      console.error(`Component error in ${componentName}:`, error, errorInfo)
    }}
    fallback={
      <Alert severity="error" sx={{ m: 2 }}>
        <Typography variant="body2">
          {componentName ? `${componentName} 컴포넌트` : '일부 기능'}에서 오류가 발생했습니다.
        </Typography>
        <Button size="small" onClick={() => window.location.reload()}>
          새로고침
        </Button>
      </Alert>
    }
  >
    {children}
  </ErrorBoundary>
)

// 네트워크 에러 전용 컴포넌트
export const NetworkError: React.FC<{ onRetry: () => void }> = ({ onRetry }) => (
  <Box textAlign="center" py={4}>
    <ErrorOutline color="warning" sx={{ fontSize: 48, mb: 2 }} />
    <Typography variant="h6" gutterBottom>
      네트워크 연결 오류
    </Typography>
    <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
      인터넷 연결을 확인하고 다시 시도해주세요.
    </Typography>
    <Button variant="contained" onClick={onRetry} startIcon={<Refresh />}>
      다시 시도
    </Button>
  </Box>
)

// 데이터 로딩 에러 컴포넌트
export const DataLoadError: React.FC<{ 
  message?: string
  onRetry?: () => void 
  onGoBack?: () => void 
}> = ({ 
  message = "데이터를 불러올 수 없습니다", 
  onRetry, 
  onGoBack 
}) => (
  <Box textAlign="center" py={4}>
    <ErrorOutline color="error" sx={{ fontSize: 48, mb: 2 }} />
    <Typography variant="h6" gutterBottom>
      {message}
    </Typography>
    <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
      일시적인 문제일 수 있습니다. 잠시 후 다시 시도해주세요.
    </Typography>
    <Stack direction="row" spacing={2} justifyContent="center">
      {onRetry && (
        <Button variant="contained" onClick={onRetry} startIcon={<Refresh />}>
          다시 시도
        </Button>
      )}
      {onGoBack && (
        <Button variant="outlined" onClick={onGoBack}>
          이전으로
        </Button>
      )}
    </Stack>
  </Box>
)