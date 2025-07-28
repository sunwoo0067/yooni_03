import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  TextField,
  Button,
  FormControlLabel,
  Checkbox,
  Link,
  Grid,
  Alert,
  InputAdornment,
  IconButton,
  CircularProgress,
  Typography,
  Divider,
} from '@mui/material'
import { 
  Visibility, 
  VisibilityOff, 
  Email, 
  Lock, 
  Person,
  CheckCircleOutline,
} from '@mui/icons-material'
import { useForm, Controller } from 'react-hook-form'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { useAppDispatch, useAppSelector } from '@store/hooks'
import { register, selectAuthError, selectAuthLoading } from '@store/slices/authSlice'
import type { RegisterData } from '@store/slices/authSlice'

interface RegisterFormData extends RegisterData {}

export default function Register() {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const isLoading = useAppSelector(selectAuthLoading)
  const authError = useAppSelector(selectAuthError)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  const {
    control,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterFormData>({
    defaultValues: {
      name: '',
      email: '',
      password: '',
      confirmPassword: '',
      acceptTerms: false,
    },
  })

  const watchPassword = watch('password')

  const onSubmit = async (data: RegisterFormData) => {
    if (data.password !== data.confirmPassword) {
      toast.error('비밀번호가 일치하지 않습니다.')
      return
    }

    try {
      await dispatch(register(data)).unwrap()
      toast.success('회원가입이 완료되었습니다! 이메일을 확인해주세요.')
      navigate('/auth/verify-email')
    } catch (err: any) {
      toast.error(err || '회원가입에 실패했습니다.')
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

  return (
    <Box sx={{ width: '100%' }}>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        <Typography
          component="h2"
          variant="h5"
          sx={{ mb: 3, textAlign: 'center', fontWeight: 'bold' }}
        >
          회원가입
        </Typography>

        {authError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {authError}
          </Alert>
        )}

        <form onSubmit={handleSubmit(onSubmit)}>
          <Controller
            name="name"
            control={control}
            rules={{
              required: '이름을 입력해주세요',
              minLength: {
                value: 2,
                message: '이름은 2자 이상이어야 합니다',
              },
            }}
            render={({ field }) => (
              <TextField
                {...field}
                margin="normal"
                required
                fullWidth
                label="이름"
                autoComplete="name"
                autoFocus
                error={!!errors.name}
                helperText={errors.name?.message}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Person color="action" />
                    </InputAdornment>
                  ),
                }}
              />
            )}
          />

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

          <Controller
            name="password"
            control={control}
            rules={{
              required: '비밀번호를 입력해주세요',
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
                  label="비밀번호"
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

          <Controller
            name="acceptTerms"
            control={control}
            rules={{
              required: '이용약관에 동의해주세요',
            }}
            render={({ field }) => (
              <FormControlLabel
                control={
                  <Checkbox 
                    {...field} 
                    checked={field.value}
                    color="primary"
                    sx={{ mt: 1 }}
                  />
                }
                label={
                  <Typography variant="body2">
                    <Link href="/terms" target="_blank" rel="noopener">
                      이용약관
                    </Link>
                    {' 및 '}
                    <Link href="/privacy" target="_blank" rel="noopener">
                      개인정보 처리방침
                    </Link>
                    에 동의합니다
                  </Typography>
                }
                sx={{ alignItems: 'flex-start', mt: 1 }}
              />
            )}
          />
          {errors.acceptTerms && (
            <Typography variant="caption" color="error" sx={{ display: 'block', mt: 0.5 }}>
              {errors.acceptTerms.message}
            </Typography>
          )}

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
              '회원가입'
            )}
          </Button>

          <Divider sx={{ my: 2 }}>
            <Typography variant="body2" color="text.secondary">
              또는
            </Typography>
          </Divider>

          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              이미 계정이 있으신가요?{' '}
              <Link 
                component="button" 
                type="button"
                variant="body2"
                onClick={() => navigate('/auth/login')}
                sx={{ fontWeight: 'bold' }}
              >
                로그인
              </Link>
            </Typography>
          </Box>

          <Box sx={{ mt: 3, textAlign: 'center' }}>
            <Typography variant="caption" color="textSecondary">
              회원가입을 완료하면 서비스 이용약관 및 개인정보 처리방침에 동의하는 것으로 간주됩니다.
            </Typography>
          </Box>
        </form>
      </motion.div>
    </Box>
  )
}