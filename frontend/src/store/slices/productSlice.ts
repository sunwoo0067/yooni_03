import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../index';

// Types
interface ProductUIState {
  selectedProductId: string | null;
  filters: {
    search?: string;
    category?: string;
    status?: string;
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
    page?: number;
    limit?: number;
  };
  recentlyViewed: string[];
  compareList: string[];
  bulkSelection: string[];
}

// Initial state - 클라이언트 UI 상태만 관리
const initialState: ProductUIState = {
  selectedProductId: null,
  filters: {
    page: 1,
    limit: 20,
    sortBy: 'updatedAt',
    sortOrder: 'desc',
  },
  recentlyViewed: typeof localStorage !== 'undefined' ? JSON.parse(localStorage.getItem('recentlyViewedProducts') || '[]') : [],
  compareList: [],
  bulkSelection: [],
};

// Slice
const productSlice = createSlice({
  name: 'product',
  initialState,
  reducers: {
    setFilters: (state, action: PayloadAction<Partial<ProductUIState['filters']>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    
    resetFilters: (state) => {
      state.filters = {
        page: 1,
        limit: 20,
        sortBy: 'updatedAt',
        sortOrder: 'desc',
      };
    },
    
    selectProduct: (state, action: PayloadAction<string>) => {
      state.selectedProductId = action.payload;
      
      // Add to recently viewed
      state.recentlyViewed = state.recentlyViewed.filter(id => id !== action.payload);
      state.recentlyViewed.unshift(action.payload);
      state.recentlyViewed = state.recentlyViewed.slice(0, 10);
      localStorage.setItem('recentlyViewedProducts', JSON.stringify(state.recentlyViewed));
    },
    
    clearSelectedProduct: (state) => {
      state.selectedProductId = null;
    },
    
    addToCompareList: (state, action: PayloadAction<string>) => {
      if (!state.compareList.includes(action.payload) && state.compareList.length < 4) {
        state.compareList.push(action.payload);
      }
    },
    
    removeFromCompareList: (state, action: PayloadAction<string>) => {
      state.compareList = state.compareList.filter(id => id !== action.payload);
    },
    
    clearCompareList: (state) => {
      state.compareList = [];
    },
    
    toggleBulkSelection: (state, action: PayloadAction<string>) => {
      const index = state.bulkSelection.indexOf(action.payload);
      if (index > -1) {
        state.bulkSelection.splice(index, 1);
      } else {
        state.bulkSelection.push(action.payload);
      }
    },
    
    setBulkSelection: (state, action: PayloadAction<string[]>) => {
      state.bulkSelection = action.payload;
    },
    
    clearBulkSelection: (state) => {
      state.bulkSelection = [];
    },
  },
});

// Actions
export const {
  setFilters,
  resetFilters,
  selectProduct,
  clearSelectedProduct,
  addToCompareList,
  removeFromCompareList,
  clearCompareList,
  toggleBulkSelection,
  setBulkSelection,
  clearBulkSelection,
} = productSlice.actions;

// Selectors
export const selectSelectedProductId = (state: RootState) => state.product.selectedProductId;
export const selectProductFilters = (state: RootState) => state.product.filters;
export const selectRecentlyViewedProducts = (state: RootState) => state.product.recentlyViewed;
export const selectCompareList = (state: RootState) => state.product.compareList;
export const selectBulkSelection = (state: RootState) => state.product.bulkSelection;
export const selectIsProductSelected = (productId: string) => (state: RootState) =>
  state.product.bulkSelection.includes(productId);

// Legacy exports removed - WebSocket now uses event-based communication

export default productSlice.reducer;