import axios from '../api'
import { CollectedProduct, CollectionRequest, CollectionStatus } from '@/types/collector'

export const collectorAPI = {
  // 도매처에서 상품 수집
  collectProducts: async (params: CollectionRequest) => {
    const response = await axios.post('/product-collector/collect', params)
    return response.data
  },

  // 수집된 상품 목록 조회
  getCollectedProducts: async (params?: {
    source?: string
    keyword?: string
    status?: CollectionStatus
    category?: string
    price_min?: number
    price_max?: number
    page?: number
    limit?: number
  }) => {
    const response = await axios.get('/product-collector/collected', { params })
    return response.data
  },

  // 수집된 상품을 실제 판매 상품으로 소싱
  sourceProduct: async (collectedProductId: string, marginRate: number) => {
    const response = await axios.post(`/product-collector/source-product/${collectedProductId}`, {
      margin_rate: marginRate
    })
    return response.data
  },

  // 수집된 상품 거부
  rejectProduct: async (collectedProductId: string) => {
    const response = await axios.delete(`/product-collector/collected/${collectedProductId}`)
    return response.data
  },

  // 사용 가능한 도매처 목록 조회
  getSources: async () => {
    const response = await axios.get('/product-collector/sources')
    return response.data
  }
}

export const wholesalerSyncAPI = {
  // 도매처 전체 동기화
  syncWholesalers: async (params: {
    sources: string[]
    collection_type?: 'all' | 'recent' | 'updated' | 'new'
    max_products_per_source?: number
    categories?: string[]
    price_min?: number
    price_max?: number
  }) => {
    const response = await axios.post('/wholesaler-sync/sync', params)
    return response.data
  },

  // 동기화 상태 조회
  getSyncStatus: async () => {
    const response = await axios.get('/wholesaler-sync/sync/status')
    return response.data
  },

  // 만료된 상품 정리
  cleanupExpired: async () => {
    const response = await axios.post('/wholesaler-sync/cleanup-expired')
    return response.data
  }
}