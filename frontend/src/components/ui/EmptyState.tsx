/**
 * 빈 상태 UI 컴포넌트
 * 데이터가 없을 때 사용자에게 명확한 가이드 제공
 */

import React from 'react'
import {
  Box,
  Typography,
  Button,
  Stack,
  Card,
  CardContent,
  useTheme,
  alpha,
} from '@mui/material'
import { motion } from 'framer-motion'

export interface EmptyStateProps {
  /** 아이콘 (Material-UI 아이콘 컴포넌트) */
  icon: React.ReactNode
  /** 주 제목 */
  title: string
  /** 부제목/설명 */
  description: string
  /** 주요 액션 버튼 */
  action?: React.ReactNode
  /** 보조 액션 버튼들 */
  secondaryActions?: React.ReactNode[]
  /** 이미지 URL (선택사항) */
  image?: string
  /** 크기 변형 */
  variant?: 'default' | 'compact' | 'detailed'
  /** 컨테이너 최대 너비 */
  maxWidth?: number | string
}

const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  secondaryActions = [],
  image,
  variant = 'default',
  maxWidth = 480,
}) => {
  const theme = useTheme()

  const getSpacing = () => {
    switch (variant) {
      case 'compact':
        return { py: 4, iconSize: 48, titleVariant: 'h6' as const }
      case 'detailed':
        return { py: 10, iconSize: 80, titleVariant: 'h4' as const }
      default:
        return { py: 8, iconSize: 64, titleVariant: 'h5' as const }
    }
  }

  const spacing = getSpacing()

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
    >
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        textAlign="center"
        sx={{
          ...spacing,
          px: 4,
          maxWidth,
          mx: 'auto',
        }}
      >
        {/* 이미지 또는 아이콘 */}
        {image ? (
          <Box
            component="img"
            src={image}
            alt={title}
            sx={{
              width: spacing.iconSize * 1.5,
              height: spacing.iconSize * 1.5,
              mb: 3,
              opacity: 0.8,
            }}
          />
        ) : (
          <Box
            sx={{
              mb: 3,
              p: 2,
              borderRadius: '50%',
              backgroundColor: alpha(theme.palette.primary.main, 0.1),
              color: alpha(theme.palette.primary.main, 0.6),
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {React.cloneElement(icon as React.ReactElement, {
              sx: { fontSize: spacing.iconSize },
            })}
          </Box>
        )}

        {/* 제목 */}
        <Typography 
          variant={spacing.titleVariant} 
          fontWeight={600}
          gutterBottom
          sx={{ 
            mb: 2,
            color: theme.palette.text.primary 
          }}
        >
          {title}
        </Typography>

        {/* 설명 */}
        <Typography
          variant="body1"
          color="text.secondary"
          sx={{
            mb: 4,
            lineHeight: 1.6,
            maxWidth: '90%',
          }}
        >
          {description}
        </Typography>

        {/* 액션 버튼들 */}
        <Stack spacing={2} direction="column" alignItems="center">
          {/* 주요 액션 */}
          {action && (
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              {action}
            </motion.div>
          )}

          {/* 보조 액션들 */}
          {secondaryActions.length > 0 && (
            <Stack spacing={1} direction="row" flexWrap="wrap" justifyContent="center">
              {secondaryActions.map((actionItem, index) => (
                <motion.div
                  key={index}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  {actionItem}
                </motion.div>
              ))}
            </Stack>
          )}
        </Stack>
      </Box>
    </motion.div>
  )
}

export default EmptyState

// 사전 정의된 빈 상태 템플릿들
export const EmptyStateTemplates = {
  products: {
    icon: <Box />, // 실제 사용 시 Inventory 아이콘 전달
    title: '등록된 상품이 없습니다',
    description: '첫 번째 상품을 등록하여 드롭시핑을 시작해보세요. 도매처에서 상품을 가져오거나 직접 등록할 수 있습니다.',
  },
  orders: {
    icon: <Box />, // 실제 사용 시 ShoppingCart 아이콘 전달
    title: '주문이 없습니다',
    description: '아직 주문이 접수되지 않았습니다. 상품을 플랫폼에 등록하고 마케팅을 시작해보세요.',
  },
  platforms: {
    icon: <Box />, // 실제 사용 시 Store 아이콘 전달
    title: '연결된 플랫폼이 없습니다',
    description: '판매할 플랫폼 계정을 연결해주세요. 쿠팡, 네이버, 11번가 등 다양한 플랫폼을 지원합니다.',
  },
  search: {
    icon: <Box />, // 실제 사용 시 Search 아이콘 전달
    title: '검색 결과가 없습니다',
    description: '다른 검색어를 시도하거나 필터를 조정해보세요.',
  },
  error: {
    icon: <Box />, // 실제 사용 시 ErrorOutline 아이콘 전달
    title: '데이터를 불러올 수 없습니다',
    description: '네트워크 연결을 확인하거나 잠시 후 다시 시도해주세요.',
  },
}

// 특화된 빈 상태 컴포넌트들
export const ProductsEmptyState: React.FC<{ onAddProduct: () => void; onImport: () => void }> = ({
  onAddProduct,
  onImport,
}) => (
  <EmptyState
    {...EmptyStateTemplates.products}
    action={
      <Button 
        variant="contained" 
        size="large" 
        onClick={onAddProduct}
        sx={{ minWidth: 160 }}
      >
        첫 상품 등록하기
      </Button>
    }
    secondaryActions={[
      <Button 
        variant="outlined" 
        onClick={onImport}
        key="import"
      >
        상품 가져오기
      </Button>,
      <Button 
        variant="text" 
        href="/help/getting-started"
        key="help"
      >
        시작 가이드 보기
      </Button>,
    ]}
  />
)

export const OrdersEmptyState: React.FC<{ onViewProducts: () => void }> = ({ onViewProducts }) => (
  <EmptyState
    {...EmptyStateTemplates.orders}
    action={
      <Button 
        variant="contained" 
        size="large" 
        onClick={onViewProducts}
        sx={{ minWidth: 160 }}
      >
        상품 등록하러 가기
      </Button>
    }
    secondaryActions={[
      <Button 
        variant="text" 
        href="/help/marketing"
        key="marketing"
      >
        마케팅 가이드 보기
      </Button>,
    ]}
  />
)

export const PlatformsEmptyState: React.FC<{ onAddPlatform: () => void }> = ({ onAddPlatform }) => (
  <EmptyState
    {...EmptyStateTemplates.platforms}
    action={
      <Button 
        variant="contained" 
        size="large" 
        onClick={onAddPlatform}
        sx={{ minWidth: 160 }}
      >
        플랫폼 연결하기
      </Button>
    }
    secondaryActions={[
      <Button 
        variant="text" 
        href="/help/platforms"
        key="help"
      >
        연결 가이드 보기
      </Button>,
    ]}
  />
)

// 카드 스타일 빈 상태 (더 세련된 버전)
export const EmptyStateCard: React.FC<EmptyStateProps> = (props) => (
  <Card 
    sx={{ 
      mx: 'auto',
      my: 4,
      maxWidth: props.maxWidth || 480,
      border: '1px dashed',
      borderColor: 'divider',
      backgroundColor: 'grey.50',
    }}
  >
    <CardContent sx={{ p: 0 }}>
      <EmptyState {...props} />
    </CardContent>
  </Card>
)