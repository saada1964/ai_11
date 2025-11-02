// API Types for AI Agent Kernel
export interface User {
  id: number;
  username: string;
  email: string;
  balance: number;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  confirm_password: string;
}

export interface Conversation {
  id: number;
  user_id: number;
  title: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  message_count: number;
}

export interface Message {
  id: number;
  conversation_id: number;
  user_id: number;
  content: string;
  message_type: 'user' | 'assistant';
  created_at: string;
  updated_at: string;
  tokens_used?: number;
  cost?: number;
  model_used?: string;
  tools_used?: string[];
  metadata?: Record<string, any>;
}

export interface AgentRequest {
  query: string;
  user_id: number;
  conversation_id?: number | null;
  model_preference?: string;
  tools_preference?: string[];
  stream?: boolean;
}

export interface AgentResponse {
  response: string;
  conversation_id?: number;
  tokens_used?: number;
  cost?: number;
  execution_time?: number;
  model_used?: string;
  tools_used?: string[];
  suggestions?: string[];
  ui_components?: any[];
}

export interface Tool {
  id: number;
  name: string;
  description: string;
  is_active: boolean;
  category: string;
  parameters: Record<string, any>;
  cost_per_use: number;
}

export interface Model {
  id: number;
  name: string;
  provider: string;
  api_endpoint: string;
  api_key_standard: string;
  price_per_million_tokens: number;
  role: string;
  max_tokens: number;
  temperature: number;
  is_active: boolean;
}

export interface CreditCode {
  id: number;
  code: string;
  amount: number;
  discount_percent: number;
  max_uses: number | null;
  used_count: number;
  expires_at: string | null;
  is_active: boolean;
  created_by: number;
  created_at: string;
}

export interface CreditTransaction {
  id: number;
  user_id: number;
  type: 'purchase' | 'credit_code' | 'topup' | 'refund';
  amount: number;
  description: string;
  status: 'pending' | 'completed' | 'failed' | 'refunded';
  payment_method?: string;
  payment_id?: string;
  created_at: string;
  completed_at?: string;
}

export interface PaymentMethod {
  id: number;
  user_id: number;
  type: 'stripe' | 'plisio' | 'paypal';
  name: string;
  is_default: boolean;
  metadata: Record<string, any>;
  created_at: string;
}

export interface PaymentInitializationRequest {
  amount: number;
  currency: string;
  payment_method: 'stripe' | 'plisio' | 'paypal';
  return_url?: string;
  cancel_url?: string;
}

export interface PaymentInitializationResponse {
  payment_id: string;
  checkout_url: string;
  qr_code?: string;
  expires_at: string;
}

export interface WebSocketMessage {
  type: 'message' | 'typing' | 'connection' | 'error';
  data: any;
  timestamp: string;
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  services: Record<string, boolean>;
  uptime: number;
  version: string;
}

export interface APIResponse<T = any> {
  success: boolean;
  data: T;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T = any> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface FilterOptions {
  search?: string;
  date_from?: string;
  date_to?: string;
  status?: string;
  type?: string;
}

export interface SortOptions {
  field: string;
  direction: 'asc' | 'desc';
}

export interface QueryOptions {
  page?: number;
  limit?: number;
  filters?: FilterOptions;
  sort?: SortOptions;
}