import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';

// Components
import { Layout } from './components/layout/Layout';
import { LoginForm } from './components/auth/LoginForm';
import { RegisterForm } from './components/auth/RegisterForm';
import ChatPage from './pages/ChatPage';
import { SettingsPage } from './pages/SettingsPage';
import { CreditPage } from './pages/CreditPage';
import { Header } from './components/layout/Header';

// Hooks & Stores
import { useAuthStore } from './store/authStore';
import { useLanguageStore } from './store/languageStore';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

// Protected Route Component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

// App Routes Component
const AppRoutes: React.FC = () => {
  const { isAuthenticated } = useAuthStore();
  
  return (
    <Routes>
      {/* Public Routes */}
      <Route 
        path="/login" 
        element={
          isAuthenticated ? <Navigate to="/chat" replace /> : <LoginForm />
        } 
      />
      <Route 
        path="/register" 
        element={
          isAuthenticated ? <Navigate to="/chat" replace /> : <RegisterForm />
        } 
      />
      
      {/* Protected Routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/chat" replace />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="credit" element={<CreditPage />} />
      </Route>
      
      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

function App() {
  const { language } = useLanguageStore();
  
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className={`min-h-screen bg-background text-foreground ${
          language === 'ar' ? 'font-arabic' : 'font-sans'
        }`} dir={language === 'ar' ? 'rtl' : 'ltr'}>
          <AppRoutes />
          <Toaster 
            position={language === 'ar' ? 'top-left' : 'top-right'}
            richColors
          />
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;