import React from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  TextField,
  Button,
  Link,
  Alert,
  InputAdornment,
  CircularProgress,
  Typography,
  Paper,
} from '@mui/material'
import { Email, ArrowBack } from '@mui/icons-material'
import { useForm, Controller } from 'react-hook-form'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { useAppDispatch, useAppSelector } from '@store/hooks'
import { requestPasswordReset, selectAuthError, selectAuthLoading } from '@store/slices/authSlice'
import type { PasswordResetRequest } from '@store/slices/authSlice'

interface ForgotPasswordFormData extends PasswordResetRequest {}

export default function ForgotPassword() {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const isLoading = useAppSelector(selectAuthLoading)
  const authError = useAppSelector(selectAuthError)

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormData>({
    defaultValues: {
      email: '',
    },
  })

  const onSubmit = async (data: ForgotPasswordFormData) => {
    try {
      await dispatch(requestPasswordReset(data)).unwrap()
      toast.success('비밀번호 재설정 이메일을 발송했습니다!')
      navigate('/auth/reset-password-sent', { state: { email: data.email } })
    } catch (err: any) {
      toast.error(err || '비밀번호 재설정 요청에 실패했습니다.')
    }
  }

  return (
    <Box sx={{ width: '100%' }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 1 }}>
          <Button
            startIcon={<ArrowBack />}
            onClick={() => navigate('/auth/login')}
            variant="text"
            size="small"
          >
            로그인으로 돌아가기
          </Button>
        </Box>

        <Typography
          component="h2"
          variant="h5"
          sx={{ mb: 2, textAlign: 'center', fontWeight: 'bold' }}
        >
          비밀번호 찾기
        </Typography>

        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ mb: 3, textAlign: 'center' }}
        >
          가입하신 이메일 주소를 입력하시면 비밀번호 재설정 링크를 보내드립니다.
        </Typography>

        {authError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {authError}
          </Alert>
        )}

        <form onSubmit={handleSubmit(onSubmit)}>
          <Controller
            name="email"
            control={control}
            rules={{
              required: '이메일을 입력해주세요',
              pattern: {
                value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                message: '올바른 이메일 형식이 아닙니다',
              },
            }}
            render={({ field }) => (
              <TextField
                {...field}
                margin="normal"
                required
                fullWidth
                label="이메일"
                autoComplete="email"
                autoFocus
                error={!!errors.email}
                helperText={errors.email?.message}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Email color="action" />
                    </InputAdornment>
                  ),
                }}
              />
            )}
          />

          <Button
            type="submit"
            fullWidth
            variant="contained"
            sx={{ mt: 3, mb: 2, py: 1.5 }}
            disabled={isLoading}
          >
            {isLoading ? (
              <CircularProgress size={24} color="inherit" />
            ) : (
              '비밀번호 재설정 이메일 발송'
            )}
          </Button>

          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              이메일이 기억나지 않으시나요?{' '}
              <Link 
                component="button" 
                type="button"
                variant="body2"
                onClick={() => navigate('/contact')}
                sx={{ fontWeight: 'bold' }}
              >
                고객지원 문의
              </Link>
            </Typography>
          </Box>
        </form>

        <Paper
          elevation={0}
          sx={{
            mt: 3,
            p: 2,
            bgcolor: 'info.light',
            borderRadius: 2,
            border: 1,
            borderColor: 'info.main',
          }}
        >
          <Typography variant="body2" color="info.dark">
            <strong>알려드립니다:</strong>
            <br />
            • 비밀번호 재설정 이메일이 스팸 폴더에 있을 수 있습니다.
            <br />
            • 이메일이 도착하지 않는다면 잠시 후 다시 시도해주세요.
            <br />
            • 계속 문제가 있다면 고객지원팀에 문의해주세요.
          </Typography>
        </Paper>
      </motion.div>
    </Box>
  )
}