import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../index';

// Types
interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  avatar?: string;
  permissions?: string[];
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  sessionExpiry: number | null;
}

interface LoginCredentials {
  email: string;
  password: string;
}

interface RegisterData extends LoginCredentials {
  name: string;
  confirmPassword: string;
}

interface AuthResponse {
  user: User;
  token: string;
  refreshToken?: string;
  expiresIn?: number;
}

// Initial state
const initialState: AuthState = {
  user: null,
  token: localStorage.getItem('token'),
  isAuthenticated: false,
  isLoading: false,
  error: null,
  sessionExpiry: null,
};

// Async thunks
export const login = createAsyncThunk<AuthResponse, LoginCredentials>(
  'auth/login',
  async (credentials, { rejectWithValue }) => {
    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials),
      });

      if (!response.ok) {
        const error = await response.json();
        return rejectWithValue(error.message || 'Login failed');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      return rejectWithValue('Network error occurred');
    }
  }
);

export const register = createAsyncThunk<AuthResponse, RegisterData>(
  'auth/register',
  async (userData, { rejectWithValue }) => {
    try {
      const response = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData),
      });

      if (!response.ok) {
        const error = await response.json();
        return rejectWithValue(error.message || 'Registration failed');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      return rejectWithValue('Network error occurred');
    }
  }
);

export const logout = createAsyncThunk(
  'auth/logout',
  async (_, { rejectWithValue }) => {
    try {
      const response = await fetch('/api/v1/auth/logout', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Logout failed');
      }

      return null;
    } catch (error) {
      return rejectWithValue('Logout failed');
    }
  }
);

export const refreshToken = createAsyncThunk<AuthResponse>(
  'auth/refreshToken',
  async (_, { getState, rejectWithValue }) => {
    try {
      const state = getState() as RootState;
      const response = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${state.auth.token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      return rejectWithValue('Token refresh failed');
    }
  }
);

export const fetchCurrentUser = createAsyncThunk<User>(
  'auth/fetchCurrentUser',
  async (_, { getState, rejectWithValue }) => {
    try {
      const state = getState() as RootState;
      const response = await fetch('/api/v1/auth/me', {
        headers: {
          'Authorization': `Bearer ${state.auth.token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch user data');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      return rejectWithValue('Failed to fetch user data');
    }
  }
);

// Slice
const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials: (state, action: PayloadAction<{ user: User; token: string }>) => {
      state.user = action.payload.user;
      state.token = action.payload.token;
      state.isAuthenticated = true;
      localStorage.setItem('token', action.payload.token);
    },
    clearCredentials: (state) => {
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      state.sessionExpiry = null;
      localStorage.removeItem('token');
    },
    updateUser: (state, action: PayloadAction<Partial<User>>) => {
      if (state.user) {
        state.user = { ...state.user, ...action.payload };
      }
    },
    setSessionExpiry: (state, action: PayloadAction<number>) => {
      state.sessionExpiry = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // Login
    builder
      .addCase(login.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload.user;
        state.token = action.payload.token;
        state.isAuthenticated = true;
        if (action.payload.expiresIn) {
          state.sessionExpiry = Date.now() + action.payload.expiresIn * 1000;
        }
        localStorage.setItem('token', action.payload.token);
      })
      .addCase(login.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Register
    builder
      .addCase(register.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(register.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload.user;
        state.token = action.payload.token;
        state.isAuthenticated = true;
        localStorage.setItem('token', action.payload.token);
      })
      .addCase(register.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Logout
    builder
      .addCase(logout.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(logout.fulfilled, (state) => {
        state.isLoading = false;
        state.user = null;
        state.token = null;
        state.refreshToken = null;
        state.isAuthenticated = false;
        state.sessionExpiry = null;
        state.rememberMe = false;
        state.sessionWarningShown = false;
        state.activeSessions = [];
        
        // Clear localStorage
        removeStorageItem(STORAGE_KEYS.TOKEN);
        removeStorageItem(STORAGE_KEYS.REFRESH_TOKEN);
        removeStorageItem(STORAGE_KEYS.USER);
        removeStorageItem(STORAGE_KEYS.REMEMBER_ME);
      })
      .addCase(logout.rejected, (state) => {
        state.isLoading = false;
        // Even if logout fails, clear local state
        state.user = null;
        state.token = null;
        state.refreshToken = null;
        state.isAuthenticated = false;
        state.sessionExpiry = null;
        state.rememberMe = false;
        state.sessionWarningShown = false;
        state.activeSessions = [];
        
        // Clear localStorage
        removeStorageItem(STORAGE_KEYS.TOKEN);
        removeStorageItem(STORAGE_KEYS.REFRESH_TOKEN);
        removeStorageItem(STORAGE_KEYS.USER);
        removeStorageItem(STORAGE_KEYS.REMEMBER_ME);
      });

    // Refresh Token
    builder
      .addCase(refreshToken.fulfilled, (state, action) => {
        state.token = action.payload.token;
        state.refreshToken = action.payload.refreshToken;
        if (action.payload.expiresIn) {
          state.sessionExpiry = Date.now() + action.payload.expiresIn * 1000;
        }
        
        // Store in localStorage
        setStorageItem(STORAGE_KEYS.TOKEN, action.payload.token);
        setStorageItem(STORAGE_KEYS.REFRESH_TOKEN, action.payload.refreshToken);
      })
      .addCase(refreshToken.rejected, (state) => {
        // If refresh fails, clear auth state
        state.user = null;
        state.token = null;
        state.refreshToken = null;
        state.isAuthenticated = false;
        state.sessionExpiry = null;
        state.rememberMe = false;
        state.sessionWarningShown = false;
        
        // Clear localStorage
        removeStorageItem(STORAGE_KEYS.TOKEN);
        removeStorageItem(STORAGE_KEYS.REFRESH_TOKEN);
        removeStorageItem(STORAGE_KEYS.USER);
        removeStorageItem(STORAGE_KEYS.REMEMBER_ME);
      });

    // Fetch Current User
    builder
      .addCase(fetchCurrentUser.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(fetchCurrentUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload;
        state.isAuthenticated = true;
      })
      .addCase(fetchCurrentUser.rejected, (state) => {
        state.isLoading = false;
        state.isAuthenticated = false;
      });
  },
});

// Actions
export const {
  setCredentials,
  clearCredentials,
  updateUser,
  setSessionExpiry,
  clearError,
} = authSlice.actions;

// Selectors
export const selectCurrentUser = (state: RootState) => state.auth.user;
export const selectIsAuthenticated = (state: RootState) => state.auth.isAuthenticated;
export const selectAuthToken = (state: RootState) => state.auth.token;
export const selectAuthLoading = (state: RootState) => state.auth.isLoading;
export const selectAuthError = (state: RootState) => state.auth.error;
export const selectSessionExpiry = (state: RootState) => state.auth.sessionExpiry;

export default authSlice.reducer;