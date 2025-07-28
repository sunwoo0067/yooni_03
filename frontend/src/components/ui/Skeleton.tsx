/**
 * 스켈레톤 UI 컴포넌트
 * 로딩 상태에서 사용자에게 예상 컨텐츠 구조를 보여줌
 */

import React from 'react'
import {
  Box,
  Card,
  CardContent,
  Grid,
  Paper,
  Skeleton,
  Stack,
  useTheme,
} from '@mui/material'
import { motion } from 'framer-motion'

// 기본 스켈레톤 래퍼 (애니메이션 효과)
export const SkeletonWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ duration: 0.3 }}
  >
    {children}
  </motion.div>
)

// 상품 카드 스켈레톤
export const ProductCardSkeleton: React.FC = () => {
  const theme = useTheme()
  
  return (
    <SkeletonWrapper>
      <Card sx={{ height: '100%' }}>
        <CardContent>
          <Stack spacing={2}>
            {/* 상품 이미지 */}
            <Skeleton
              variant="rectangular"
              width="100%"
              height={120}
              sx={{ borderRadius: 1 }}
            />
            
            {/* 상품명 */}
            <Skeleton variant="text" width="80%" height={24} />
            <Skeleton variant="text" width="60%" height={20} />
            
            {/* 가격 정보 */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Skeleton variant="text" width="40%" height={32} />
              <Skeleton variant="circular" width={24} height={24} />
            </Box>
            
            {/* 상태 정보 */}
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Skeleton variant="rounded" width={60} height={24} />
              <Skeleton variant="rounded" width={80} height={24} />
            </Box>
          </Stack>
        </CardContent>
      </Card>
    </SkeletonWrapper>
  )
}

// 주문 카드 스켈레톤
export const OrderCardSkeleton: React.FC = () => (
  <SkeletonWrapper>
    <Card>
      <CardContent>
        <Stack spacing={2}>
          {/* 주문 헤더 */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Skeleton variant="text" width="30%" height={24} />
            <Skeleton variant="rounded" width={60} height={24} />
          </Box>
          
          {/* 고객 정보 */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Skeleton variant="circular" width={40} height={40} />
            <Box sx={{ flex: 1 }}>
              <Skeleton variant="text" width="60%" height={20} />
              <Skeleton variant="text" width="40%" height={16} />
            </Box>
          </Box>
          
          {/* 주문 금액 */}
          <Box sx={{ textAlign: 'right' }}>
            <Skeleton variant="text" width="30%" height={28} sx={{ ml: 'auto' }} />
          </Box>
        </Stack>
      </CardContent>
    </Card>
  </SkeletonWrapper>
)

// 데이터 그리드 스켈레톤
export const DataGridSkeleton: React.FC<{ rows?: number; columns?: number }> = ({ 
  rows = 10, 
  columns = 6 
}) => (
  <SkeletonWrapper>
    <Paper sx={{ p: 2 }}>
      {/* 헤더 */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        {Array.from({ length: columns }).map((_, index) => (
          <Skeleton
            key={`header-${index}`}
            variant="text"
            width={index === 0 ? '30%' : '15%'}
            height={40}
            sx={{ flex: index === 0 ? 1 : 'none' }}
          />
        ))}
      </Box>
      
      {/* 데이터 행들 */}
      <Stack spacing={1}>
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <Box key={`row-${rowIndex}`} sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            {Array.from({ length: columns }).map((_, colIndex) => (
              <Skeleton
                key={`cell-${rowIndex}-${colIndex}`}
                variant="text"
                width={colIndex === 0 ? '30%' : '15%'}
                height={32}
                sx={{ flex: colIndex === 0 ? 1 : 'none' }}
              />
            ))}
          </Box>
        ))}
      </Stack>
    </Paper>
  </SkeletonWrapper>
)

// 대시보드 통계 카드 스켈레톤
export const StatCardSkeleton: React.FC = () => (
  <SkeletonWrapper>
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ flex: 1 }}>
            <Skeleton variant="text" width="60%" height={16} />
            <Skeleton variant="text" width="40%" height={36} />
          </Box>
          <Skeleton variant="circular" width={40} height={40} />
        </Box>
      </CardContent>
    </Card>
  </SkeletonWrapper>
)

