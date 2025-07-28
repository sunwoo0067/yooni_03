import React from 'react'
import { Outlet } from 'react-router-dom'
import { Box, Container, Paper, Typography } from '@mui/material'
import { motion } from 'framer-motion'

export default function AuthLayout() {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Container component="main" maxWidth="xs">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Paper
            elevation={3}
            sx={{
              p: 4,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              borderRadius: 2,
            }}
          >
            <Box sx={{ mb: 3, textAlign: 'center' }}>
              <Typography
                component="h1"
                variant="h4"
                sx={{
                  fontWeight: 'bold',
                  background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  mb: 1,
                }}
              >
                Yooni Dropshipping
              </Typography>
              <Typography variant="body2" color="text.secondary">
                스마트한 드랍쉬핑 통합 관리 시스템
              </Typography>
            </Box>
            <Outlet />
          </Paper>
        </motion.div>
      </Container>
    </Box>
  )
}