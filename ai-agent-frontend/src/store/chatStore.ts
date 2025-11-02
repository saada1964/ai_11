import { create } from 'zustand';
import { Conversation, Message, AgentRequest } from '../types/api';
import { apiService } from '../services/api/api';

interface ChatState {
  // Current state
  currentConversation: Conversation | null;
  conversations: Conversation[];
  messages: Message[];
  
  // UI state
  isLoading: boolean;
  isTyping: boolean;
  error: string | null;
  
  // WebSocket state
  isConnected: boolean;
  typingUsers: Map<number, boolean>; // userId -> isTyping
  
  // Actions
  loadConversations: () => Promise<void>;
  loadConversation: (id: number) => Promise<void>;
  createConversation: (title?: string) => Promise<void>;
  deleteConversation: (id: number) => Promise<void>;
  renameConversation: (id: number, title: string) => Promise<void>;
  sendMessage: (content: string, conversationId?: number) => Promise<void>;
  sendAgentRequest: (request: AgentRequest) => Promise<void>;
  clearMessages: () => void;
  setCurrentConversation: (conversation: Conversation | null) => void;
  setIsTyping: (isTyping: boolean) => void;
  updateTypingUser: (userId: number, isTyping: boolean) => void;
  setConnected: (connected: boolean) => void;
  clearError: () => void;
  
  // Local utilities
  getCurrentMessages: () => Message[];
  getConversationById: (id: number) => Conversation | undefined;
}

