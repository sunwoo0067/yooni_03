// 로그인 기능 제거 - 항상 인증된 상태로 처리
export const useAuth = () => {
  return {
    isAuthenticated: true,
    user: {
      id: 1,
      email: 'admin@yooni.com',
      name: 'Admin User'
    },
    loading: false,
    sessionExpiry: null,
  }
}