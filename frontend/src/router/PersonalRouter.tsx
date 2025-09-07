import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import PersonalDashboard from '@pages/PersonalDashboard';
import PersonalSettings from '@pages/PersonalSettings';
import Products from '@pages/Products';
import Collection from '@pages/Collection';
import Orders from '@pages/Orders';
import AISourcing from '@pages/AISourcing';

// 개인 사용자용 라우터
const PersonalRouter = () => {
  return (
    <Routes>
      {/* 기본 경로 - 대시보드로 리다이렉트 */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      
      {/* 대시보드 */}
      <Route path="/dashboard" element={<PersonalDashboard />} />
      
      {/* 설정 */}
      <Route path="/settings" element={<PersonalSettings />} />
      
      {/* 상품 관리 */}
      <Route path="/products" element={<Products />} />
      
      {/* 상품 수집 */}
      <Route path="/collection" element={<Collection />} />
      
      {/* 주문 관리 */}
      <Route path="/orders" element={<Orders />} />
      
      {/* AI 소싱 */}
      <Route path="/ai-sourcing" element={<AISourcing />} />
      
      {/* 기타 경로 - 대시보드로 리다이렉트 */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};

export default PersonalRouter;