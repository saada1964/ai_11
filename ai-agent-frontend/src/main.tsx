import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';
import './index.css';
import './i18n.ts';

// Import language store to initialize
import './store/languageStore';

// Development helper for testing without backend
if (import.meta.env.DEV) {
  // Add development helpers
  (window as any).__DEV_MODE__ = true;
  
  // Mock API responses for development
  if (import.meta.env.VITE_MOCK_API === 'true') {
    console.log('🔧 Development mode with mock API enabled');
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);