// 차트 스켈레톤
export const ChartSkeleton: React.FC<{ height?: number }> = ({ height = 300 }) => (
  <SkeletonWrapper>
    <Card>
      <CardContent>
        <Stack spacing={2}>
          {/* 차트 제목 */}
          <Skeleton variant="text" width="30%" height={24} />
          
          {/* 차트 영역 */}
          <Skeleton
            variant="rectangular"
            width="100%"
            height={height}
            sx={{ borderRadius: 1 }}
          />
          
          {/* 범례 */}
          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 3 }}>
            {Array.from({ length: 4 }).map((_, index) => (
              <Box key={index} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Skeleton variant="circular" width={12} height={12} />
                <Skeleton variant="text" width={60} height={16} />
              </Box>
            ))}
          </Box>
        </Stack>
      </CardContent>
    </Card>
  </SkeletonWrapper>
)

// 플랫폼 계정 카드 스켈레톤
export const PlatformCardSkeleton: React.FC = () => (
  <SkeletonWrapper>
    <Card>
      <CardContent>
        <Stack spacing={2}>
          {/* 플랫폼 헤더 */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Skeleton variant="circular" width={48} height={48} />
            <Box sx={{ flex: 1 }}>
              <Skeleton variant="text" width="70%" height={20} />
              <Skeleton variant="text" width="50%" height={16} />
            </Box>
            <Skeleton variant="circular" width={24} height={24} />
          </Box>
          
          {/* 상태 정보 */}
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Skeleton variant="rounded" width={60} height={24} />
            <Skeleton variant="rounded" width={80} height={24} />
          </Box>
          
          {/* 통계 정보 */}
          <Grid container spacing={2}>
            {Array.from({ length: 4 }).map((_, index) => (
              <Grid item xs={6} key={index}>
                <Skeleton variant="text" width="80%" height={14} />
                <Skeleton variant="text" width="60%" height={20} />
              </Grid>
            ))}
          </Grid>
          
          {/* 하단 액션 */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Skeleton variant="text" width="40%" height={16} />
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Skeleton variant="circular" width={32} height={32} />
              <Skeleton variant="circular" width={32} height={32} />
            </Box>
          </Box>
        </Stack>
      </CardContent>
    </Card>
  </SkeletonWrapper>
)

// 리스트 아이템 스켈레톤
export const ListItemSkeleton: React.FC = () => (
  <SkeletonWrapper>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2 }}>
      <Skeleton variant="circular" width={40} height={40} />
      <Box sx={{ flex: 1 }}>
        <Skeleton variant="text" width="70%" height={20} />
        <Skeleton variant="text" width="50%" height={16} />
      </Box>
      <Skeleton variant="rounded" width={60} height={24} />
    </Box>
  </SkeletonWrapper>
)

// 페이지 전체 스켈레톤 (헤더 + 컨텐츠)
export const PageSkeleton: React.FC<{ title?: boolean; stats?: boolean; content?: boolean }> = ({
  title = true,
  stats = true,
  content = true
}) => (
  <SkeletonWrapper>
    <Box sx={{ p: 3 }}>
      {/* 페이지 제목 */}
      {title && (
        <Box sx={{ mb: 3 }}>
          <Skeleton variant="text" width="30%" height={40} />
          <Skeleton variant="text" width="50%" height={20} />
        </Box>
      )}
      
      {/* 통계 카드들 */}
      {stats && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          {Array.from({ length: 4 }).map((_, index) => (
            <Grid item xs={12} sm={6} md={3} key={index}>
              <StatCardSkeleton />
            </Grid>
          ))}
        </Grid>
      )}
      
      {/* 메인 컨텐츠 */}
      {content && (
        <DataGridSkeleton />
      )}
    </Box>
  </SkeletonWrapper>
)

// 폼 스켈레톤
export const FormSkeleton: React.FC<{ fields?: number }> = ({ fields = 6 }) => (
  <SkeletonWrapper>
    <Card>
      <CardContent>
        <Stack spacing={3}>
          {/* 폼 제목 */}
          <Skeleton variant="text" width="40%" height={28} />
          
          {/* 폼 필드들 */}
          <Grid container spacing={2}>
            {Array.from({ length: fields }).map((_, index) => (
              <Grid item xs={12} sm={6} key={index}>
                <Skeleton variant="text" width="30%" height={16} />
                <Skeleton variant="rectangular" width="100%" height={56} sx={{ mt: 1, borderRadius: 1 }} />
              </Grid>
            ))}
          </Grid>
          
          {/* 폼 액션 버튼들 */}
          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
            <Skeleton variant="rounded" width={80} height={36} />
            <Skeleton variant="rounded" width={100} height={36} />
          </Box>
        </Stack>
      </CardContent>
    </Card>
  </SkeletonWrapper>
)

export default Skeleton