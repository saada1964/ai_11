// User types
export interface User {
  id: number;
  username: string;
  email: string;
  phone?: string;
  balance: number;
  created_at: string;
  avatar?: string;
}

// Conversation types
export interface Conversation {
  id: number;
  user_id: number;
  title: string;
  summary?: string;
  total_messages: number;
  created_at: string;
  updated_at: string;
  username?: string;
}

// Message types
export interface Message {
  id?: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tokens_used?: number;
  cost_usd?: number;
  created_at?: string;
  attachments?: FileAttachment[];
}

// File attachment types
export interface FileAttachment {
  id: string;
  name: string;
  type: string;
  size: number;
  url: string;
  preview?: string;
}

// Agent request types
export interface AgentRequest {
  query: string;
  user_id: number;
  conversation_id?: number;
  context?: Record<string, any>;
  model_preference?: string;
}

// Agent response types
export interface AgentResponse {
  response: string;
  conversation_id: number;
  intent: string;
  tokens_used: number;
  cost_usd: number;
  plan_description?: string;
}

// Streaming message types
export interface StreamMessage {
  type: 'status' | 'chunk' | 'step' | 'complete' | 'error';
  content?: string;
  message?: string;
  step?: string;
  progress?: string;
  conversation_id?: number;
  response?: string;
  tokens_used?: number;
  cost_usd?: number;
  intent?: string;
  plan_description?: string;
  error?: string;
  timestamp?: string;
}

// Credit types
export interface CreditCode {
  id: number;
  code: string;
  name: string;
  description?: string;
  credit_amount: number;
  discount_percentage?: number;
  current_uses: number;
  max_uses?: number;
  expires_at?: string;
  is_active: boolean;
}

export interface CreditTransaction {
  id: number;
  user_id: number;
  transaction_type: 'purchase' | 'credit_code' | 'topup' | 'refund';
  amount: number;
  status: 'pending' | 'completed' | 'failed' | 'refunded';
  credit_code_id?: number;
  payment_record_id?: number;
  created_at: string;
  metadata?: Record<string, any>;
}

export interface PaymentMethod {
  id: number;
  name: string;
  provider: string;
  min_amount_usd: number;
  max_amount_usd: number;
  fees_percentage: number;
  fixed_fee_usd: number;
  is_active: boolean;
  icon?: string;
}

// Settings types
export interface UserSettings {
  language: 'ar' | 'en';
  theme: 'light' | 'dark' | 'auto';
  notifications: boolean;
  soundEnabled: boolean;
}

// API Response types
export interface APIResponse<T = any> {
  success: boolean;
  message?: string;
  data?: T;
  error?: string;
}

// Theme types
export type Theme = 'light' | 'dark';
export type Language = 'ar' | 'en';
