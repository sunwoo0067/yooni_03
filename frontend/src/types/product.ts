export interface Product {
  id: string
  name: string
  sku?: string
  barcode?: string
  description?: string
  category?: string
  brand?: string
  price: number
  cost?: number
  wholesale_price?: number
  stock_quantity: number
  min_stock?: number
  max_stock?: number
  weight?: number
  dimensions?: {
    length?: number
    width?: number
    height?: number
  }
  status: 'active' | 'inactive' | 'out_of_stock' | 'discontinued'
  tags?: string[]
  image_urls?: string[]
  main_image_url?: string
  platform_listings?: PlatformListing[]
  created_at?: string
  updated_at?: string
}

export interface PlatformListing {
  id: string
  platform: string
  platform_product_id?: string
  is_synced: boolean
  last_sync?: string
  price?: number
  status?: string
}

export interface ProductFilter {
  search?: string
  category?: string
  status?: string
  platform?: string
  min_price?: number
  max_price?: number
  low_stock?: boolean
  out_of_stock?: boolean
}

export interface ProductStats {
  total: number
  active: number
  inactive: number
  out_of_stock: number
  low_stock: number
}