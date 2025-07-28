import React from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Box,
  Button,
  Typography,
  Paper,
  Avatar,
} from '@mui/material'
import { MailOutline, ArrowBack } from '@mui/icons-material'
import { motion } from 'framer-motion'

export default function ResetPasswordSent() {
  const navigate = useNavigate()
  const location = useLocation()
  const email = location.state?.email || ''

  return (
    <Box sx={{ width: '100%' }}>
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
            <MailOutline sx={{ fontSize: 40, color: 'success.main' }} />
          </Avatar>

          <Typography
            component="h2"
            variant="h5"
            sx={{ mb: 2, fontWeight: 'bold' }}
          >
            이메일을 확인해주세요
          </Typography>

          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            비밀번호 재설정 링크를 다음 이메일로 발송했습니다:
          </Typography>

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
              {email}
            </Typography>
          </Paper>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
            이메일을 받지 못하셨나요? 스팸 폴더를 확인해보시거나 잠시 후 다시 시도해주세요.
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Button
              fullWidth
              variant="contained"
              onClick={() => navigate('/auth/login')}
              sx={{ py: 1.5 }}
            >
              로그인 페이지로 돌아가기
            </Button>

            <Button
              fullWidth
              variant="outlined"
              startIcon={<ArrowBack />}
              onClick={() => navigate('/auth/forgot-password')}
            >
              다시 요청하기
            </Button>
          </Box>
        </Box>

        <Paper
          elevation={0}
          sx={{
            p: 2,
            bgcolor: 'warning.light',
            borderRadius: 2,
            border: 1,
            borderColor: 'warning.main',
          }}
        >
          <Typography variant="body2" color="warning.dark">
            <strong>참고사항:</strong>
            <br />
            • 비밀번호 재설정 링크는 24시간 동안 유효합니다.
            <br />
            • 보안을 위해 링크는 한 번만 사용할 수 있습니다.
            <br />
            • 이메일을 받지 못하셨다면 고객지원팀에 문의해주세요.
          </Typography>
        </Paper>
      </motion.div>
    </Box>
  )
}