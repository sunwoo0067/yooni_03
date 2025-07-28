import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Box,
  Button,
  Typography,
  Paper,
  Avatar,
  CircularProgress,
  Alert,
} from '@mui/material'
import { 
  MailOutline, 
  CheckCircleOutline, 
  ErrorOutline, 
  Refresh,
} from '@mui/icons-material'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { useAppDispatch, useAppSelector } from '@store/hooks'
import { 
  verifyEmail, 
  resendVerificationEmail,
  selectAuthError,
  selectAuthLoading,
  selectCurrentUser,
} from '@store/slices/authSlice'

export default function VerifyEmail() {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const [searchParams] = useSearchParams()
  const isLoading = useAppSelector(selectAuthLoading)
  const authError = useAppSelector(selectAuthError)
  const currentUser = useAppSelector(selectCurrentUser)
  const [verificationStatus, setVerificationStatus] = useState<'pending' | 'success' | 'error'>('pending')
  const [canResend, setCanResend] = useState(true)
  const [resendCountdown, setResendCountdown] = useState(0)

  const token = searchParams.get('token')

  useEffect(() => {
    if (token) {
      // If there's a token in URL, verify it automatically
      handleVerifyEmail(token)
    } else if (currentUser?.emailVerified) {
      // If user is already verified, redirect to dashboard
      navigate('/dashboard')
    }
  }, [token, currentUser])

  const handleVerifyEmail = async (verificationToken: string) => {
    try {
      await dispatch(verifyEmail({ token: verificationToken })).unwrap()
      setVerificationStatus('success')
      toast.success('이메일 인증이 완료되었습니다!')
      
      // Redirect to dashboard after 3 seconds
      setTimeout(() => {
        navigate('/dashboard')
      }, 3000)
    } catch (err: any) {
      setVerificationStatus('error')
      toast.error(err || '이메일 인증에 실패했습니다.')
    }
  }

  const handleResendVerification = async () => {
    if (!canResend) return

    try {
      await dispatch(resendVerificationEmail()).unwrap()
      toast.success('인증 이메일을 다시 발송했습니다!')
      
      // Start countdown
      setCanResend(false)
      setResendCountdown(60)
      
      const countdown = setInterval(() => {
        setResendCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(countdown)
            setCanResend(true)
            return 0
          }
          return prev - 1
        })
      }, 1000)
    } catch (err: any) {
      toast.error(err || '이메일 재발송에 실패했습니다.')
    }
  }

  const renderContent = () => {
    if (verificationStatus === 'pending' && token) {
      return (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <Box sx={{ textAlign: 'center', mb: 4 }}>
            <CircularProgress size={60} sx={{ mb: 2 }} />
            <Typography variant="h6" sx={{ mb: 2 }}>
              이메일 인증 중...
            </Typography>
            <Typography variant="body2" color="text.secondary">
              잠시만 기다려주세요.
            </Typography>
          </Box>
        </motion.div>
      )
    }

    if (verificationStatus === 'success') {
      return (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <Box sx={{ textAlign: 'center', mb: 4 }}>
            <Avatar
              sx={{
                width: 80,
                height: 80,
                bgcolor: 'success.light',
                mx: 'auto',
                mb: 2,
              }}
            >
              <CheckCircleOutline sx={{ fontSize: 40, color: 'success.main' }} />
            </Avatar>

            <Typography
              component="h2"
              variant="h5"
              sx={{ mb: 2, fontWeight: 'bold', color: 'success.main' }}
            >
              이메일 인증 완료!
            </Typography>

            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              계정 인증이 성공적으로 완료되었습니다.
              <br />
              이제 모든 서비스를 이용하실 수 있습니다.
            </Typography>

            <Button
              fullWidth
              variant="contained"
              onClick={() => navigate('/dashboard')}
              sx={{ py: 1.5 }}
            >
              대시보드로 이동
            </Button>
          </Box>
        </motion.div>
      )
    }

    if (verificationStatus === 'error') {
      return (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <Box sx={{ textAlign: 'center', mb: 4 }}>
            <Avatar
              sx={{
                width: 80,
                height: 80,
                bgcolor: 'error.light',
                mx: 'auto',
                mb: 2,
              }}
            >
              <ErrorOutline sx={{ fontSize: 40, color: 'error.main' }} />
            </Avatar>

            <Typography
              component="h2"
              variant="h5"
              sx={{ mb: 2, fontWeight: 'bold', color: 'error.main' }}
            >
              인증 실패
            </Typography>

            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              이메일 인증에 실패했습니다.
              <br />
              링크가 만료되었거나 잘못된 링크일 수 있습니다.
            </Typography>

            {authError && (
              <Alert severity="error" sx={{ mb: 3 }}>
                {authError}
              </Alert>
            )}

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Button
                fullWidth
                variant="contained"
                startIcon={<Refresh />}
                onClick={handleResendVerification}
                disabled={!canResend || isLoading}
                sx={{ py: 1.5 }}
              >
                {isLoading ? (
                  <CircularProgress size={20} color="inherit" />
                ) : canResend ? (
                  '인증 이메일 재발송'
                ) : (
                  `재발송 가능까지 ${resendCountdown}초`
                )}
              </Button>

              <Button
                fullWidth
                variant="outlined"
                onClick={() => navigate('/auth/login')}
              >
                로그인 페이지로 돌아가기
              </Button>
            </Box>
          </Box>
        </motion.div>
      )
    }

    // Default: waiting for verification
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Avatar
            sx={{
              width: 80,
              height: 80,
              bgcolor: 'info.light',
              mx: 'auto',
              mb: 2,
            }}
          >
            <MailOutline sx={{ fontSize: 40, color: 'info.main' }} />
          </Avatar>

          <Typography
            component="h2"
            variant="h5"
            sx={{ mb: 2, fontWeight: 'bold' }}
          >
            이메일을 확인해주세요
          </Typography>

          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            가입하신 이메일로 인증 링크를 발송했습니다.
            <br />
            이메일의 링크를 클릭하여 계정을 인증해주세요.
          </Typography>

          {currentUser?.email && (
            <Paper
              elevation={0}
              sx={{
                p: 2,
                bgcolor: 'grey.100',
                borderRadius: 2,
                mb: 3,
              }}
            >
              <Typography
                variant="body1"
                sx={{ fontWeight: 'bold', color: 'primary.main' }}
              >
                {currentUser.email}
              </Typography>
            </Paper>
          )}

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Button
              fullWidth
              variant="contained"
              startIcon={<Refresh />}
              onClick={handleResendVerification}
              disabled={!canResend || isLoading}
              sx={{ py: 1.5 }}
            >
              {isLoading ? (
                <CircularProgress size={20} color="inherit" />
              ) : canResend ? (
                '인증 이메일 재발송'
              ) : (
                `재발송 가능까지 ${resendCountdown}초`
              )}
            </Button>

            <Button
              fullWidth
              variant="outlined"
              onClick={() => navigate('/auth/login')}
            >
              로그인 페이지로 돌아가기
            </Button>
          </Box>
        </Box>
      </motion.div>
    )
  }

  return (
    <Box sx={{ width: '100%' }}>
      {renderContent()}

      <Paper
        elevation={0}
        sx={{
          mt: 3,
          p: 2,
          bgcolor: 'warning.light',
          borderRadius: 2,
          border: 1,
          borderColor: 'warning.main',
        }}
      >
        <Typography variant="body2" color="warning.dark">
          <strong>이메일을 받지 못하셨나요?</strong>
          <br />
          • 스팸 폴더를 확인해보세요.
          <br />
          • 이메일 주소가 정확한지 확인해보세요.
          <br />
          • 위의 "재발송" 버튼을 클릭해보세요.
          <br />
          • 문제가 지속된다면 고객지원팀에 문의해주세요.
        </Typography>
      </Paper>
    </Box>
  )
}