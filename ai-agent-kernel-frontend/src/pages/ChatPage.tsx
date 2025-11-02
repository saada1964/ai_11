import React, { useState, useEffect, useRef } from 'react';
import { Send, User, Bot, Download, Play, Pause, Volume2, Image as ImageIcon, FileText, Clock } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useChatStore } from '../store/chatStore';
import { useAuthStore } from '../store/authStore';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import ChatInput from '../components/chat/ChatInput';
import Layout from '../components/layout/Layout';

interface ChatMessage {
  id: string;
  content: string;
  type: 'text' | 'file' | 'audio' | 'image';
  fileName?: string;
  fileUrl?: string;
  fileSize?: number;
  duration?: number;
  transcript?: string;
  timestamp: Date;
  isUser: boolean;
  isStreaming?: boolean;
}

const ChatPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const { user } = useAuthStore();
  const { 
    conversations, 
    activeConversationId, 
    createConversation, 
    addMessage, 
    updateMessage,
    setActiveConversation 
  } = useChatStore();
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const audioRefs = useRef<{ [key: string]: HTMLAudioElement }>({});

  // التمرير التلقائي للرسائل الجديدة
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // تحميل رسائل المحادثة النشطة
  useEffect(() => {
    if (activeConversationId) {
      const conversation = conversations.find(c => c.id === activeConversationId);
      if (conversation) {
        setMessages(conversation.messages as ChatMessage[]);
      }
    } else {
      setMessages([]);
    }
  }, [activeConversationId, conversations]);

  // إنشاء محادثة جديدة إذا لم تكن موجودة
  const ensureConversation = async () => {
    if (!activeConversationId) {
      const newConversation = await createConversation();
      if (newConversation) {
        setActiveConversation(newConversation.id);
      }
    }
  };

  // إرسال رسالة
  const handleSendMessage = async (message: ChatMessage) => {
    try {
      // إضافة رسالة المستخدم
      const userMessage: ChatMessage = {
        ...message,
        id: Date.now().toString(),
        isUser: true,
        timestamp: new Date()
      };

      await ensureConversation();
      await addMessage(activeConversationId!, userMessage);
      
      // محاكاة رد المساعد (سيتم استبدالها بـ API حقيقي)
      setIsTyping(true);
      
      setTimeout(async () => {
        const aiMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          content: generateAIResponse(message),
          type: 'text',
          isUser: false,
          timestamp: new Date(),
          isStreaming: false
        };

        await addMessage(activeConversationId!, aiMessage);
        setIsTyping(false);
      }, 1500 + Math.random() * 2000);

    } catch (error) {
      console.error('خطأ في إرسال الرسالة:', error);
      setIsTyping(false);
    }
  };

  // توليد رد الذكاء الاصطناعي (محاكاة)
  const generateAIResponse = (userMessage: ChatMessage): string => {
    const responses = [
      t('chatPage.aiResponses.acknowledgment', 'شكراً لك على رسالتك. كيف يمكنني مساعدتك اليوم؟'),
      t('chatPage.aiResponses.help', 'أهلاً وسهلاً! أنا هنا لمساعدتك. ما الذي تحتاج إليه؟'),
      t('chatPage.aiResponses.file', 'تم استلام الملف بنجاح. هل تريد مني تحليل محتواه؟'),
      t('chatPage.aiResponses.audio', 'تم استقبال التسجيل الصوتي. هل تريد مني تحويله إلى نص؟'),
      t('chatPage.aiResponses.image', 'تم接收 الصورة بنجاح. هل تريد مني وصف محتواها؟'),
      t('chatPage.aiResponses.general', 'فهمت رسالتك. دعني أساعدك في ذلك.')
    ];

    if (userMessage.type === 'file') {
      return responses[2];
    } else if (userMessage.type === 'audio') {
      return responses[3];
    } else if (userMessage.type === 'image') {
      return responses[4];
    }

    return responses[Math.floor(Math.random() * responses.length)];
  };

  // تشغيل/إيقاف الصوت
  const toggleAudio = (messageId: string, audioUrl: string) => {
    const audio = audioRefs.current[messageId];
    if (audio) {
      if (audio.paused) {
        audio.play();
      } else {
        audio.pause();
      }
    } else {
      const newAudio = new Audio(audioUrl);
      audioRefs.current[messageId] = newAudio;
      newAudio.play();
    }
  };

  // تنزيل الملف
  const downloadFile = (fileUrl: string, fileName: string) => {
    const link = document.createElement('a');
    link.href = fileUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // تنسيق الوقت
  const formatTime = (date: Date): string => {
    return date.toLocaleTimeString(i18n.language, { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  // تنسيق حجم الملف
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // عرض الرسالة
  const renderMessage = (message: ChatMessage) => {
    const isUser = message.isUser;
    
    return (
      <div key={message.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
        <div className={`flex ${isUser ? 'flex-row-reverse' : 'flex-row'} items-start space-x-3 max-w-[80%]`}>
          {/* أيقونة المستخدم */}
          <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
            isUser 
              ? 'bg-blue-600 text-white' 
              : 'bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300'
          }`}>
            {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
          </div>

          {/* محتوى الرسالة */}
          <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
            <div className={`px-4 py-2 rounded-lg max-w-full ${
              isUser 
                ? 'bg-blue-600 text-white rounded-br-none' 
                : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-bl-none'
            }`}>
              {/* محتوى الرسالة */}
              {message.type === 'text' && (
                <p className="whitespace-pre-wrap break-words">{message.content}</p>
              )}

              {/* ملف */}
              {message.type === 'file' && (
                <div className="flex items-center space-x-3">
                  <FileText className="w-5 h-5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{message.fileName}</p>
                    {message.fileSize && (
                      <p className="text-sm opacity-80">
                        {formatFileSize(message.fileSize)}
                      </p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => downloadFile(message.fileUrl!, message.fileName!)}
                    className="p-1"
                  >
                    <Download className="w-4 h-4" />
                  </Button>
                </div>
              )}

              {/* صوت */}
              {message.type === 'audio' && (
                <div className="space-y-2">
                  <div className="flex items-center space-x-3">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleAudio(message.id, message.fileUrl!)}
                      className="p-2 text-white hover:bg-white/20"
                    >
                      <Volume2 className="w-4 h-4" />
                    </Button>
                    <div className="flex-1">
                      <p className="text-sm opacity-80">
                        {t('chatPage.audioMessage', 'رسالة صوتية')}
                      </p>
                      {message.fileSize && (
                        <p className="text-xs opacity-60">
                          {formatFileSize(message.fileSize)}
                        </p>
                      )}
                    </div>
                  </div>
                  {message.transcript && (
                    <div className="bg-white/10 rounded p-2 mt-2">
                      <p className="text-xs opacity-80">
                        {t('chatPage.transcript', 'النص المحول:')} {message.transcript}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* صورة */}
              {message.type === 'image' && (
                <div className="space-y-2">
                  <div className="relative group">
                    <img
                      src={message.fileUrl}
                      alt={message.fileName}
                      className="max-w-full h-auto rounded max-h-64 object-cover"
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => downloadFile(message.fileUrl!, message.fileName!)}
                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-black/50 text-white hover:bg-black/70"
                    >
                      <Download className="w-4 h-4" />
                    </Button>
                  </div>
                  {message.fileSize && (
                    <p className="text-xs opacity-60">
                      {formatFileSize(message.fileSize)}
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* الوقت */}
            <div className={`flex items-center mt-1 space-x-1 text-xs text-gray-500 dark:text-gray-400 ${
              isUser ? 'flex-row-reverse' : 'flex-row'
            }`}>
              <Clock className="w-3 h-3" />
              <span>{formatTime(message.timestamp)}</span>
              {message.isStreaming && (
                <span className="animate-pulse">
                  {t('chatPage.typing', 'يكتب...')}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <Layout>
      <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900">
        {/* رأس الصفحة */}
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                {t('chatPage.title', 'المحادثة')}
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {t('chatPage.subtitle', 'تحدث مع مساعد الذكاء الاصطناعي')}
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {t('chatPage.online', 'متصل')}
              </span>
            </div>
          </div>
        </div>

        {/* منطقة الرسائل */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <Bot className="w-16 h-16 text-gray-400 dark:text-gray-600 mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
                {t('chatPage.welcome', 'مرحباً بك!')}
              </h2>
              <p className="text-gray-600 dark:text-gray-400 max-w-md">
                {t('chatPage.welcomeMessage', 'ابدأ محادثة جديدة أو أرسل ملفاً أو رسالة صوتية. أنا هنا لمساعدتك!')}
              </p>
            </div>
          ) : (
            <>
              {messages.map(renderMessage)}
              {isTyping && (
                <div className="flex justify-start mb-4">
                  <div className="flex items-center space-x-3 max-w-[80%]">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-600 flex items-center justify-center">
                      <Bot className="w-4 h-4 text-gray-600 dark:text-gray-300" />
                    </div>
                    <div className="bg-gray-100 dark:bg-gray-700 rounded-lg rounded-bl-none px-4 py-2">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* منطقة الإدخال */}
        <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
          <ChatInput
            onSendMessage={handleSendMessage}
            disabled={isTyping}
            placeholder={t('chatPage.inputPlaceholder', 'اكتب رسالتك أو استخدم الأزرار لإرفاق ملف...')}
            maxFileSize={10 * 1024 * 1024} // 10MB
            supportedFormats={['pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'mp4', 'mp3', 'wav', 'webm']}
          />
        </div>
      </div>
    </Layout>
  );
};

export default ChatPage;