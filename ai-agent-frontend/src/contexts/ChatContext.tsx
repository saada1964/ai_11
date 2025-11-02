import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import type { Conversation, Message, StreamMessage, AgentRequest } from '../types';
import { apiService } from '../services/api';
import { useApp } from './AppContext';

interface ChatContextType {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: Message[];
  loading: boolean;
  streaming: boolean;
  streamingMessage: string;
  error: string | null;
  loadConversations: () => Promise<void>;
  loadConversation: (conversationId: number) => Promise<void>;
  createNewConversation: (title?: string) => Promise<Conversation | null>;
  sendMessage: (content: string, files?: File[]) => Promise<void>;
  deleteConversation: (conversationId: number) => Promise<void>;
  setCurrentConversation: (conversation: Conversation | null) => void;
  clearError: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { user } = useApp();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const [error, setError] = useState<string | null>(null);

  const loadConversations = useCallback(async () => {
    if (!user) return;
    
    try {
      setLoading(true);
      const data = await apiService.getConversations(user.id);
      setConversations(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'فشل تحميل المحادثات');
    } finally {
      setLoading(false);
    }
  }, [user]);

  const loadConversation = useCallback(async (conversationId: number) => {
    if (!user) return;

    try {
      setLoading(true);
      const [conversation, messagesData] = await Promise.all([
        apiService.getConversation(conversationId),
        apiService.getConversationMessages(conversationId),
      ]);
      
      setCurrentConversation(conversation);
      setMessages(messagesData.messages);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'فشل تحميل المحادثة');
    } finally {
      setLoading(false);
    }
  }, [user]);

  const createNewConversation = useCallback(async (title?: string): Promise<Conversation | null> => {
    if (!user) return null;

    try {
      setLoading(true);
      const conversation = await apiService.createConversation(user.id, title);
      setConversations((prev) => [conversation, ...prev]);
      setCurrentConversation(conversation);
      setMessages([]);
      setError(null);
      return conversation;
    } catch (err: any) {
      setError(err.message || 'فشل إنشاء محادثة جديدة');
      return null;
    } finally {
      setLoading(false);
    }
  }, [user]);

  const sendMessage = useCallback(async (content: string, files?: File[]) => {
    if (!user) return;

    try {
      // Create conversation if none exists
      let conversation = currentConversation;
      if (!conversation) {
        conversation = await createNewConversation();
        if (!conversation) return;
      }

      // Add user message immediately
      const userMessage: Message = {
        role: 'user',
        content,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Prepare request
      const request: AgentRequest = {
        query: content,
        user_id: user.id,
        conversation_id: conversation.id,
      };

      // Start streaming
      setStreaming(true);
      setStreamingMessage('');

      const eventSource = apiService.getEventSource(request);
      let fullResponse = '';

      eventSource.onmessage = (event) => {
        if (event.data === '[DONE]') {
          eventSource.close();
          setStreaming(false);
          
          // Add assistant message
          const assistantMessage: Message = {
            role: 'assistant',
            content: fullResponse,
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, assistantMessage]);
          setStreamingMessage('');
          
          // Reload conversation to update message count
          if (conversation) {
            apiService.getConversation(conversation.id).then(setCurrentConversation);
          }
          return;
        }

        try {
          const data: StreamMessage = JSON.parse(event.data);
          
          if (data.type === 'chunk' && data.content) {
            fullResponse += data.content;
            setStreamingMessage(fullResponse);
          } else if (data.type === 'complete' && data.response) {
            fullResponse = data.response;
            setStreamingMessage(fullResponse);
          } else if (data.type === 'error') {
            setError(data.error || 'حدث خطأ');
            eventSource.close();
            setStreaming(false);
          }
        } catch (err) {
          console.error('Error parsing stream data:', err);
        }
      };

      eventSource.onerror = (err) => {
        console.error('EventSource error:', err);
        setError('فشل الاتصال بالخادم');
        eventSource.close();
        setStreaming(false);
      };
      
    } catch (err: any) {
      setError(err.message || 'فشل إرسال الرسالة');
      setStreaming(false);
    }
  }, [user, currentConversation, createNewConversation]);

  const deleteConversation = useCallback(async (conversationId: number) => {
    try {
      setLoading(true);
      await apiService.deleteConversation(conversationId);
      setConversations((prev) => prev.filter((c) => c.id !== conversationId));
      
      if (currentConversation?.id === conversationId) {
        setCurrentConversation(null);
        setMessages([]);
      }
      
      setError(null);
    } catch (err: any) {
      setError(err.message || 'فشل حذف المحادثة');
    } finally {
      setLoading(false);
    }
  }, [currentConversation]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value: ChatContextType = {
    conversations,
    currentConversation,
    messages,
    loading,
    streaming,
    streamingMessage,
    error,
    loadConversations,
    loadConversation,
    createNewConversation,
    sendMessage,
    deleteConversation,
    setCurrentConversation,
    clearError,
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within ChatProvider');
  }
  return context;
};

export default ChatContext;
