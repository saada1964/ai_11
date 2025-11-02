// API Configuration
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  TIMEOUT: 30000,
  HEADERS: {
    'Content-Type': 'application/json',
  },
};

// WebSocket Configuration
export const WS_CONFIG = {
  URL: import.meta.env.VITE_WS_URL || 'ws://localhost:8000',
  RECONNECT_INTERVAL: 3000,
  MAX_RECONNECT_ATTEMPTS: 5,
};

// App Configuration
export const APP_CONFIG = {
  DEFAULT_LANGUAGE: 'ar' as const,
  DEFAULT_THEME: 'light' as const,
  MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
  SUPPORTED_FILE_TYPES: [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'video/mp4',
    'video/webm',
    'audio/mpeg',
    'audio/wav',
    'audio/ogg',
  ],
  MESSAGES_PER_PAGE: 50,
  CONVERSATIONS_PER_PAGE: 20,
};

// Storage Keys
export const STORAGE_KEYS = {
  USER: 'ai_agent_user',
  TOKEN: 'ai_agent_token',
  LANGUAGE: 'ai_agent_language',
  THEME: 'ai_agent_theme',
  SETTINGS: 'ai_agent_settings',
};