export const useChatStore = create<ChatState>((set, get) => ({
  // Initial state
  currentConversation: null,
  conversations: [],
  messages: [],
  isLoading: false,
  isTyping: false,
  error: null,
  isConnected: false,
  typingUsers: new Map(),

  // Load conversations
  loadConversations: async () => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await apiService.getConversations();
      set({
        conversations: response.items,
        isLoading: false
      });
    } catch (error: any) {
      console.error('Failed to load conversations:', error);
      set({
        isLoading: false,
        error: error.response?.data?.message || error.message || 'فشل في تحميل المحادثات'
      });
    }
  },

  // Load specific conversation with messages
  loadConversation: async (id: number) => {
    set({ isLoading: true, error: null });
    
    try {
      const [conversation, messagesResponse] = await Promise.all([
        apiService.getConversation(id),
        apiService.getConversationMessages(id)
      ]);
      
      set({
        currentConversation: conversation,
        messages: messagesResponse.items,
        isLoading: false
      });
    } catch (error: any) {
      console.error('Failed to load conversation:', error);
      set({
        isLoading: false,
        error: error.response?.data?.message || error.message || 'فشل في تحميل المحادثة'
      });
    }
  },

  // Create new conversation
  createConversation: async (title?: string) => {
    set({ isLoading: true, error: null });
    
    try {
      const conversation = await apiService.createConversation(title);
      
      set(state => ({
        conversations: [conversation, ...state.conversations],
        currentConversation: conversation,
        messages: [],
        isLoading: false
      }));
      
      console.log('Created new conversation:', conversation.id);
    } catch (error: any) {
      console.error('Failed to create conversation:', error);
      set({
        isLoading: false,
        error: error.response?.data?.message || error.message || 'فشل في إنشاء المحادثة'
      });
      throw error;
    }
  },

  // Delete conversation
  deleteConversation: async (id: number) => {
    try {
      await apiService.deleteConversation(id);
      
      set(state => {
        const updatedConversations = state.conversations.filter(c => c.id !== id);
        const isCurrentConversation = state.currentConversation?.id === id;
        
        return {
          conversations: updatedConversations,
          currentConversation: isCurrentConversation ? null : state.currentConversation,
          messages: isCurrentConversation ? [] : state.messages
        };
      });
      
      console.log('Deleted conversation:', id);
    } catch (error: any) {
      console.error('Failed to delete conversation:', error);
      set({ error: error.response?.data?.message || error.message || 'فشل في حذف المحادثة' });
      throw error;
    }
  },

  // Rename conversation
  renameConversation: async (id: number, title: string) => {
    try {
      const updatedConversation = await apiService.updateConversation(id, title);
      
      set(state => ({
        conversations: state.conversations.map(c => 
          c.id === id ? updatedConversation : c
        ),
        currentConversation: state.currentConversation?.id === id 
          ? updatedConversation 
          : state.currentConversation
      }));
      
      console.log('Renamed conversation:', id, 'to:', title);
    } catch (error: any) {
      console.error('Failed to rename conversation:', error);
      set({ error: error.response?.data?.message || error.message || 'فشل في إعادة تسمية المحادثة' });
      throw error;
    }
  },

  // Send message
  sendMessage: async (content: string, conversationId?: number) => {
    const state = get();
    const targetConversationId = conversationId || state.currentConversation?.id;
    
    if (!targetConversationId) {
      set({ error: 'لا توجد محادثة نشطة' });
      return;
    }

    // Add user message to local state immediately for better UX
    const userMessage: Message = {
      id: Date.now(), // Temporary ID
      conversation_id: targetConversationId,
      user_id: 0, // Will be updated by server
      content,
      message_type: 'user',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    set(state => ({
      messages: [...state.messages, userMessage]
    }));

    // Set typing indicator
    get().setIsTyping(true);

    try {
      const agentRequest: AgentRequest = {
        query: content,
        user_id: 0, // Will be updated by server
        conversation_id: targetConversationId,
        stream: false
      };

      const response = await apiService.invokeAgent(agentRequest);
      
      // Add assistant response
      const assistantMessage: Message = {
        id: Date.now() + 1, // Temporary ID
        conversation_id: targetConversationId,
        user_id: 0, // Assistant message
        content: response.response,
        message_type: 'assistant',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        tokens_used: response.tokens_used,
        cost: response.cost,
        model_used: response.model_used,
        tools_used: response.tools_used
      };

      set(state => ({
        messages: [...state.messages, assistantMessage],
        isTyping: false
      }));

      console.log('Message sent and response received');
    } catch (error: any) {
      console.error('Failed to send message:', error);
      set(state => ({
        isTyping: false,
        error: error.response?.data?.message || error.message || 'فشل في إرسال الرسالة'
      }));
      throw error;
    }
  },

  // Send agent request (for advanced features)
  sendAgentRequest: async (request: AgentRequest) => {
    get().setIsTyping(true);

    try {
      const response = await apiService.invokeAgent(request);
      
      set(state => ({
        messages: [...state.messages, {
          id: Date.now(),
          conversation_id: request.conversation_id || 0,
          user_id: 0,
          content: response.response,
          message_type: 'assistant',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          tokens_used: response.tokens_used,
          cost: response.cost,
          model_used: response.model_used,
          tools_used: response.tools_used
        }],
        isTyping: false
      }));

      console.log('Agent request completed');
    } catch (error: any) {
      console.error('Failed to send agent request:', error);
      set({
        isTyping: false,
        error: error.response?.data?.message || error.message || 'فشل في معالجة الطلب'
      });
      throw error;
    }
  },

  // Clear all messages
  clearMessages: () => {
    set({ messages: [] });
  },

  // Set current conversation
  setCurrentConversation: (conversation: Conversation | null) => {
    set({ currentConversation: conversation });
  },

  // Set typing indicator
  setIsTyping: (isTyping: boolean) => {
    set({ isTyping });
  },

  // Update typing user status
  updateTypingUser: (userId: number, isTyping: boolean) => {
    set(state => {
      const newTypingUsers = new Map(state.typingUsers);
      if (isTyping) {
        newTypingUsers.set(userId, true);
      } else {
        newTypingUsers.delete(userId);
      }
      return { typingUsers: newTypingUsers };
    });
  },

  // Set connection status
  setConnected: (connected: boolean) => {
    set({ isConnected: connected });
  },

  // Clear error
  clearError: () => {
    set({ error: null });
  },

  // Utilities
  getCurrentMessages: () => {
    return get().messages;
  },

  getConversationById: (id: number) => {
    return get().conversations.find(c => c.id === id);
  }
}));