import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, AuthTokens } from '../types/api';
import { apiService } from '../services/api/api';

interface AuthState {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  login: (credentials: { username: string; password: string }) => Promise<void>;
  register: (data: { username: string; email: string; password: string; confirm_password: string }) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  clearError: () => void;
  setTokens: (tokens: AuthTokens) => void;
  updateUser: (userData: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      tokens: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (credentials) => {
        set({ isLoading: true, error: null });
        
        try {
          const tokens = await apiService.login(credentials);
          
          // Set tokens in API service
          apiService.setTokens(tokens.access_token, tokens.refresh_token);
          
          // Get user data
          const user = await apiService.getCurrentUser();
          
          set({
            user,
            tokens,
            isAuthenticated: true,
            isLoading: false,
            error: null
          });
          
          console.log('Login successful for user:', user.username);
        } catch (error: any) {
          console.error('Login failed:', error);
          set({
            isLoading: false,
            error: error.response?.data?.message || error.message || 'فشل في تسجيل الدخول'
          });
          throw error;
        }
      },

      register: async (data) => {
        set({ isLoading: true, error: null });
        
        try {
          const tokens = await apiService.register(data);
          
          // Set tokens in API service
          apiService.setTokens(tokens.access_token, tokens.refresh_token);
          
          // Get user data
          const user = await apiService.getCurrentUser();
          
          set({
            user,
            tokens,
            isAuthenticated: true,
            isLoading: false,
            error: null
          });
          
          console.log('Registration successful for user:', user.username);
        } catch (error: any) {
          console.error('Registration failed:', error);
          set({
            isLoading: false,
            error: error.response?.data?.message || error.message || 'فشل في إنشاء الحساب'
          });
          throw error;
        }
      },

      logout: async () => {
        set({ isLoading: true });
        
        try {
          await apiService.logout();
        } catch (error) {
          console.error('Logout error:', error);
        } finally {
          set({
            user: null,
            tokens: null,
            isAuthenticated: false,
            isLoading: false,
            error: null
          });
          
          // Clear tokens from API service
          apiService.clearAuth();
        }
      },

      refreshUser: async () => {
        if (!get().isAuthenticated) return;
        
        try {
          const user = await apiService.getCurrentUser();
          set({ user });
        } catch (error) {
          console.error('Failed to refresh user data:', error);
          // If we can't refresh user data, logout
          get().logout();
        }
      },

      clearError: () => {
        set({ error: null });
      },

      setTokens: (tokens: AuthTokens) => {
        apiService.setTokens(tokens.access_token, tokens.refresh_token);
        set({ tokens });
      },

      updateUser: (userData: Partial<User>) => {
        const currentUser = get().user;
        if (currentUser) {
          set({
            user: { ...currentUser, ...userData }
          });
        }
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        tokens: state.tokens,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
);