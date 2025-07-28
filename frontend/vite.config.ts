import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    'import.meta.env.VITE_API_BASE_URL': JSON.stringify('http://localhost:8000/api/v1'),
  },
  optimizeDeps: {
    include: ['@emotion/react', '@emotion/styled', '@mui/material'],
    esbuildOptions: {
      target: 'es2020',
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@pages': path.resolve(__dirname, './src/pages'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@services': path.resolve(__dirname, './src/services'),
      '@store': path.resolve(__dirname, './src/store'),
      '@types': path.resolve(__dirname, './src/types'),
      '@assets': path.resolve(__dirname, './src/assets'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // node_modules 라이브러리들을 분리
          if (id.includes('node_modules')) {
            // React 관련
            if (id.includes('react-router') || id.includes('react-dom')) {
              return 'react-vendor';
            }
            // Redux 및 상태 관리
            if (id.includes('@reduxjs') || id.includes('react-redux') || id.includes('@tanstack/react-query')) {
              return 'state-management';
            }
            // MUI 컴포넌트
            if (id.includes('@mui/material') || id.includes('@mui/icons-material')) {
              return 'mui-core';
            }
            if (id.includes('@mui/lab') || id.includes('@mui/x-date-pickers')) {
              return 'mui-lab';
            }
            if (id.includes('@mui/x-data-grid')) {
              return 'mui-data';
            }
            // 차트
            if (id.includes('recharts')) {
              return 'charts';
            }
            // 유틸리티
            if (id.includes('axios') || id.includes('date-fns') || id.includes('react-hook-form')) {
              return 'utils';
            }
            // 애니메이션 및 UI
            if (id.includes('framer-motion') || id.includes('react-hot-toast') || id.includes('react-grid-layout')) {
              return 'ui-libs';
            }
          }
        },
      },
    },
    // 청크 크기 경고 한계 증가
    chunkSizeWarningLimit: 600,
  },
})