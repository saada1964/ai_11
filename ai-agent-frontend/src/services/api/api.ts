import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { 
  User, 
  AuthRequest, 
  RegisterRequest, 
  AuthTokens, 
  APIResponse, 
  Conversation, 
  Message, 
  AgentRequest, 
  AgentResponse,
  Tool,
  Model,
  CreditCode,
  CreditTransaction,
  PaymentMethod,
  PaymentInitializationRequest,
  PaymentInitializationResponse,
  SystemHealth,
  PaginatedResponse,
  QueryOptions
} from '../../types/api';

class APIService {
  private client: AxiosInstance;
  private authClient: AxiosInstance;
  private mockMode: boolean;

  constructor() {
    // Force mock mode in production or when no backend URL is provided
    this.mockMode = import.meta.env.VITE_MOCK_API === 'true' || 
                   !import.meta.env.VITE_API_BASE_URL || 
                   import.meta.env.PROD;
    
    const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    
    // Force mock mode if we're in production and no backend is configured
    if (import.meta.env.PROD && !import.meta.env.VITE_API_BASE_URL) {
      this.mockMode = true;
    }
    
    if (this.mockMode) {
      console.log('🔧 API Service running in MOCK mode');
    } else {
      console.log('🔌 API Service connecting to:', baseURL);
    }
    
    // Main API client
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Auth client for handling token refresh
    this.authClient = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (this.mockMode) {
      console.log('🔧 API Service running in MOCK mode');
    }

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor to handle token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (this.mockMode) {
          return Promise.reject(error);
        }

        const originalRequest = error.config;
        
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          
          try {
            const newToken = await this.refreshToken();
            if (newToken) {
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return this.client(originalRequest);
            }
          } catch (refreshError) {
            this.clearAuth();
            window.location.href = '/login';
          }
        }
        
