import axios from 'axios'

const API_BASE_URL = '/api'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// API 함수들
export const api = {
  // 상품 관련
  getProducts: (params?: { supplier?: string; limit?: number; offset?: number }) =>
    apiClient.get('/products', { params }),
  
  getProduct: (productCode: string) =>
    apiClient.get(`/products/${productCode}`),
  
  // 공급사 관련
  getSuppliers: () => apiClient.get('/suppliers'),
  
  // 수집 관련
  getCollectionLogs: (params?: { supplier?: string; limit?: number }) =>
    apiClient.get('/collection-logs', { params }),
  
  startCollection: (supplier: string, testMode: boolean = true) =>
    apiClient.post(`/collection/full/${supplier}`, null, {
      params: { test_mode: testMode }
    }),
  
  // 증분 수집
  startIncrementalSync: (supplier: string, testMode: boolean = true) =>
    apiClient.post(`/collection/incremental/${supplier}`, null, {
      params: { test_mode: testMode }
    }),
  
  getSyncStatus: () =>
    apiClient.get('/collection/sync/status'),
  
  getCollectionStatus: (supplier: string) =>
    apiClient.get(`/collection/status/${supplier}`),
  
  // 엑셀 업로드
  uploadExcel: (supplier: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post(`/excel/upload/${supplier}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
  
  getExcelTemplate: (supplier: string) =>
    apiClient.get(`/excel/template/${supplier}`, {
      responseType: 'blob',
    }),
  
  downloadProducts: (supplier?: string) =>
    apiClient.get('/excel/download', {
      params: { supplier },
      responseType: 'blob',
    }),
  
  getUploadHistory: () =>
    apiClient.get('/excel/uploads'),
  
  // 설정 관련
  getSupplierSettings: (supplier: string) =>
    apiClient.get(`/settings/suppliers/${supplier}`),
  
  updateZentradeSettings: (settings: any) =>
    apiClient.put('/settings/suppliers/zentrade', settings),
  
  updateOwnerClanSettings: (settings: any) =>
    apiClient.put('/settings/suppliers/ownerclan', settings),
  
  updateDomeggookSettings: (settings: any) =>
    apiClient.put('/settings/suppliers/domeggook', settings),
  
  // 마켓플레이스 설정
  updateMarketplaceSettings: (marketplace: string, settings: any) =>
    apiClient.put(`/settings/marketplace/${marketplace}`, settings),
  
  testSupplierConnection: (supplier: string) =>
    apiClient.post(`/settings/test-connection/${supplier}`),
}