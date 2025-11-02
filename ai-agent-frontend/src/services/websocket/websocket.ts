import { io, Socket } from 'socket.io-client';
import { WebSocketMessage } from '../../types/api';

export interface WebSocketConfig {
  url?: string;
  auth?: {
    token: string;
    userId: number;
  };
  reconnect?: boolean;
  reconnectionAttempts?: number;
  reconnectionDelay?: number;
}

export interface WebSocketEvents {
  connect: () => void;
  disconnect: (reason: string) => void;
  reconnect: (attemptNumber: number) => void;
  error: (error: any) => void;
  message: (data: any) => void;
  typing: (data: { userId: number; isTyping: boolean; conversationId?: number }) => void;
  user_status: (data: { userId: number; status: 'online' | 'offline' | 'away' }) => void;
  conversation_updated: (data: { conversationId: number; changes: any }) => void;
  agent_response: (data: any) => void;
  payment_status: (data: { paymentId: string; status: string }) => void;
  system_notification: (data: { type: string; message: string; data?: any }) => void;
}

class WebSocketService {
  private socket: Socket | null = null;
  private listeners: Map<keyof WebSocketEvents, Function[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectionDelay = 1000;
  private isConnected = false;
  private config: WebSocketConfig;

  constructor(config: WebSocketConfig = {}) {
    this.config = {
      url: config.url || import.meta.env.VITE_WEBSOCKET_URL || 'http://localhost:8000',
      reconnect: config.reconnect !== false,
      reconnectionAttempts: config.reconnectionAttempts || 5,
      reconnectionDelay: config.reconnectionDelay || 1000,
      ...config
    };
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.socket = io(this.config.url!, {
          auth: {
            token: this.config.auth?.token,
            userId: this.config.auth?.userId
          },
          reconnection: this.config.reconnect,
          reconnectionAttempts: this.config.reconnectionAttempts,
          reconnectionDelay: this.config.reconnectionDelay,
          transports: ['websocket', 'polling']
        });

        // Connection events
        this.socket.on('connect', () => {
          console.log('WebSocket connected');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this.emit('connect');
          resolve();
        });

        this.socket.on('disconnect', (reason: string) => {
          console.log('WebSocket disconnected:', reason);
          this.isConnected = false;
          this.emit('disconnect', reason);
        });

        this.socket.on('reconnect', (attemptNumber: number) => {
          console.log('WebSocket reconnected after', attemptNumber, 'attempts');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this.emit('reconnect', attemptNumber);
        });

        this.socket.on('reconnect_failed', () => {
          console.log('WebSocket failed to reconnect');
          this.emit('error', new Error('Failed to reconnect to WebSocket'));
        });

        // Message events
        this.socket.on('message', (data: any) => {
          this.emit('message', data);
        });

        this.socket.on('typing', (data: any) => {
          this.emit('typing', data);
        });

        this.socket.on('user_status', (data: any) => {
          this.emit('user_status', data);
        });

        this.socket.on('conversation_updated', (data: any) => {
          this.emit('conversation_updated', data);
        });

        this.socket.on('agent_response', (data: any) => {
          this.emit('agent_response', data);
        });

        this.socket.on('payment_status', (data: any) => {
          this.emit('payment_status', data);
        });

        this.socket.on('system_notification', (data: any) => {
          this.emit('system_notification', data);
        });

        this.socket.on('error', (error: any) => {
          console.error('WebSocket error:', error);
          this.emit('error', error);
        });

        // Handle connection timeout
        setTimeout(() => {
          if (!this.isConnected) {
            reject(new Error('WebSocket connection timeout'));
          }
        }, 10000);

      } catch (error) {
        reject(error);
      }
    });
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.isConnected = false;
      this.listeners.clear();
    }
  }

  reconnect(): Promise<void> {
    this.disconnect();
    return this.connect();
  }

  on<K extends keyof WebSocketEvents>(event: K, callback: WebSocketEvents[K]): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event)!.push(callback);
  }

  off<K extends keyof WebSocketEvents>(event: K, callback?: WebSocketEvents[K]): void {
    if (!callback) {
      this.listeners.delete(event);
      return;
    }

    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      const index = eventListeners.indexOf(callback);
      if (index > -1) {
        eventListeners.splice(index, 1);
      }
    }
  }

  private emit<K extends keyof WebSocketEvents>(event: K, ...args: Parameters<WebSocketEvents[K]>): void {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.forEach(callback => {
        try {
          callback(...args);
        } catch (error) {
          console.error(`Error in WebSocket event listener for ${event}:`, error);
        }
      });
    }
  }

  // Message sending methods
  sendMessage(message: any): void {
    if (this.socket && this.isConnected) {
      this.socket.emit('message', message);
    } else {
      console.warn('Cannot send message: WebSocket not connected');
    }
  }

  sendTyping(conversationId: number, isTyping: boolean): void {
    if (this.socket && this.isConnected) {
      this.socket.emit('typing', { conversationId, isTyping });
    }
  }

  joinConversation(conversationId: number): void {
    if (this.socket && this.isConnected) {
      this.socket.emit('join_conversation', { conversationId });
    }
  }

  leaveConversation(conversationId: number): void {
    if (this.socket && this.isConnected) {
      this.socket.emit('leave_conversation', { conversationId });
    }
  }

  updateUserStatus(status: 'online' | 'away' | 'offline'): void {
    if (this.socket && this.isConnected) {
      this.socket.emit('user_status', { status });
    }
  }

  requestAgentResponse(data: {
    query: string;
    conversationId?: number;
    stream?: boolean;
  }): void {
    if (this.socket && this.isConnected) {
      this.socket.emit('agent_request', data);
    }
  }

  // Getters
  get connected(): boolean {
    return this.isConnected;
  }

  get socketId(): string | null {
    return this.socket?.id || null;
  }
}

// Singleton instance with default configuration
let defaultWebSocketService: WebSocketService | null = null;

export function getWebSocketService(config?: WebSocketConfig): WebSocketService {
  if (!defaultWebSocketService) {
    defaultWebSocketService = new WebSocketService(config);
  }
  return defaultWebSocketService;
}

export { WebSocketService };