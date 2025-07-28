import React, { useState } from 'react'
import {
  Box,
  Card,
  CardHeader,
  CardContent,
  TextField,
  Button,
  Avatar,
  IconButton,
  Typography,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  InputAdornment,
  Divider,
  CircularProgress,
} from '@mui/material'
import {
  Edit as EditIcon,
  PhotoCamera,
  Visibility,
  VisibilityOff,
  Save as SaveIcon,
  Cancel as CancelIcon,
} from '@mui/icons-material'
import { useForm, Controller } from 'react-hook-form'
import toast from 'react-hot-toast'
import { useAppDispatch, useAppSelector } from '@store/hooks'
import {
  updateProfile,
  changePassword,
  selectCurrentUser,
  selectAuthLoading,
  selectAuthError,
} from '@store/slices/authSlice'
import type { UpdateProfileRequest, ChangePasswordRequest } from '@store/slices/authSlice'

interface ProfileFormData extends UpdateProfileRequest {}
interface PasswordFormData extends ChangePasswordRequest {}

export default function ProfileSettings() {
  const dispatch = useAppDispatch()
  const currentUser = useAppSelector(selectCurrentUser)
  const isLoading = useAppSelector(selectAuthLoading)
  const authError = useAppSelector(selectAuthError)
  
  const [isEditing, setIsEditing] = useState(false)
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false)
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  // Profile form
  const profileForm = useForm<ProfileFormData>({
    defaultValues: {
      name: currentUser?.name || '',
      email: currentUser?.email || '',
    },
  })

  // Password form
  const passwordForm = useForm<PasswordFormData>({
    defaultValues: {
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
    },
  })

  const handleProfileSubmit = async (data: ProfileFormData) => {
    try {
      await dispatch(updateProfile(data)).unwrap()
      toast.success('프로필이 업데이트되었습니다!')
      setIsEditing(false)
    } catch (err: any) {
      toast.error(err || '프로필 업데이트에 실패했습니다.')
    }
  }

  const handlePasswordSubmit = async (data: PasswordFormData) => {
    if (data.newPassword !== data.confirmPassword) {
      toast.error('새 비밀번호가 일치하지 않습니다.')
      return
    }

    try {
      await dispatch(changePassword(data)).unwrap()
      toast.success('비밀번호가 변경되었습니다!')
      setPasswordDialogOpen(false)
      passwordForm.reset()
    } catch (err: any) {
      toast.error(err || '비밀번호 변경에 실패했습니다.')
    }
  }

  const handleCancelEdit = () => {
    profileForm.reset({
      name: currentUser?.name || '',
      email: currentUser?.email || '',
    })
    setIsEditing(false)
  }

  const handleAvatarUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      // Here you would typically upload the file to your server
      // and get back a URL to update the user's avatar
      console.log('Upload avatar:', file)
      toast.info('아바타 업로드 기능은 곧 제공될 예정입니다.')
    }
  }

  return (
    <Box>
      {/* Profile Information Card */}
      <Card sx={{ mb: 3 }}>
        <CardHeader
          title="프로필 정보"
          action={
            !isEditing && (
              <Button
                startIcon={<EditIcon />}
                onClick={() => setIsEditing(true)}
                variant="outlined"
                size="small"
              >
                편집
              </Button>
            )
          }
        />
        <CardContent>
          {authError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {authError}
            </Alert>
          )}

          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
            <Box sx={{ position: 'relative' }}>
              <Avatar
                src={currentUser?.avatar}
                sx={{ width: 80, height: 80, mr: 2 }}
              >
                {currentUser?.name?.charAt(0).toUpperCase()}
              </Avatar>
              <IconButton
                sx={{
                  position: 'absolute',
                  bottom: -5,
                  right: 5,
                  backgroundColor: 'primary.main',
                  color: 'white',
                  width: 30,
                  height: 30,
                  '&:hover': {
                    backgroundColor: 'primary.dark',
                  },
                }}
                component="label"
              >
                <PhotoCamera sx={{ fontSize: 16 }} />
                <input
                  type="file"
                  hidden
                  accept="image/*"
                  onChange={handleAvatarUpload}
                />
              </IconButton>
            </Box>
            <Box>
              <Typography variant="h6">{currentUser?.name}</Typography>
              <Typography variant="body2" color="text.secondary">
                {currentUser?.email}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                역할: {currentUser?.role}
              </Typography>
            </Box>
          </Box>

          <form onSubmit={profileForm.handleSubmit(handleProfileSubmit)}>
            <Controller
              name="name"
              control={profileForm.control}
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
                  fullWidth
                  label="이름"
                  margin="normal"
                  disabled={!isEditing}
                  error={!!profileForm.formState.errors.name}
                  helperText={profileForm.formState.errors.name?.message}
                />
              )}
            />

            <Controller
              name="email"
              control={profileForm.control}
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
                  fullWidth
                  label="이메일"
                  margin="normal"
                  disabled={!isEditing}
                  error={!!profileForm.formState.errors.email}
                  helperText={profileForm.formState.errors.email?.message}
                />
              )}
            />

            {isEditing && (
              <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                <Button
                  type="submit"
                  variant="contained"
                  startIcon={<SaveIcon />}
                  disabled={isLoading}
                >
                  {isLoading ? <CircularProgress size={20} /> : '저장'}
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<CancelIcon />}
                  onClick={handleCancelEdit}
                >
                  취소
                </Button>
              </Box>
            )}
          </form>
        </CardContent>
      </Card>

      {/* Security Settings Card */}
      <Card>
        <CardHeader title="보안 설정" />
        <CardContent>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              비밀번호
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              계정 보안을 위해 정기적으로 비밀번호를 변경해주세요.
            </Typography>
            <Button
              variant="outlined"
              onClick={() => setPasswordDialogOpen(true)}
            >
              비밀번호 변경
            </Button>
          </Box>

          <Divider sx={{ my: 2 }} />

          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              계정 정보
            </Typography>
            <Typography variant="body2" color="text.secondary">
              생성일: {currentUser?.createdAt ? new Date(currentUser.createdAt).toLocaleString('ko-KR') : '정보 없음'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              마지막 로그인: {currentUser?.lastLogin ? new Date(currentUser.lastLogin).toLocaleString('ko-KR') : '정보 없음'}
            </Typography>
          </Box>
        </CardContent>
      </Card>

      {/* Password Change Dialog */}
      <Dialog
        open={passwordDialogOpen}
        onClose={() => setPasswordDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>비밀번호 변경</DialogTitle>
        <form onSubmit={passwordForm.handleSubmit(handlePasswordSubmit)}>
          <DialogContent>
            <Controller
              name="currentPassword"
              control={passwordForm.control}
              rules={{ required: '현재 비밀번호를 입력해주세요' }}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label="현재 비밀번호"
                  type={showCurrentPassword ? 'text' : 'password'}
                  margin="normal"
                  error={!!passwordForm.formState.errors.currentPassword}
                  helperText={passwordForm.formState.errors.currentPassword?.message}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                          edge="end"
                        >
                          {showCurrentPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
              )}
            />

            <Controller
              name="newPassword"
              control={passwordForm.control}
              rules={{
                required: '새 비밀번호를 입력해주세요',
                minLength: {
                  value: 8,
                  message: '비밀번호는 8자 이상이어야 합니다',
                },
              }}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label="새 비밀번호"
                  type={showNewPassword ? 'text' : 'password'}
                  margin="normal"
                  error={!!passwordForm.formState.errors.newPassword}
                  helperText={passwordForm.formState.errors.newPassword?.message}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => setShowNewPassword(!showNewPassword)}
                          edge="end"
                        >
                          {showNewPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
              )}
            />

            <Controller
              name="confirmPassword"
              control={passwordForm.control}
              rules={{
                required: '비밀번호 확인을 입력해주세요',
                validate: (value) =>
                  value === passwordForm.watch('newPassword') || '비밀번호가 일치하지 않습니다',
              }}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label="비밀번호 확인"
                  type={showConfirmPassword ? 'text' : 'password'}
                  margin="normal"
                  error={!!passwordForm.formState.errors.confirmPassword}
                  helperText={passwordForm.formState.errors.confirmPassword?.message}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
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
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setPasswordDialogOpen(false)}>
              취소
            </Button>
            <Button type="submit" variant="contained" disabled={isLoading}>
              {isLoading ? <CircularProgress size={20} /> : '변경'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  )
}