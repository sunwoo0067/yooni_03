export interface CollectedProduct {
  id: string
  source: string
  supplier_id?: string
  supplier_name?: string
  supplier_url?: string
  name: string
  description?: string
  brand?: string
  category?: string
  price: number
  original_price?: number
  currency: string
  image_urls: string[]
  main_image_url?: string
  options?: Record<string, any>
  stock_status: string
  stock_quantity?: number
  minimum_order?: number
  shipping_info?: Record<string, any>
  attributes?: Record<string, any>
  quality_score?: number
  popularity_score?: number
  status: CollectionStatus
  collected_at: string
  expires_at?: string
  last_checked?: string
  collection_keyword?: string
  collection_batch_id?: string
}

export enum CollectionStatus {
  COLLECTED = 'collected',
  SOURCED = 'sourced',
  REJECTED = 'rejected',
  EXPIRED = 'expired'
}

export interface CollectionRequest {
  source: string
  keyword?: string
  category?: string
  price_min?: number
  price_max?: number
  limit?: number
  page?: number
}

export interface WholesalerSource {
  id: string
  name: string
  description: string
  base_url: string
  api_type: string
  categories: string[]
  is_active: boolean
  features: string[]
}

export interface SyncStatus {
  is_running: boolean
  current_source?: string
  current_category?: string
  progress?: number
  products_collected: number
  products_updated: number
  products_failed: number
  started_at?: string
  estimated_completion?: string
  errors: string[]
}