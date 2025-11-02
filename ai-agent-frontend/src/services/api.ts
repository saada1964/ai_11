import axios, { AxiosInstance, AxiosError } from 'axios';
import { API_CONFIG, STORAGE_KEYS } from '../config/constants';
import type {
  User,
  Conversation,
  Message,
  AgentRequest,
  AgentResponse,
  CreditCode,
  CreditTransaction,
  PaymentMethod,
  APIResponse,
} from '../types';

class APIService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: API_CONFIG.HEADERS,
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem(STORAGE_KEYS.TOKEN);
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          localStorage.removeItem(STORAGE_KEYS.TOKEN);
          localStorage.removeItem(STORAGE_KEYS.USER);
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Health check
  async healthCheck() {
    const response = await this.client.get('/health');
    return response.data;
  }

  // Agent endpoints
  async invokeAgent(request: AgentRequest): Promise<AgentResponse> {
    const response = await this.client.post('/agent/invoke', request);
    return response.data;
  }

  // Get event source for streaming
  getEventSource(request: AgentRequest): EventSource {
    const token = localStorage.getItem(STORAGE_KEYS.TOKEN);
    const params = new URLSearchParams({
      query: request.query,
      user_id: request.user_id.toString(),
      ...(request.conversation_id && { conversation_id: request.conversation_id.toString() }),
      ...(token && { token }),
    });
    
    return new EventSource(`${API_CONFIG.BASE_URL}/agent/invoke-stream?${params}`);
  }

  // Conversations
  async getConversations(userId: number, limit = 20, offset = 0): Promise<Conversation[]> {
    const response = await this.client.get('/conversations', {
      params: { user_id: userId, limit, offset },
    });
    return response.data;
  }

  async getConversation(conversationId: number): Promise<Conversation> {
    const response = await this.client.get(`/conversations/${conversationId}`);
    return response.data;
  }

  async createConversation(userId: number, title?: string): Promise<Conversation> {
    const response = await this.client.post('/conversations', {
      user_id: userId,
      title: title || 'محادثة جديدة',
    });
    return response.data;
  }

  async updateConversation(conversationId: number, data: Partial<Conversation>): Promise<Conversation> {
    const response = await this.client.put(`/conversations/${conversationId}`, data);
    return response.data;
  }

  async deleteConversation(conversationId: number): Promise<void> {
    await this.client.delete(`/conversations/${conversationId}`);
  }

  async getConversationMessages(
    conversationId: number,
    limit = 50,
    offset = 0
  ): Promise<{ messages: Message[]; has_more: boolean }> {
    const response = await this.client.get(`/conversations/${conversationId}/messages`, {
      params: { limit, offset },
    });
    return response.data;
  }

  // Credit System
  async getUserBalance(userId: number): Promise<{ balance: number; user_id: number }> {
    const response = await this.client.get(`/credit/balance/${userId}`);
    return response.data;
  }

  async redeemCreditCode(code: string, userId: number): Promise<APIResponse> {
    const response = await this.client.post('/credit/codes/redeem', {
      code,
      user_id: userId,
    });
    return response.data;
  }

  async getUserTransactions(
    userId: number,
    page = 1,
    perPage = 20
  ): Promise<{ transactions: CreditTransaction[]; total: number }> {
    const response = await this.client.get('/credit/transactions', {
      params: { user_id: userId, page, per_page: perPage },
    });
    return response.data;
  }

  async getPaymentMethods(): Promise<PaymentMethod[]> {
    const response = await this.client.get('/credit/payment-methods');
    return response.data;
  }

  async initializePayment(
    userId: number,
    amount: number,
    paymentMethod: string
  ): Promise<APIResponse> {
    const response = await this.client.post('/credit/payments/initialize', {
      user_id: userId,
      amount_usd: amount,
      payment_method: paymentMethod,
    });
    return response.data;
  }

  // File upload
  async uploadFile(file: File): Promise<{ url: string; name: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.client.post('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  // Audio transcription
  async transcribeAudio(audioBlob: Blob): Promise<{ text: string }> {
    const formData = new FormData();
    formData.append('audio', audioBlob);

    const response = await this.client.post('/audio/transcribe', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }
}

export const apiService = new APIService();
export default apiService;
