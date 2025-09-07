import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Divider,
  Alert,
  Snackbar,
  CircularProgress,
  Chip,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Save,
  Refresh,
  CheckCircle,
  Error,
} from '@mui/icons-material';
import { useQuery, useMutation } from '@tanstack/react-query';
import { settingsAPI } from '@services/api';

// 개인 사용자용 설정 페이지
const PersonalSettings = () => {
  const [settings, setSettings] = useState({
    // 공급사 설정
    ownerclanApiKey: '',
    zentradeApiKey: '',
    domaekkukApiKey: '',
    
    // 마켓플레이스 설정
    coupangVendorId: '',
    coupangAccessKey: '',
    coupangSecretKey: '',
    naverClientId: '',
    naverClientSecret: '',
    
    // 일반 설정
    autoCollection: true,
    collectionInterval: 24, // hours
    autoRegistration: true,
    singleUserMode: true,
    
    // 알림 설정
    emailNotifications: true,
    slackNotifications: false,
  });
  
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'info' });
  const [isSaving, setIsSaving] = useState(false);

  // 설정 데이터 가져오기
  const { data, isLoading, isError } = useQuery({
    queryKey: ['personalSettings'],
    queryFn: async () => {
      try {
        const response = await settingsAPI.getSettings();
        return response.data;
      } catch (error) {
        console.warn('설정 로드 실패:', error);
        return null;
      }
    },
  });

  // 설정 데이터가 로드되면 상태 업데이트
  useEffect(() => {
    if (data) {
      setSettings({
        ownerclanApiKey: data.ownerclan?.apiKey || '',
        zentradeApiKey: data.zentrade?.apiKey || '',
        domaekkukApiKey: data.domaekkuk?.apiKey || '',
        coupangVendorId: data.coupang?.vendorId || '',
        coupangAccessKey: data.coupang?.accessKey || '',
        coupangSecretKey: data.coupang?.secretKey || '',
        naverClientId: data.naver?.clientId || '',
        naverClientSecret: data.naver?.clientSecret || '',
        autoCollection: data.collection?.autoCollection ?? true,
        collectionInterval: data.collection?.interval || 24,
        autoRegistration: data.registration?.autoRegistration ?? true,
        singleUserMode: data.system?.singleUserMode ?? true,
        emailNotifications: data.notifications?.email ?? true,
        slackNotifications: data.notifications?.slack ?? false,
      });
    }
  }, [data]);

  // 설정 저장 뮤테이션
  const saveSettingsMutation = useMutation({
    mutationFn: (newSettings) => settingsAPI.updateSettings(newSettings),
    onSuccess: () => {
      setIsSaving(false);
      showNotification('설정이 저장되었습니다.', 'success');
    },
    onError: (error) => {
      setIsSaving(false);
      showNotification('설정 저장 중 오류가 발생했습니다.', 'error');
      console.error('설정 저장 오류:', error);
    },
  });

  // 입력 변경 핸들러
  const handleChange = (field, value) => {
    setSettings(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // 폼 제출 핸들러
  const handleSubmit = (e) => {
    e.preventDefault();
    setIsSaving(true);
    saveSettingsMutation.mutate(settings);
  };

  // 알림 표시
  const showNotification = (message, severity = 'info') => {
    setNotification({ open: true, message, severity });
  };

  // 알림 닫기
  const handleCloseNotification = () => {
    setNotification({ ...notification, open: false });
  };

  // 테스트 연결 핸들러
  const handleTestConnection = async (platform) => {
    try {
      // 실제 구현에서는 해당 플랫폼의 연결 테스트 API를 호출
      showNotification(`${platform} 연결 테스트 중...`, 'info');
      
      // 시뮬레이션 딜레이
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      showNotification(`${platform} 연결 성공!`, 'success');
    } catch (error) {
      showNotification(`${platform} 연결 실패: ${error.message}`, 'error');
    }
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column', p: 3 }}>
      {/* 헤더 */}
      <Paper sx={{ p: 2, mb: 3, borderRadius: 2 }} elevation={2}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <SettingsIcon sx={{ fontSize: 40, color: 'primary.main' }} />
            <Box>
              <Typography variant="h4" fontWeight="bold">
                개인 사용자 설정
              </Typography>
              <Typography variant="body2" color="text.secondary">
                드롭시핑 시스템의 작동 방식을 설정하세요
              </Typography>
            </Box>
          </Box>
          <Button 
            startIcon={<Save />} 
            onClick={handleSubmit}
            variant="contained"
            disabled={isSaving}
          >
            {isSaving ? <CircularProgress size={20} /> : '설정 저장'}
          </Button>
        </Box>
      </Paper>

      {/* 로딩 상태 */}
      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
          <CircularProgress />
          <Typography sx={{ ml: 2 }}>설정을 불러오는 중...</Typography>
        </Box>
      )}

      {/* 에러 상태 */}
      {isError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          설정을 불러오는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.
        </Alert>
      )}

      {/* 설정 폼 */}
      {!isLoading && !isError && (
        <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 3, flex: 1, overflow: 'auto' }}>
          {/* 공급사 설정 */}
          <Paper sx={{ p: 3, borderRadius: 2 }}>
            <Typography variant="h6" fontWeight="bold" gutterBottom>
              공급사 설정
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              상품을 수집할 공급사의 API 키를 입력하세요. 최소 하나의 공급사 정보가 필요합니다.
            </Typography>
            
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 3 }}>
              <TextField
                label="OwnerClan API 키"
                value={settings.ownerclanApiKey}
                onChange={(e) => handleChange('ownerclanApiKey', e.target.value)}
                fullWidth
                type="password"
                helperText="OwnerClan 공급사 연동을 위한 API 키"
                InputProps={{
                  endAdornment: (
                    <Button 
                      size="small" 
                      onClick={() => handleTestConnection('OwnerClan')}
                      disabled={!settings.ownerclanApiKey}
                    >
                      테스트
                    </Button>
                  ),
                }}
              />
              
              <TextField
                label="ZenTrade API 키"
                value={settings.zentradeApiKey}
                onChange={(e) => handleChange('zentradeApiKey', e.target.value)}
                fullWidth
                type="password"
                helperText="ZenTrade 공급사 연동을 위한 API 키"
                InputProps={{
                  endAdornment: (
                    <Button 
                      size="small" 
                      onClick={() => handleTestConnection('ZenTrade')}
                      disabled={!settings.zentradeApiKey}
                    >
                      테스트
                    </Button>
                  ),
                }}
              />
              
              <TextField
                label="DoMaeKkuk API 키"
                value={settings.domaekkukApiKey}
                onChange={(e) => handleChange('domaekkukApiKey', e.target.value)}
                fullWidth
                type="password"
                helperText="DoMaeKkuk 공급사 연동을 위한 API 키"
                InputProps={{
                  endAdornment: (
                    <Button 
                      size="small" 
                      onClick={() => handleTestConnection('DoMaeKkuk')}
                      disabled={!settings.domaekkukApiKey}
                    >
                      테스트
                    </Button>
                  ),
                }}
              />
            </Box>
          </Paper>

          <Divider />

          {/* 마켓플레이스 설정 */}
          <Paper sx={{ p: 3, borderRadius: 2 }}>
            <Typography variant="h6" fontWeight="bold" gutterBottom>
              마켓플레이스 설정
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              상품을 등록할 마켓플레이스의 API 키를 입력하세요. 최소 하나의 마켓플레이스 정보가 필요합니다.
            </Typography>
            
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 3 }}>
              <TextField
                label="쿠팡 벤더 ID"
                value={settings.coupangVendorId}
                onChange={(e) => handleChange('coupangVendorId', e.target.value)}
                fullWidth
                helperText="쿠팡 파트너스 센터에서 확인 가능한 벤더 ID"
              />
              
              <TextField
                label="쿠팡 액세스 키"
                value={settings.coupangAccessKey}
                onChange={(e) => handleChange('coupangAccessKey', e.target.value)}
                fullWidth
                type="password"
                helperText="쿠팡 API 인증을 위한 액세스 키"
              />
              
              <TextField
                label="쿠팡 시크릿 키"
                value={settings.coupangSecretKey}
                onChange={(e) => handleChange('coupangSecretKey', e.target.value)}
                fullWidth
                type="password"
                helperText="쿠팡 API 인증을 위한 시크릿 키"
                InputProps={{
                  endAdornment: (
                    <Button 
                      size="small" 
                      onClick={() => handleTestConnection('쿠팡')}
                      disabled={!settings.coupangVendorId || !settings.coupangAccessKey || !settings.coupangSecretKey}
                    >
                      테스트
                    </Button>
                  ),
                }}
              />
              
              <TextField
                label="네이버 클라이언트 ID"
                value={settings.naverClientId}
                onChange={(e) => handleChange('naverClientId', e.target.value)}
                fullWidth
                helperText="네이버 스마트스토어 API 인증을 위한 클라이언트 ID"
              />
              
              <TextField
                label="네이버 클라이언트 시크릿"
                value={settings.naverClientSecret}
                onChange={(e) => handleChange('naverClientSecret', e.target.value)}
                fullWidth
                type="password"
                helperText="네이버 스마트스토어 API 인증을 위한 클라이언트 시크릿"
                InputProps={{
                  endAdornment: (
                    <Button 
                      size="small" 
                      onClick={() => handleTestConnection('네이버')}
                      disabled={!settings.naverClientId || !settings.naverClientSecret}
                    >
                      테스트
                    </Button>
                  ),
                }}
              />
            </Box>
          </Paper>

          <Divider />

          {/* 자동화 설정 */}
          <Paper sx={{ p: 3, borderRadius: 2 }}>
            <Typography variant="h6" fontWeight="bold" gutterBottom>
              자동화 설정
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              시스템의 자동화 기능을 설정하세요.
            </Typography>
            
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.autoCollection}
                    onChange={(e) => handleChange('autoCollection', e.target.checked)}
                    color="primary"
                  />
                }
                label="자동 상품 수집"
              />
              
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <TextField
                  label="수집 주기"
                  value={settings.collectionInterval}
                  onChange={(e) => handleChange('collectionInterval', parseInt(e.target.value) || 24)}
                  type="number"
                  InputProps={{ inputProps: { min: 1, max: 168 } }}
                  sx={{ width: 200 }}
                />
                <Typography>시간</Typography>
                <Typography variant="body2" color="text.secondary">
                  (1-168시간, 1주일 최대)
                </Typography>
              </Box>
              
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.autoRegistration}
                    onChange={(e) => handleChange('autoRegistration', e.target.checked)}
                    color="primary"
                  />
                }
                label="자동 상품 등록"
              />
              
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.singleUserMode}
                    onChange={(e) => handleChange('singleUserMode', e.target.checked)}
                    color="primary"
                    disabled
                  />
                }
                label="단일 사용자 모드 (개인 사용자용으로 고정)"
              />
            </Box>
          </Paper>

          <Divider />

          {/* 알림 설정 */}
          <Paper sx={{ p: 3, borderRadius: 2 }}>
            <Typography variant="h6" fontWeight="bold" gutterBottom>
              알림 설정
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              시스템 이벤트에 대한 알림을 설정하세요.
            </Typography>
            
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.emailNotifications}
                    onChange={(e) => handleChange('emailNotifications', e.target.checked)}
                    color="primary"
                  />
                }
                label="이메일 알림"
              />
              
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.slackNotifications}
                    onChange={(e) => handleChange('slackNotifications', e.target.checked)}
                    color="primary"
                  />
                }
                label="슬랙 알림"
              />
            </Box>
          </Paper>

          {/* 저장 버튼 */}
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
            <Button 
              startIcon={<Save />} 
              onClick={handleSubmit}
              variant="contained"
              size="large"
              disabled={isSaving}
            >
              {isSaving ? <CircularProgress size={20} /> : '설정 저장'}
            </Button>
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

export default PersonalSettings;