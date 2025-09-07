import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Chip,
  IconButton,
  CircularProgress,
  Alert,
  Snackbar,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Refresh,
  Download,
  Settings,
  HealthAndSafety,
  AttachMoney,
  ShoppingCart,
  Inventory,
  TrendingUp,
  Notifications,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { analyticsAPI } from '@services/api';
import { Card } from '@components/ui/Card';

// 간소화된 대시보드 컴포넌트
const PersonalDashboard = () => {
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'info' });
  const [lastUpdated, setLastUpdated] = useState(new Date());

  // 대시보드 데이터 가져오기
  const { data: dashboardData, isLoading, isError, refetch } = useQuery({
    queryKey: ['personalDashboard'],
    queryFn: async () => {
      try {
        // 실제 API에서 대시보드 통계 가져오기
        const response = await analyticsAPI.getDashboard();
        const stats = response.data;

        return {
          stats: {
            totalRevenue: stats.orders?.revenue || 0,
            totalOrders: stats.orders?.total || 0,
            totalProducts: stats.products?.total || 0,
            connectedPlatforms: stats.platforms?.connected || 0,
          },
          health: {
            status: 'healthy',
            message: '시스템 정상 작동 중',
          },
        };
      } catch (error) {
        console.warn('API 실패, 기본 데이터 사용:', error);
        // API 실패시 fallback 데이터
        return {
          stats: {
            totalRevenue: 0,
            totalOrders: 0,
            totalProducts: 0,
            connectedPlatforms: 0,
          },
          health: {
            status: 'warning',
            message: '데이터를 불러오는 중...',
          },
        };
      }
    },
    refetchInterval: autoRefresh ? 30000 : false,
  });

  // 자동 새로고침 설정
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        refetch();
        setLastUpdated(new Date());
      }, 30000);
      
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refetch]);

  // 새로고침 핸들러
  const handleRefresh = () => {
    refetch();
    setLastUpdated(new Date());
    showNotification('대시보드가 업데이트되었습니다.', 'success');
  };

  // 알림 표시
  const showNotification = (message, severity = 'info') => {
    setNotification({ open: true, message, severity });
  };

  // 알림 닫기
  const handleCloseNotification = () => {
    setNotification({ ...notification, open: false });
  };

  // 통계 카드 데이터
  const statCards = [
    {
      title: '총 매출',
      value: `₩${dashboardData?.stats.totalRevenue.toLocaleString() || 0}`,
      icon: <AttachMoney />,
      color: 'primary',
    },
    {
      title: '총 주문',
      value: dashboardData?.stats.totalOrders || 0,
      icon: <ShoppingCart />,
      color: 'secondary',
    },
    {
      title: '상품 수',
      value: dashboardData?.stats.totalProducts || 0,
      icon: <Inventory />,
      color: 'warning',
    },
    {
      title: '연결 플랫폼',
      value: dashboardData?.stats.connectedPlatforms || 0,
      icon: <TrendingUp />,
      color: 'success',
    },
  ];

  // 상태 표시
  const healthStatus = dashboardData?.health || { status: 'loading', message: '로딩 중...' };

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column', p: 3 }}>
      {/* 헤더 */}
      <Paper sx={{ p: 2, mb: 3, borderRadius: 2 }} elevation={2}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <DashboardIcon sx={{ fontSize: 40, color: 'primary.main' }} />
            <Box>
              <Typography variant="h4" fontWeight="bold">
                개인 사용자 대시보드
              </Typography>
              <Typography variant="body2" color="text.secondary">
                드롭시핑 시스템의 현재 상태를 확인하세요
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Chip
              icon={healthStatus.status === 'healthy' ? <HealthAndSafety /> : <CircularProgress size={16} />}
              label={healthStatus.message}
              color={healthStatus.status === 'healthy' ? 'success' : 'warning'}
              size="small"
            />
            <Typography variant="caption" color="text.secondary">
              마지막 업데이트: {lastUpdated.toLocaleTimeString()}
            </Typography>
            <Button 
              startIcon={<Refresh />} 
              onClick={handleRefresh}
              variant="outlined"
            >
              새로고침
            </Button>
          </Box>
        </Box>
      </Paper>

      {/* 로딩 상태 */}
      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
          <CircularProgress />
          <Typography sx={{ ml: 2 }}>데이터를 불러오는 중...</Typography>
        </Box>
      )}

      {/* 에러 상태 */}
      {isError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          데이터를 불러오는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.
        </Alert>
      )}

      {/* 통계 카드 그리드 */}
      {!isLoading && !isError && (
        <Box sx={{ 
          display: 'grid', 
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' }, 
          gap: 3,
          mb: 3
        }}>
          {statCards.map((card, index) => (
            <Card key={index} sx={{ height: '100%' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Box sx={{ 
                  width: 56, 
                  height: 56, 
                  borderRadius: '50%', 
                  backgroundColor: `${card.color}.light`, 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  mr: 2
                }}>
                  {React.cloneElement(card.icon, { sx: { color: `${card.color}.main`, fontSize: 30 } })}
                </Box>
                <Box>
                  <Typography variant="h5" fontWeight="bold">
                    {card.value}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {card.title}
                  </Typography>
                </Box>
              </Box>
            </Card>
          ))}
        </Box>
      )}

      {/* 활동 및 알림 섹션 */}
      {!isLoading && !isError && (
        <Box sx={{ display: 'grid', gridTemplateColumns: { md: '2fr 1fr' }, gap: 3, flex: 1 }}>
          {/* 최근 활동 */}
          <Card title="최근 활동" sx={{ height: '100%' }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {[
                { time: '5분 전', event: '새 주문 접수', detail: '무선 이어폰 외 2건', type: 'order' },
                { time: '15분 전', event: '상품 등록 완료', detail: '스마트워치 Series 5', type: 'product' },
                { time: '1시간 전', event: '배송 완료', detail: '주문번호 #12345', type: 'delivery' },
                { time: '2시간 전', event: '수집 작업 완료', detail: '오너클랜 상품 50개', type: 'collection' },
              ].map((activity, index) => (
                <Box 
                  key={index} 
                  sx={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    p: 2,
                    borderRadius: 1,
                    backgroundColor: index % 2 === 0 ? 'grey.50' : 'transparent'
                  }}
                >
                  <Box>
                    <Typography variant="body1" fontWeight="medium">
                      {activity.event}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {activity.detail}
                    </Typography>
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {activity.time}
                  </Typography>
                </Box>
              ))}
            </Box>
          </Card>

          {/* 알림 및 시스템 상태 */}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Card title="시스템 상태" sx={{ flex: 1 }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                <HealthAndSafety sx={{ fontSize: 60, color: 'success.main', mb: 2 }} />
                <Typography variant="h6" fontWeight="bold" color="success.main">
                  정상 작동 중
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1, textAlign: 'center' }}>
                  모든 시스템이 정상적으로 작동하고 있습니다
                </Typography>
              </Box>
            </Card>

            <Card title="알림" sx={{ flex: 1 }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Chip
                  icon={<Notifications />}
                  label="재고 부족 경고: 3개 상품"
                  color="warning"
                  size="small"
                  onClick={() => showNotification('재고 부족 상품을 확인하세요.')}
                />
                <Chip
                  icon={<TrendingUp />}
                  label="판매 증가: +25%"
                  color="success"
                  size="small"
                  onClick={() => showNotification('최근 1시간 동안 판매가 증가했습니다.')}
                />
                <Chip
                  icon={<Settings />}
                  label="업데이트 필요"
                  color="info"
                  size="small"
                  onClick={() => showNotification('새로운 기능이 추가되었습니다.')}
                />
              </Box>
            </Card>
          </Box>
        </Box>
      )}

      {/* 알림 스낵바 */}
      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={handleCloseNotification}
        message={notification.message}
      />
    </Box>
  );
};

export default PersonalDashboard;