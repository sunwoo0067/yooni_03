import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../index';

// Types
type Theme = 'light' | 'dark' | 'system';
type SidebarState = 'expanded' | 'collapsed' | 'hidden';
type NotificationType = 'success' | 'error' | 'warning' | 'info';

interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message?: string;
  duration?: number;
  timestamp: number;
  actionLabel?: string;
  actionCallback?: () => void;
}

interface Modal {
  id: string;
  component: string;
  props?: Record<string, any>;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  closable?: boolean;
  onClose?: () => void;
}

interface Breadcrumb {
  label: string;
  path?: string;
  icon?: string;
}

interface UIState {
  theme: Theme;
  sidebarState: SidebarState;
  sidebarOpen: boolean;
  collapsed: boolean;
  isMobile: boolean;
  isTablet: boolean;
  notifications: Notification[];
  modals: Modal[];
  breadcrumbs: Breadcrumb[];
  isLoading: boolean;
  loadingMessage?: string;
  pageTitle: string;
  activeTab?: string;
  expandedMenuItems: string[];
  pinnedMenuItems: string[];
  recentlyVisited: Array<{ label: string; path: string; timestamp: number }>;
  userPreferences: {
    compactMode: boolean;
    showNotifications: boolean;
    autoSave: boolean;
    language: string;
    dateFormat: string;
    currency: string;
  };
}

// Initial state
const initialState: UIState = {
  theme: (localStorage.getItem('theme') as Theme) || 'system',
  sidebarState: 'expanded',
  sidebarOpen: true,
  collapsed: false,
  isMobile: false,
  isTablet: false,
  notifications: [],
  modals: [],
  breadcrumbs: [],
  isLoading: false,
  pageTitle: 'Dashboard',
  expandedMenuItems: [],
  pinnedMenuItems: JSON.parse(localStorage.getItem('pinnedMenuItems') || '[]'),
  recentlyVisited: JSON.parse(localStorage.getItem('recentlyVisited') || '[]'),
  userPreferences: {
    compactMode: false,
    showNotifications: true,
    autoSave: true,
    language: 'ko',
    dateFormat: 'YYYY-MM-DD',
    currency: 'KRW',
  },
};