        return Promise.reject(error);
      }
    );
  }

  private getAccessToken(): string | null {
    return localStorage.getItem('access_token');
  }

  private getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token');
  }

  private async refreshToken(): Promise<string | null> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) return null;

    try {
      const response = await this.authClient.post('/auth/refresh', {
        refresh_token: refreshToken
      });
      
      const { access_token } = response.data.data;
      this.setTokens(access_token, refreshToken);
      return access_token;
    } catch (error) {
      this.clearAuth();
      return null;
    }
  }

  setTokens(accessToken: string, refreshToken?: string): void {
    localStorage.setItem('access_token', accessToken);
    if (refreshToken) {
      localStorage.setItem('refresh_token', refreshToken);
    }
  }

  clearAuth(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  // Mock data generators
  private generateMockUser(): User {
    return {
      id: 1,
      username: 'مستخدم تجريبي',
      email: 'demo@example.com',
      balance: 1000,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      is_active: true
    };
  }

  private generateMockConversations(): Conversation[] {
    return [
      {
        id: 1,
        user_id: 1,
        title: 'محادثة تجريبية 1',
        created_at: new Date(Date.now() - 3600000).toISOString(),
        updated_at: new Date(Date.now() - 3600000).toISOString(),
        is_active: true,
        message_count: 5
      },
      {
        id: 2,
        user_id: 1,
        title: 'محادثة حول الذكاء الاصطناعي',
        created_at: new Date(Date.now() - 7200000).toISOString(),
        updated_at: new Date(Date.now() - 7200000).toISOString(),
        is_active: true,
        message_count: 12
      }
    ];
  }

  private generateMockMessages(): Message[] {
    return [
      {
        id: 1,
        conversation_id: 1,
        user_id: 1,
        content: 'مرحبا، كيف يمكنني مساعدتك اليوم؟',
        message_type: 'assistant',
        created_at: new Date(Date.now() - 1800000).toISOString(),
        updated_at: new Date(Date.now() - 1800000).toISOString(),
        tokens_used: 45,
        cost: 0.02,
        model_used: 'gpt-3.5-turbo'
      },
      {
        id: 2,
        conversation_id: 1,
        user_id: 1,
        content: 'أريد معلومات حول الذكاء الاصطناعي',
        message_type: 'user',
        created_at: new Date(Date.now() - 1700000).toISOString(),
        updated_at: new Date(Date.now() - 1700000).toISOString(),
        tokens_used: 12,
        cost: 0.01,
        model_used: null
      }
    ];
  }

  private generateMockTransactions(): CreditTransaction[] {
    return [
      {
        id: 1,
        user_id: 1,
        type: 'credit_code',
        amount: 100,
        description: 'كود خصم تجريبي',
        status: 'completed',
        created_at: new Date(Date.now() - 86400000).toISOString()
      },
      {
        id: 2,
        user_id: 1,
        type: 'purchase',
        amount: 50,
        description: 'شراء رصيد',
        status: 'completed',
        created_at: new Date(Date.now() - 172800000).toISOString()
      }
    ];
  }

  // Mock API responses
  private mockResponse<T>(data: T, delay: number = 500): Promise<APIResponse<T>> {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({ success: true, data });
      }, delay);
    });
  }

  private mockPaginatedResponse<T>(items: T[], page: number = 1, limit: number = 10): Promise<PaginatedResponse<T>> {
    const start = (page - 1) * limit;
    const end = start + limit;
    const paginatedItems = items.slice(start, end);
    
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          items: paginatedItems,
          total: items.length,
          page,
          limit,
          has_next: end < items.length,
          has_prev: page > 1
        });
      }, 300);
    });
  }

  // Auth Methods
  async login(credentials: AuthRequest): Promise<AuthTokens> {
    if (this.mockMode || credentials.username === 'demo' && credentials.password === 'demo123') {
      const result = await this.mockResponse({
        access_token: 'mock_access_token',
        refresh_token: 'mock_refresh_token',
        token_type: 'Bearer',
        expires_in: 1800
      });
      return result.data;
    }
    
    try {
      const response: AxiosResponse<APIResponse<AuthTokens>> = await this.client.post('/auth/login', credentials);
      return response.data.data;
    } catch (error) {
      // Fallback to mock if real API fails
      if (error.code === 'NETWORK_ERROR') {
        console.log('Network error, falling back to mock mode');
        return {
          access_token: 'mock_access_token',
          refresh_token: 'mock_refresh_token',
          token_type: 'Bearer',
          expires_in: 1800
        };
      }
      throw error;
    }
  }

  async register(data: RegisterRequest): Promise<AuthTokens> {
    if (this.mockMode) {
      const result = await this.mockResponse({
        access_token: 'mock_access_token',
        refresh_token: 'mock_refresh_token',
        token_type: 'Bearer',
        expires_in: 1800
      });
      return result.data;
    }

    const response: AxiosResponse<APIResponse<AuthTokens>> = await this.client.post('/auth/register', data);
    return response.data.data;
  }

  async logout(): Promise<void> {
    if (this.mockMode) {
      return;
    }

    const refreshToken = this.getRefreshToken();
    if (refreshToken) {
      await this.client.post('/auth/logout', { refresh_token: refreshToken });
    }
    this.clearAuth();
  }

  async getCurrentUser(): Promise<User> {
    if (this.mockMode) {
      const result = await this.mockResponse(this.generateMockUser());
      return result.data;
    }

    const response: AxiosResponse<APIResponse<User>> = await this.client.get('/auth/me');
    return response.data.data;
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    if (this.mockMode) {
      return;
    }

    await this.client.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword
    });
  }

  // Agent Methods
  async invokeAgent(request: AgentRequest): Promise<AgentResponse> {
    if (this.mockMode) {
      const mockResponses = [
        'مرحباً! أنا وكيل الذكاء الاصطناعي. كيف يمكنني مساعدتك اليوم؟',
        'شكراً لسؤالك. الذكاء الاصطناعي هو تقنية متطورة تساعد في حل المشاكل المعقدة.',
        'هذا سؤال ممتاز! دعني أشرح لك المفهوم بالتفصيل.',
        'يمكنني مساعدتك في العديد من المهام. ما الذي تريد أن نتحدث عنه؟'
      ];
      
      const randomResponse = mockResponses[Math.floor(Math.random() * mockResponses.length)];
      
      const result = await this.mockResponse({
        response: randomResponse,
        conversation_id: request.conversation_id || 1,
        tokens_used: Math.floor(Math.random() * 100) + 10,
        cost: Math.random() * 0.05,
        execution_time: Math.random() * 2,
        model_used: 'gpt-3.5-turbo',
        tools_used: [],
        suggestions: ['كيف يعمل الذكاء الاصطناعي؟', 'ما هي تطبيقات الذكاء الاصطناعي؟']
      });
      return result.data;
    }

    const response: AxiosResponse<APIResponse<AgentResponse>> = await this.client.post('/agent/invoke', request);
    return response.data.data;
  }

  async invokeAgentStream(request: AgentRequest): Promise<ReadableStream> {
    if (this.mockMode) {
      throw new Error('Mock mode does not support streaming');
    }

    const response = await this.client.post('/agent/invoke-stream', request, {
      responseType: 'stream'
    });
    return response.data;
  }

  // Conversation Methods
  async getConversations(options?: QueryOptions): Promise<PaginatedResponse<Conversation>> {
    if (this.mockMode) {
      return this.mockPaginatedResponse(this.generateMockConversations(), options?.page, options?.limit);
    }

    const params = new URLSearchParams();
    if (options?.page) params.append('page', options.page.toString());
    if (options?.limit) params.append('limit', options.limit.toString());
    if (options?.filters?.search) params.append('search', options.filters.search);
    
    const response: AxiosResponse<APIResponse<PaginatedResponse<Conversation>>> = await this.client.get(`/conversations?${params}`);
    return response.data.data;
  }

  async getConversation(id: number): Promise<Conversation> {
    if (this.mockMode) {
      const conversations = this.generateMockConversations();
      const conversation = conversations.find(c => c.id === id) || conversations[0];
      const result = await this.mockResponse(conversation);
      return result.data;
    }

    const response: AxiosResponse<APIResponse<Conversation>> = await this.client.get(`/conversations/${id}`);
    return response.data.data;
  }

  async getConversationMessages(id: number, options?: QueryOptions): Promise<PaginatedResponse<Message>> {
    if (this.mockMode) {
      return this.mockPaginatedResponse(this.generateMockMessages(), options?.page, options?.limit);
    }

    const params = new URLSearchParams();
    if (options?.page) params.append('page', options.page.toString());
    if (options?.limit) params.append('limit', options.limit.toString());
    
    const response: AxiosResponse<APIResponse<PaginatedResponse<Message>>> = await this.client.get(`/conversations/${id}/messages?${params}`);
    return response.data.data;
  }

  async createConversation(title?: string): Promise<Conversation> {
    if (this.mockMode) {
      const newConversation: Conversation = {
        id: Date.now(),
        user_id: 1,
        title: title || 'محادثة جديدة',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        is_active: true,
        message_count: 0
      };
      const result = await this.mockResponse(newConversation);
      return result.data;
    }

    const response: AxiosResponse<APIResponse<Conversation>> = await this.client.post('/conversations', { title });
    return response.data.data;
  }

  async updateConversation(id: number, title: string): Promise<Conversation> {
    if (this.mockMode) {
      const updatedConversation: Conversation = {
        id,
        user_id: 1,
        title,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        is_active: true,
        message_count: 0
      };
      const result = await this.mockResponse(updatedConversation);
      return result.data;
    }

    const response: AxiosResponse<APIResponse<Conversation>> = await this.client.patch(`/conversations/${id}`, { title });
    return response.data.data;
  }

  async deleteConversation(id: number): Promise<void> {
    if (this.mockMode) {
      return;
    }

    await this.client.delete(`/conversations/${id}`);
  }

  // Tool Methods
  async getTools(): Promise<Tool[]> {
    if (this.mockMode) {
      const tools: Tool[] = [
        {
          id: 1,
          name: 'web_search',
          description: 'البحث في الويب',
          is_active: true,
          category: 'search',
          parameters: {},
          cost_per_use: 0.01
        },
        {
          id: 2,
          name: 'calculator',
          description: 'الحاسبة',
          is_active: true,
          category: 'utility',
          parameters: {},
          cost_per_use: 0.001
        }
      ];
      const result = await this.mockResponse(tools);
      return result.data;
    }

    const response: AxiosResponse<APIResponse<Tool[]>> = await this.client.get('/tools/active');
    return response.data.data;
  }

  async testTool(id: number, query: string): Promise<any> {
    if (this.mockMode) {
      return this.mockResponse({ result: 'نتيجة تجريبية للأداة' });
    }

    const response: AxiosResponse<APIResponse<any>> = await this.client.post(`/tools/${id}/test`, { query });
    return response.data.data;
  }

  // Model Methods
  async getModels(): Promise<Model[]> {
    if (this.mockMode) {
      const models: Model[] = [
        {
          id: 1,
          name: 'gpt-3.5-turbo',
          provider: 'OpenAI',
          api_endpoint: 'https://api.openai.com/v1/chat/completions',
          api_key_standard: 'openai',
          price_per_million_tokens: 2.0,
          role: 'direct_answer',
          max_tokens: 4000,
          temperature: 0.7,
          is_active: true
        }
      ];
      const result = await this.mockResponse(models);
      return result.data;
    }

    const response: AxiosResponse<APIResponse<Model[]>> = await this.client.get('/models/active');
    return response.data.data;
  }

  async createModel(model: Partial<Model>): Promise<Model> {
    if (this.mockMode) {
      const newModel: Model = {
        id: Date.now(),
        name: model.name || 'new_model',
        provider: model.provider || 'unknown',
        api_endpoint: model.api_endpoint || '',
        api_key_standard: model.api_key_standard || 'openai',
        price_per_million_tokens: model.price_per_million_tokens || 1.0,
        role: model.role || 'direct_answer',
        max_tokens: model.max_tokens || 1000,
        temperature: model.temperature || 0.7,
        is_active: true
      };
      const result = await this.mockResponse(newModel);
      return result.data;
    }

    const response: AxiosResponse<APIResponse<Model>> = await this.client.post('/models/', model);
    return response.data.data;
  }

  // Credit System Methods
  async getUserBalance(): Promise<{ balance: number }> {
    if (this.mockMode) {
      const result = await this.mockResponse({ balance: 1000 });
      return result.data;
    }

    const response: AxiosResponse<APIResponse<{ balance: number }>> = await this.client.get('/credit/balance');
    return response.data.data;
  }

  async getCreditTransactions(options?: QueryOptions): Promise<PaginatedResponse<CreditTransaction>> {
    if (this.mockMode) {
      return this.mockPaginatedResponse(this.generateMockTransactions(), options?.page, options?.limit);
    }

    const params = new URLSearchParams();
    if (options?.page) params.append('page', options.page.toString());
    if (options?.limit) params.append('limit', options.limit.toString());
    if (options?.filters?.date_from) params.append('date_from', options.filters.date_from);
    if (options?.filters?.date_to) params.append('date_to', options.filters.date_to);
    if (options?.filters?.type) params.append('type', options.filters.type);
    if (options?.filters?.status) params.append('status', options.filters.status);
    
    const response: AxiosResponse<APIResponse<PaginatedResponse<CreditTransaction>>> = await this.client.get(`/credit/transactions?${params}`);
    return response.data.data;
  }

  async redeemCreditCode(code: string): Promise<{ balance: number; message: string }> {
    if (this.mockMode) {
      if (code.toUpperCase() === 'DEMO10') {
        const result = await this.mockResponse({
          balance: 1010,
          message: 'تم تطبيق الكود بنجاح! تم إضافة 10 رصيد.'
        });
        return result.data;
      } else if (code.toUpperCase() === 'FREE50') {
        const result = await this.mockResponse({
          balance: 1050,
          message: 'تم تطبيق الكود بنجاح! تم إضافة 50 رصيد مجاناً.'
        });
        return result.data;
      } else {
        throw new Error('كود غير صحيح أو منتهي الصلاحية');
      }
    }

    const response: AxiosResponse<APIResponse<{ balance: number; message: string }>> = await this.client.post('/credit/redeem', { code });
    return response.data.data;
  }

  async initializePayment(request: PaymentInitializationRequest): Promise<PaymentInitializationResponse> {
    if (this.mockMode) {
      const result = await this.mockResponse({
        payment_id: `mock_payment_${Date.now()}`,
        checkout_url: 'https://checkout.stripe.com/demo',
        qr_code: null,
        expires_at: new Date(Date.now() + 3600000).toISOString()
      });
      return result.data;
    }

    const response: AxiosResponse<APIResponse<PaymentInitializationResponse>> = await this.client.post('/credit/payment/initialize', request);
    return response.data.data;
  }

  async completePayment(paymentId: string): Promise<void> {
    if (this.mockMode) {
      return;
    }

    await this.client.post('/credit/payment/complete', { payment_id: paymentId });
  }

  async getCreditStatistics(): Promise<any> {
    if (this.mockMode) {
      return this.mockResponse({
        total_spent: 150.75,
        total_earned: 200.00,
        monthly_usage: 75.50,
        top_transactions: this.generateMockTransactions()
      });
    }

    const response: AxiosResponse<APIResponse<any>> = await this.client.get('/credit/statistics');
    return response.data.data;
  }

  // Health Check
  async getHealth(): Promise<SystemHealth> {
    if (this.mockMode) {
      const result = await this.mockResponse({
        status: 'healthy' as const,
        services: {
          api: true,
          database: true,
          websocket: true
        },
        uptime: 86400,
        version: '1.0.0'
      });
      return result.data;
    }

    const response: AxiosResponse<APIResponse<SystemHealth>> = await this.client.get('/health');
    return response.data.data;
  }

  async getDetailedHealth(): Promise<any> {
    if (this.mockMode) {
      return this.mockResponse({
        system: {
          status: 'healthy',
          uptime: 86400,
          memory_usage: '45%',
          cpu_usage: '23%'
        },
        services: {
          database: { status: 'healthy', response_time: '12ms' },
          cache: { status: 'healthy', response_time: '3ms' },
          websocket: { status: 'healthy', connections: 25 }
        }
      });
    }

    const response: AxiosResponse<APIResponse<any>> = await this.client.get('/health/detailed');
    return response.data.data;
  }

  // File Upload
  async uploadFile(file: File, onProgress?: (progress: number) => void): Promise<{ url: string; filename: string }> {
    if (this.mockMode) {
      // Simulate upload progress
      return new Promise((resolve) => {
        let progress = 0;
        const interval = setInterval(() => {
          progress += 10;
          if (onProgress) {
            onProgress(progress);
          }
          if (progress >= 100) {
            clearInterval(interval);
            resolve({
              url: `https://mock-storage.com/files/${file.name}`,
              filename: file.name
            });
          }
        }, 100);
      });
    }

    const formData = new FormData();
    formData.append('file', file);

    const response: AxiosResponse<APIResponse<{ url: string; filename: string }>> = await this.client.post('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = (progressEvent.loaded / progressEvent.total) * 100;
          onProgress(progress);
        }
      },
    });

    return response.data.data;
  }

  // Statistics and Analytics
  async getUserStatistics(): Promise<any> {
    if (this.mockMode) {
      return this.mockResponse({
        total_messages: 156,
        total_conversations: 12,
        average_response_time: '1.2s',
        favorite_topics: ['الذكاء الاصطناعي', 'البرمجة', 'التكنولوجيا'],
        usage_by_hour: Array.from({ length: 24 }, (_, i) => ({
          hour: i,
          count: Math.floor(Math.random() * 10)
        }))
      });
    }

    const response: AxiosResponse<APIResponse<any>> = await this.client.get('/statistics/user');
    return response.data.data;
  }

  async getSystemStatistics(): Promise<any> {
    if (this.mockMode) {
      return this.mockResponse({
        total_users: 1247,
        active_users_today: 89,
        total_messages_today: 1234,
        system_load: '23%',
        api_response_time: '145ms'
      });
    }

    const response: AxiosResponse<APIResponse<any>> = await this.client.get('/statistics/system');
    return response.data.data;
  }
}

export const apiService = new APIService();