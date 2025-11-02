import React, { useState, useRef, useEffect } from 'react';
import { useChatStore } from '../../store/chatStore';
import { useLanguageStore } from '../../store/languageStore';
import { Button } from '../ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { 
  Send, 
  Paperclip, 
  Mic, 
  MicOff, 
  Loader2, 
  User, 
  Bot,
  Copy,
  ThumbsUp,
  ThumbsDown,
  Share,
  MoreVertical
} from 'lucide-react';
import { Input } from '../ui/Input';
import { Message } from '../../types/api';

export const ChatArea: React.FC = () => {
  const { 
    currentConversation, 
    messages, 
    isLoading, 
    isTyping, 
    sendMessage,
    error 
  } = useChatStore();
  
  const { language } = useLanguageStore();
  const [inputValue, setInputValue] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const messageContent = inputValue.trim();
    setInputValue('');

    try {
      await sendMessage(messageContent);
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  const toggleRecording = () => {
    setIsRecording(!isRecording);
    // TODO: Implement voice recording functionality
  };

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString(language === 'ar' ? 'ar-SA' : 'en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    // TODO: Show toast notification
  };

  const MessageBubble: React.FC<{ message: Message }> = ({ message }) => {
    const isUser = message.message_type === 'user';
    
    return (
      <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 group`}>
        <div className={`max-w-[70%] ${isUser ? 'order-2' : 'order-1'}`}>
          <div
            className={`rounded-lg p-3 ${
              isUser
                ? 'bg-primary text-primary-foreground ml-4'
                : 'bg-muted text-foreground mr-4'
            }`}
          >
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
            
            {/* Message metadata */}
            <div className="mt-2 text-xs opacity-70 space-y-1">
              <div className="flex items-center justify-between">
                <span>{formatTime(message.created_at)}</span>
                {message.tokens_used && (
                  <span className="text-xs">
                    {message.tokens_used} {language === 'ar' ? 'رمز' : 'tokens'}
                  </span>
                )}
              </div>
              
              {message.model_used && (
                <div className="text-xs">
                  {language === 'ar' ? 'النموذج:' : 'Model:'} {message.model_used}
                </div>
              )}
              
              {message.cost && (
                <div className="text-xs">
                  {language === 'ar' ? 'التكلفة:' : 'Cost:'} ${message.cost.toFixed(4)}
                </div>
              )}
            </div>
          </div>
          
          {/* Message actions */}
          {!isUser && (
            <div className="flex items-center mt-2 space-x-1 rtl:space-x-reverse opacity-0 group-hover:opacity-100 transition-opacity">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => copyToClipboard(message.content)}
                title={language === 'ar' ? 'نسخ' : 'Copy'}
              >
                <Copy className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                title={language === 'ar' ? 'إعجاب' : 'Like'}
              >
                <ThumbsUp className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                title={language === 'ar' ? 'عدم إعجاب' : 'Dislike'}
              >
                <ThumbsDown className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                title={language === 'ar' ? 'مشاركة' : 'Share'}
              >
                <Share className="h-3 w-3" />
              </Button>
            </div>
          )}
        </div>
        
        {/* Avatar */}
        <div className={`flex-shrink-0 ${isUser ? 'order-1 mr-2' : 'order-2 ml-2'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
            isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
          }`}>
            {isUser ? (
              <User className="h-4 w-4" />
            ) : (
              <Bot className="h-4 w-4" />
            )}
          </div>
        </div>
      </div>
    );
  };

  if (!currentConversation) {
    return (
      <div className="flex-1 flex items-center justify-center bg-muted/20">
        <Card className="text-center p-8">
          <CardHeader>
            <CardTitle className="text-xl">
              {language === 'ar' ? 'مرحباً بك!' : 'Welcome!'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">
              {language === 'ar' 
                ? 'ابدأ محادثة جديدة لبدء التفاعل مع وكيل الذكاء الاصطناعي'
                : 'Start a new conversation to begin interacting with the AI agent'
              }
            </p>
            <Button>
              {language === 'ar' ? 'محادثة جديدة' : 'New Conversation'}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-background">
      {/* Chat Header */}
      <div className="border-b p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">{currentConversation.title}</h2>
          <div className="flex items-center space-x-2 rtl:space-x-reverse">
            {isTyping && (
              <div className="flex items-center space-x-1 rtl:space-x-reverse text-sm text-muted-foreground">
                <div className="flex space-x-1 rtl:space-x-reverse">
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
                <span>{language === 'ar' ? 'يكتب...' : 'typing...'}</span>
              </div>
            )}
            <Button variant="ghost" size="icon">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-muted-foreground">
              {language === 'ar' ? 'لا توجد رسائل بعد' : 'No messages yet'}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isTyping && (
              <div className="flex justify-start mb-4">
                <div className="max-w-[70%]">
                  <div className="bg-muted text-foreground rounded-lg p-3 mr-4">
                    <div className="flex items-center space-x-2 rtl:space-x-reverse">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span className="text-sm">
                        {language === 'ar' ? 'يفكر...' : 'Thinking...'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4">
          <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
            {error}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="border-t p-4">
        <form onSubmit={handleSubmit} className="flex items-end space-x-2 rtl:space-x-reverse">
          <div className="flex-1">
            <Input
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={language === 'ar' ? 'اكتب رسالتك هنا...' : 'Type your message...'}
              disabled={isLoading}
              className="resize-none"
            />
          </div>
          
          <div className="flex items-center space-x-1 rtl:space-x-reverse">
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={toggleRecording}
              title={language === 'ar' ? 'تسجيل صوتي' : 'Voice recording'}
            >
              {isRecording ? (
                <MicOff className="h-4 w-4 text-destructive" />
              ) : (
                <Mic className="h-4 w-4" />
              )}
            </Button>
            
            <Button
              type="button"
              variant="outline"
              size="icon"
              title={language === 'ar' ? 'إرفاق ملف' : 'Attach file'}
            >
              <Paperclip className="h-4 w-4" />
            </Button>
            
            <Button
              type="submit"
              disabled={!inputValue.trim() || isLoading}
              loading={isLoading}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};