// Slice
const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setTheme: (state, action: PayloadAction<Theme>) => {
      state.theme = action.payload;
      localStorage.setItem('theme', action.payload);
    },
    
    setSidebarState: (state, action: PayloadAction<SidebarState>) => {
      state.sidebarState = action.payload;
    },
    
    toggleSidebar: (state) => {
      if (state.sidebarState === 'expanded') {
        state.sidebarState = 'collapsed';
        state.sidebarOpen = false;
        state.collapsed = true;
      } else if (state.sidebarState === 'collapsed') {
        state.sidebarState = 'expanded';
        state.sidebarOpen = true;
        state.collapsed = false;
      }
    },
    
    toggleTheme: (state) => {
      // Toggle between light and dark themes
      if (state.theme === 'light') {
        state.theme = 'dark';
      } else if (state.theme === 'dark') {
        state.theme = 'light';
      } else {
        // If theme is 'system', default to 'light'
        state.theme = 'light';
      }
      localStorage.setItem('theme', state.theme);
    },
    
    setDeviceType: (state, action: PayloadAction<{ isMobile: boolean; isTablet: boolean }>) => {
      state.isMobile = action.payload.isMobile;
      state.isTablet = action.payload.isTablet;
      
      // Auto-adjust sidebar for mobile
      if (action.payload.isMobile) {
        state.sidebarState = 'hidden';
      }
    },
    
    addNotification: (state, action: PayloadAction<Omit<Notification, 'id' | 'timestamp'>>) => {
      const notification: Notification = {
        ...action.payload,
        id: `notification-${Date.now()}-${Math.random()}`,
        timestamp: Date.now(),
        duration: action.payload.duration || 5000,
      };
      state.notifications.push(notification);
    },
    
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(n => n.id !== action.payload);
    },
    
    clearNotifications: (state) => {
      state.notifications = [];
    },
    
    openModal: (state, action: PayloadAction<Omit<Modal, 'id'>>) => {
      const modal: Modal = {
        ...action.payload,
        id: `modal-${Date.now()}-${Math.random()}`,
        closable: action.payload.closable !== false,
      };
      state.modals.push(modal);
    },
    
    closeModal: (state, action: PayloadAction<string>) => {
      state.modals = state.modals.filter(m => m.id !== action.payload);
    },
    
    closeAllModals: (state) => {
      state.modals = [];
    },
    
    setBreadcrumbs: (state, action: PayloadAction<Breadcrumb[]>) => {
      state.breadcrumbs = action.payload;
    },
    
    setLoading: (state, action: PayloadAction<boolean | { loading: boolean; message?: string }>) => {
      if (typeof action.payload === 'boolean') {
        state.isLoading = action.payload;
        state.loadingMessage = undefined;
      } else {
        state.isLoading = action.payload.loading;
        state.loadingMessage = action.payload.message;
      }
    },
    
    setPageTitle: (state, action: PayloadAction<string>) => {
      state.pageTitle = action.payload;
      document.title = `${action.payload} - Yooni Platform`;
    },
    
    setActiveTab: (state, action: PayloadAction<string>) => {
      state.activeTab = action.payload;
    },
    
    toggleMenuItem: (state, action: PayloadAction<string>) => {
      const index = state.expandedMenuItems.indexOf(action.payload);
      if (index > -1) {
        state.expandedMenuItems.splice(index, 1);
      } else {
        state.expandedMenuItems.push(action.payload);
      }
    },
    
    togglePinnedMenuItem: (state, action: PayloadAction<string>) => {
      const index = state.pinnedMenuItems.indexOf(action.payload);
      if (index > -1) {
        state.pinnedMenuItems.splice(index, 1);
      } else {
        state.pinnedMenuItems.push(action.payload);
      }
      localStorage.setItem('pinnedMenuItems', JSON.stringify(state.pinnedMenuItems));
    },
    
    addRecentlyVisited: (state, action: PayloadAction<{ label: string; path: string }>) => {
      const newItem = {
        ...action.payload,
        timestamp: Date.now(),
      };
      
      // Remove if already exists
      state.recentlyVisited = state.recentlyVisited.filter(
        item => item.path !== action.payload.path
      );
      
      // Add to beginning
      state.recentlyVisited.unshift(newItem);
      
      // Keep only last 10
      state.recentlyVisited = state.recentlyVisited.slice(0, 10);
      
      localStorage.setItem('recentlyVisited', JSON.stringify(state.recentlyVisited));
    },
    
    updateUserPreferences: (state, action: PayloadAction<Partial<UIState['userPreferences']>>) => {
      state.userPreferences = {
        ...state.userPreferences,
        ...action.payload,
      };
      localStorage.setItem('userPreferences', JSON.stringify(state.userPreferences));
    },
    
    resetUI: (state) => {
      // Reset to initial state but keep some user preferences
      return {
        ...initialState,
        theme: state.theme,
        pinnedMenuItems: state.pinnedMenuItems,
        recentlyVisited: state.recentlyVisited,
        userPreferences: state.userPreferences,
      };
    },
  },
});

// Actions
export const {
  setTheme,
  setSidebarState,
  toggleSidebar,
  toggleTheme,
  setDeviceType,
  addNotification,
  removeNotification,
  clearNotifications,
  openModal,
  closeModal,
  closeAllModals,
  setBreadcrumbs,
  setLoading,
  setPageTitle,
  setActiveTab,
  toggleMenuItem,
  togglePinnedMenuItem,
  addRecentlyVisited,
  updateUserPreferences,
  resetUI,
} = uiSlice.actions;

// Selectors
export const selectTheme = (state: RootState) => state.ui.theme;
export const selectSidebarState = (state: RootState) => state.ui.sidebarState;
export const selectIsMobile = (state: RootState) => state.ui.isMobile;
export const selectIsTablet = (state: RootState) => state.ui.isTablet;
export const selectNotifications = (state: RootState) => state.ui.notifications;
export const selectModals = (state: RootState) => state.ui.modals;
export const selectBreadcrumbs = (state: RootState) => state.ui.breadcrumbs;
export const selectIsLoading = (state: RootState) => state.ui.isLoading;
export const selectLoadingMessage = (state: RootState) => state.ui.loadingMessage;
export const selectPageTitle = (state: RootState) => state.ui.pageTitle;
export const selectActiveTab = (state: RootState) => state.ui.activeTab;
export const selectExpandedMenuItems = (state: RootState) => state.ui.expandedMenuItems;
export const selectPinnedMenuItems = (state: RootState) => state.ui.pinnedMenuItems;
export const selectRecentlyVisited = (state: RootState) => state.ui.recentlyVisited;
export const selectUserPreferences = (state: RootState) => state.ui.userPreferences;

// Helper selectors
export const selectIsMenuItemExpanded = (menuItem: string) => (state: RootState) => 
  state.ui.expandedMenuItems.includes(menuItem);

export const selectIsMenuItemPinned = (menuItem: string) => (state: RootState) => 
  state.ui.pinnedMenuItems.includes(menuItem);

export default uiSlice.reducer;