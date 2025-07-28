import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { productAPI } from '../services/api';

// Types (재사용을 위해 별도 파일로 분리하는 것이 좋지만, 일단 여기에 정의)
export interface Product {
  id: string;
  name: string;
  sku: string;
  barcode?: string;
  description?: string;
  category: string;
  subcategory?: string;
  brand?: string;
  status: 'active' | 'inactive' | 'out_of_stock' | 'discontinued';
  price: number;
  cost: number;
  wholesalePrice?: number;
  retailPrice?: number;
  currency: string;
  stock: number;
  minStock?: number;
  maxStock?: number;
  unit?: string;
  weight?: number;
  dimensions?: {
    length: number;
    width: number;
    height: number;
  };
  images: string[];
  thumbnailUrl?: string;
  tags: string[];
  attributes?: Record<string, any>;
  platformData?: Record<string, any>;
  supplierId?: string;
  supplierName?: string;
  createdAt: string;
  updatedAt: string;
  lastSyncedAt?: string;
}

export interface ProductFilters {
  search?: string;
  category?: string;
  subcategory?: string;
  brand?: string;
  status?: Product['status'];
  priceMin?: number;
  priceMax?: number;
  stockMin?: number;
  stockMax?: number;
  supplierId?: string;
  tags?: string[];
  sortBy?: 'name' | 'price' | 'stock' | 'createdAt' | 'updatedAt';
  sortOrder?: 'asc' | 'desc';
  page?: number;
  limit?: number;
}

// Query Keys
export const productKeys = {
  all: ['products'] as const,
  lists: () => [...productKeys.all, 'list'] as const,
  list: (filters: ProductFilters) => [...productKeys.lists(), filters] as const,
  details: () => [...productKeys.all, 'detail'] as const,
  detail: (id: string) => [...productKeys.details(), id] as const,
  stats: () => [...productKeys.all, 'stats'] as const,
};

// Hooks
export const useProducts = (filters: ProductFilters = {}) => {
  return useQuery({
    queryKey: productKeys.list(filters),
    queryFn: async () => {
      const response = await productAPI.getProducts(filters);
      return response.data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};

export const useProduct = (id: string) => {
  return useQuery({
    queryKey: productKeys.detail(id),
    queryFn: async () => {
      const response = await productAPI.getProduct(id);
      return response.data;
    },
    enabled: !!id,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};

export const useProductStats = () => {
  return useQuery({
    queryKey: productKeys.stats(),
    queryFn: async () => {
      const response = await productAPI.getProducts({ stats: true });
      return response.data.stats;
    },
    staleTime: 1000 * 60 * 10, // 10 minutes
  });
};

export const useCreateProduct = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (data: Partial<Product>) => {
      const response = await productAPI.createProduct(data);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate and refetch products list
      queryClient.invalidateQueries({ queryKey: productKeys.lists() });
      queryClient.invalidateQueries({ queryKey: productKeys.stats() });
    },
  });
};

export const useUpdateProduct = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<Product> }) => {
      const response = await productAPI.updateProduct(id, data);
      return response.data;
    },
    onSuccess: (data) => {
      // Update the specific product in cache
      queryClient.setQueryData(productKeys.detail(data.id), data);
      // Invalidate lists to refetch
      queryClient.invalidateQueries({ queryKey: productKeys.lists() });
      queryClient.invalidateQueries({ queryKey: productKeys.stats() });
    },
  });
};

export const useDeleteProduct = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (id: string) => {
      await productAPI.deleteProduct(id);
      return id;
    },
    onSuccess: (id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: productKeys.detail(id) });
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: productKeys.lists() });
      queryClient.invalidateQueries({ queryKey: productKeys.stats() });
    },
  });
};

export const useBulkUpdateProducts = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ ids, data }: { ids: string[]; data: Partial<Product> }) => {
      const response = await productAPI.bulkUpdate({ productIds: ids, updates: data });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: productKeys.all });
    },
  });
};

export const useImportProducts = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (data: any) => {
      const response = await productAPI.importProducts(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: productKeys.all });
    },
  });
};

export const useSearchProducts = (query: string, enabled = true) => {
  return useQuery({
    queryKey: ['products', 'search', query],
    queryFn: async () => {
      const response = await productAPI.searchProducts(query);
      return response.data;
    },
    enabled: enabled && !!query,
    staleTime: 1000 * 60 * 2, // 2 minutes
  });
};