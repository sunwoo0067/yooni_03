import React, { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Box,
  TextField,
  Button,
  Alert,
  InputAdornment,
  IconButton,
  CircularProgress,
  Typography,
  Paper,
} from '@mui/material'
import { 
  Visibility, 
  VisibilityOff, 
  Lock,
  CheckCircleOutline,
} from '@mui/icons-material'
import { useForm, Controller } from 'react-hook-form'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { useAppDispatch, useAppSelector } from '@store/hooks'
import { confirmPasswordReset, selectAuthError, selectAuthLoading } from '@store/slices/authSlice'
import type { PasswordResetConfirm } from '@store/slices/authSlice'

interface ResetPasswordFormData extends PasswordResetConfirm {}

export default function ResetPassword() {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const [searchParams] = useSearchParams()
  const isLoading = useAppSelector(selectAuthLoading)
  const authError = useAppSelector(selectAuthError)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  const token = searchParams.get('token')

  const {
    control,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<ResetPasswordFormData>({
    defaultValues: {
      token: token || '',
      password: '',
      confirmPassword: '',
    },
  })

  const watchPassword = watch('password')

  useEffect(() => {
    if (!token) {
      toast.error('유효하지 않은 비밀번호 재설정 링크입니다.')
      navigate('/auth/forgot-password')
    }
  }, [token, navigate])

  const onSubmit = async (data: ResetPasswordFormData) => {
    if (data.password !== data.confirmPassword) {
      toast.error('비밀번호가 일치하지 않습니다.')
      return
    }

    try {
      await dispatch(confirmPasswordReset(data)).unwrap()
      toast.success('비밀번호가 성공적으로 변경되었습니다!')
      navigate('/auth/login')
    } catch (err: any) {
      toast.error(err || '비밀번호 재설정에 실패했습니다.')
    }
  }

  // Password strength validation
  const getPasswordStrength = (password: string) => {
    let strength = 0
    const checks = {
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /\d/.test(password),
      special: /[!@#$%^&*(),.?":{}|<>]/.test(password),
    }

    strength = Object.values(checks).filter(Boolean).length
    return { strength, checks }
  }

  const passwordInfo = getPasswordStrength(watchPassword)

  const getStrengthColor = (strength: number) => {
    if (strength < 2) return 'error'
    if (strength < 4) return 'warning'
    return 'success'
  }

  const getStrengthText = (strength: number) => {
    if (strength < 2) return '약함'
    if (strength < 4) return '보통'
    return '강함'
  }

  if (!token) {
    return null
  }

  return (
    <Box sx={{ width: '100%' }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Typography
          component="h2"
          variant="h5"
          sx={{ mb: 2, textAlign: 'center', fontWeight: 'bold' }}
        >
          새 비밀번호 설정
        </Typography>

        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ mb: 3, textAlign: 'center' }}
        >
          계정의 보안을 위해 강력한 비밀번호를 설정해주세요.
        </Typography>

        {authError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {authError}
          </Alert>
        )}

        <form onSubmit={handleSubmit(onSubmit)}>
          <Controller
            name="password"
            control={control}
            rules={{
              required: '새 비밀번호를 입력해주세요',
              minLength: {
                value: 8,
                message: '비밀번호는 8자 이상이어야 합니다',
              },
            }}
            render={({ field }) => (
              <Box>
                <TextField
                  {...field}
                  margin="normal"
                  required
                  fullWidth
                  label="새 비밀번호"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  error={!!errors.password}
                  helperText={errors.password?.message}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Lock color="action" />
                      </InputAdornment>
                    ),
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          aria-label="toggle password visibility"
                          onClick={() => setShowPassword(!showPassword)}
                          edge="end"
                        >
                          {showPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
                
                {watchPassword && (
                  <Box sx={{ mt: 1 }}>
                    <Typography 
                      variant="caption" 
                      color={`${getStrengthColor(passwordInfo.strength)}.main`}
                      sx={{ fontWeight: 'bold' }}
                    >
                      비밀번호 강도: {getStrengthText(passwordInfo.strength)}
                    </Typography>
                    <Box sx={{ mt: 0.5 }}>
                      {Object.entries(passwordInfo.checks).map(([key, passed]) => (
                        <Typography
                          key={key}
                          variant="caption"
                          sx={{ 
                            display: 'block',
                            color: passed ? 'success.main' : 'text.secondary',
                            fontSize: '0.7rem'
                          }}
                        >
                          <CheckCircleOutline 
                            sx={{ 
                              fontSize: '0.8rem', 
                              mr: 0.5,
                              color: passed ? 'success.main' : 'text.disabled'
                            }} 
                          />
                          {key === 'length' && '8자 이상'}
                          {key === 'uppercase' && '대문자 포함'}
                          {key === 'lowercase' && '소문자 포함'}
                          {key === 'number' && '숫자 포함'}
                          {key === 'special' && '특수문자 포함'}
                        </Typography>
                      ))}
                    </Box>
                  </Box>
                )}
              </Box>
            )}
          />

          <Controller
            name="confirmPassword"
            control={control}
            rules={{
              required: '비밀번호 확인을 입력해주세요',
              validate: (value) =>
                value === watchPassword || '비밀번호가 일치하지 않습니다',
            }}
            render={({ field }) => (
              <TextField
                {...field}
                margin="normal"
                required
                fullWidth
                label="비밀번호 확인"
                type={showConfirmPassword ? 'text' : 'password'}
                autoComplete="new-password"
                error={!!errors.confirmPassword}
                helperText={errors.confirmPassword?.message}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Lock color="action" />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label="toggle password visibility"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        edge="end"
                      >
                        {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
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
              '비밀번호 변경'
            )}
          </Button>

          <Box sx={{ textAlign: 'center' }}>
            <Button
              variant="text"
              onClick={() => navigate('/auth/login')}
              sx={{ textDecoration: 'underline' }}
            >
              로그인 페이지로 돌아가기
            </Button>
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
            <strong>보안 권장사항:</strong>
            <br />
            • 대소문자, 숫자, 특수문자를 조합해주세요.
            <br />
            • 개인정보나 쉬운 단어는 피해주세요.
            <br />
            • 정기적으로 비밀번호를 변경해주세요.
          </Typography>
        </Paper>
      </motion.div>
    </Box>
  )
}