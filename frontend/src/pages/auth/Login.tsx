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
} from '@mui/material'
import { Visibility, VisibilityOff, Email, Lock } from '@mui/icons-material'
import { useForm, Controller } from 'react-hook-form'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { useAppDispatch, useAppSelector } from '@store/hooks'
import { login, selectAuthError, selectAuthLoading } from '@store/slices/authSlice'

interface LoginFormData {
  email: string
  password: string
  rememberMe: boolean
}

export default function Login() {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const isLoading = useAppSelector(selectAuthLoading)
  const authError = useAppSelector(selectAuthError)
  const [showPassword, setShowPassword] = useState(false)

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    defaultValues: {
      email: '',
      password: '',
      rememberMe: false,
    },
  })

  const onSubmit = async (data: LoginFormData) => {
    try {
      await dispatch(login({
        email: data.email,
        password: data.password,
        rememberMe: data.rememberMe,
      })).unwrap()

      toast.success('로그인에 성공했습니다!')
      navigate('/dashboard')
    } catch (err: any) {
      toast.error(err || '로그인에 실패했습니다. 이메일과 비밀번호를 확인해주세요.')
    }
  }

  // Demo login
  const handleDemoLogin = () => {
    onSubmit({
      email: 'demo@yooni.com',
      password: 'demo1234',
      rememberMe: true,
    })
  }

  return (
    <Box sx={{ width: '100%' }}>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
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

          <Controller
            name="password"
            control={control}
            rules={{
              required: '비밀번호를 입력해주세요',
              minLength: {
                value: 6,
                message: '비밀번호는 6자 이상이어야 합니다',
              },
            }}
            render={({ field }) => (
              <TextField
                {...field}
                margin="normal"
                required
                fullWidth
                label="비밀번호"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
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
            )}
          />

          <Controller
            name="rememberMe"
            control={control}
            render={({ field }) => (
              <FormControlLabel
                control={<Checkbox {...field} checked={field.value} color="primary" />}
                label="로그인 상태 유지"
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
              '로그인'
            )}
          </Button>

          <Button
            fullWidth
            variant="outlined"
            onClick={handleDemoLogin}
            sx={{ mb: 2 }}
            disabled={isLoading}
          >
            데모 계정으로 로그인
          </Button>

          <Grid container>
            <Grid item xs>
              <Link 
                component="button" 
                type="button"
                variant="body2"
                onClick={() => navigate('/auth/forgot-password')}
              >
                비밀번호를 잊으셨나요?
              </Link>
            </Grid>
            <Grid item>
              <Link 
                component="button" 
                type="button"
                variant="body2"
                onClick={() => navigate('/auth/register')}
              >
                회원가입
              </Link>
            </Grid>
          </Grid>

          <Box sx={{ mt: 3, textAlign: 'center' }}>
            <Typography variant="caption" color="textSecondary">
              로그인하면 서비스 이용약관 및 개인정보 처리방침에 동의하는 것으로 간주됩니다.
            </Typography>
          </Box>
        </form>
      </motion.div>
    </Box>
  )
}