import React, { useState, useRef, useCallback } from 'react';
import { Send, Paperclip, Mic, Camera, Smile, X, FileText, Image as ImageIcon, Volume2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Card } from '../ui/Card';
import { FileUploader } from '../file-upload/FileUploader';
import AudioRecorder from '../audio/AudioRecorder';
import ImageCapture from '../image/ImageCapture';

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
  isUser: boolean; // مطلوب ليكون متوافق مع ChatPage
  isStreaming?: boolean;
}

interface ChatInputProps {
  onSendMessage: (message: ChatMessage) => Promise<void> | void;
  disabled?: boolean;
  placeholder?: string;
  maxFileSize?: number; // بايت
  supportedFormats?: string[];
  className?: string;
}

type InputMode = 'text' | 'file' | 'audio' | 'camera';

const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  disabled = false,
  placeholder,
  maxFileSize = 10 * 1024 * 1024, // 10MB
  supportedFormats = ['pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'mp4', 'mp3', 'wav', 'webm'],
  className = ''
}) => {
  const { t } = useTranslation();
  const [inputMode, setInputMode] = useState<InputMode>('text');
  const [message, setMessage] = useState('');
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [isExpanded, setIsExpanded] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // تنظيف النص
  const cleanMessage = (text: string): string => {
    return text.replace(/\s+/g, ' ').trim();
  };

  // إرسال الرسالة النصية
  const sendTextMessage = useCallback(() => {
    const cleanedMessage = cleanMessage(message);
    if (!cleanedMessage || disabled) return;

    const chatMessage: ChatMessage = {
      id: Date.now().toString(),
      content: cleanedMessage,
      type: 'text',
      timestamp: new Date(),
      isUser: true
    };

    onSendMessage(chatMessage);
    setMessage('');
    setIsExpanded(false);
    
    // إعادة تصغير الـ textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [message, disabled, onSendMessage]);

  // إرسال الملفات
  const sendFiles = useCallback((files: File[]) => {
    const newFiles = [...attachedFiles, ...files];
    setAttachedFiles(newFiles);

    files.forEach(file => {
      const isImage = file.type.startsWith('image/');
      const isAudio = file.type.startsWith('audio/');
      
      let messageType: ChatMessage['type'] = 'file';
      if (isImage) messageType = 'image';
      else if (isAudio) messageType = 'audio';

      const chatMessage: ChatMessage = {
        id: `${Date.now()}-${Math.random()}`,
        content: file.name,
        type: messageType,
        fileName: file.name,
        fileUrl: URL.createObjectURL(file),
        fileSize: file.size,
        timestamp: new Date(),
        isUser: true
      };

      onSendMessage(chatMessage);
    });

    setAttachedFiles([]);
    setInputMode('text');
  }, [attachedFiles, onSendMessage]);

  // إرسال التسجيل الصوتي
  const handleAudioRecording = useCallback((audioBlob: Blob, transcript?: string) => {
    const audioUrl = URL.createObjectURL(audioBlob);
    
    const chatMessage: ChatMessage = {
      id: Date.now().toString(),
      content: transcript || t('chatInput.voiceMessage', 'رسالة صوتية'),
      type: 'audio',
      fileName: `recording_${new Date().toISOString().slice(0, 19)}.webm`,
      fileUrl: audioUrl,
      fileSize: audioBlob.size,
      transcript,
      timestamp: new Date(),
      isUser: true
    };

    onSendMessage(chatMessage);
    setInputMode('text');
  }, [onSendMessage, t]);

  // إرسال الصورة الملتقطة
  const handleImageCapture = useCallback((imageBlob: Blob, imageUrl: string) => {
    const chatMessage: ChatMessage = {
      id: Date.now().toString(),
      content: t('chatInput.capturedImage', 'صورة ملتقطة'),
      type: 'image',
      fileName: `captured_image_${new Date().toISOString().slice(0, 19)}.jpeg`,
      fileUrl: imageUrl,
      fileSize: imageBlob.size,
      timestamp: new Date(),
      isUser: true
    };

    onSendMessage(chatMessage);
    setInputMode('text');
  }, [onSendMessage, t]);

  // إزالة الملف المرفق
  const removeAttachedFile = useCallback((index: number) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  // تعديل ارتفاع الـ textarea
  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const maxHeight = 120; // 5 أسطر تقريباً
      textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`;
    }
  }, []);

  // معالجة تغيير النص
  const handleMessageChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    adjustTextareaHeight();
  }, [adjustTextareaHeight]);

  // معالجة الضغط على Enter
  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (attachedFiles.length > 0) {
        sendFiles(attachedFiles);
      } else {
        sendTextMessage();
      }
    }
  }, [attachedFiles, sendFiles, sendTextMessage]);

  // تبديل وضع الإدخال
  const switchMode = useCallback((mode: InputMode) => {
    setInputMode(mode);
    setIsExpanded(mode !== 'text');
  }, []);

  // إغلاق النافذة الموسعة
  const closeExpanded = useCallback(() => {
    setInputMode('text');
    setIsExpanded(false);
    setAttachedFiles([]);
  }, []);

  // الحصول على أيقونة نوع الملف
  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext || '')) {
      return <ImageIcon className="w-4 h-4" />;
    } else if (['mp3', 'wav', 'webm', 'ogg'].includes(ext || '')) {
      return <Volume2 className="w-4 h-4" />;
    } else {
      return <FileText className="w-4 h-4" />;
    }
  };

  // تنسيق حجم الملف
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // عرض واجهة الإدخال حسب الوضع
  const renderInputMode = () => {
    switch (inputMode) {
      case 'file':
        return (
          <FileUploader
            onFileUploaded={(file) => {
              // تحويل إلى ملف فارغة للتوافق مع sendFiles
              const fileList = [new File([], file.filename, { type: 'application/octet-stream' })];
              sendFiles(fileList);
            }}
            maxFiles={10}
            maxSize={maxFileSize}
            acceptedTypes={supportedFormats.map(format => `.${format}`)}
            className="w-full"
          />
        );

      case 'audio':
        return (
          <AudioRecorder
            onRecordingComplete={handleAudioRecording}
            maxDuration={300}
            language="ar-SA"
            className="w-full"
          />
        );

      case 'camera':
        return (
          <ImageCapture
            onCaptureComplete={handleImageCapture}
            maxWidth={1920}
            maxHeight={1080}
            quality={0.8}
            className="w-full"
          />
        );

      default:
        return (
          <div className="space-y-4">
            {/* منطقة النص */}
            <div className="relative">
              <textarea
                ref={textareaRef}
                value={message}
                onChange={handleMessageChange}
                onKeyPress={handleKeyPress}
                placeholder={placeholder || t('chatInput.placeholder', 'اكتب رسالتك...')}
                disabled={disabled}
                className="w-full min-h-[50px] max-h-[120px] p-3 pr-12 border border-gray-300 dark:border-gray-600 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                style={{ height: 'auto' }}
              />
              
              {/* زر الرموز التعبيرية */}
              <Button
                variant="ghost"
                size="sm"
                className="absolute right-2 top-2 p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                title={t('chatInput.emoji', 'رموز تعبيرية')}
              >
                <Smile className="w-4 h-4" />
              </Button>
            </div>

            {/* الملفات المرفقة */}
            {attachedFiles.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('chatInput.attachedFiles', 'الملفات المرفقة ({{count}})', { count: attachedFiles.length })}
                </p>
                <div className="grid grid-cols-1 gap-2">
                  {attachedFiles.map((file, index) => (
                    <div key={index} className="flex items-center space-x-3 p-2 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="flex-shrink-0">
                        {getFileIcon(file.name)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                          {file.name}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {formatFileSize(file.size)}
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeAttachedFile(index)}
                        className="text-red-600 hover:text-red-700 p-1"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
    }
  };

  return (
    <div className={`border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 ${className}`}>
      {isExpanded && (
        <div className="border-b border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {inputMode === 'file' && t('chatInput.uploadFiles', 'رفع الملفات')}
              {inputMode === 'audio' && t('chatInput.recordAudio', 'التسجيل الصوتي')}
              {inputMode === 'camera' && t('chatInput.captureImage', 'التقاط صورة')}
            </h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={closeExpanded}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
        </div>
      )}

      <div className="p-4">
        {renderInputMode()}
      </div>

      {!isExpanded && (
        <div className="border-t border-gray-200 dark:border-gray-700 px-4 py-3">
          <div className="flex items-center justify-between">
            {/* أزرار الوسائط */}
            <div className="flex items-center space-x-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => switchMode('file')}
                disabled={disabled}
                className="text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
                title={t('chatInput.attachFile', 'إرفاق ملف')}
              >
                <Paperclip className="w-5 h-5" />
              </Button>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => switchMode('audio')}
                disabled={disabled}
                className="text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
                title={t('chatInput.recordVoice', 'تسجيل صوتي')}
              >
                <Mic className="w-5 h-5" />
              </Button>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => switchMode('camera')}
                disabled={disabled}
                className="text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
                title={t('chatInput.takePhoto', 'التقاط صورة')}
              >
                <Camera className="w-5 h-5" />
              </Button>
            </div>

            {/* زر الإرسال */}
            <div className="flex items-center space-x-3">
              {attachedFiles.length > 0 && (
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {attachedFiles.length} {t('chatInput.files', 'ملف')}
                </span>
              )}
              
              <Button
                onClick={attachedFiles.length > 0 ? () => sendFiles(attachedFiles) : sendTextMessage}
                disabled={disabled || (attachedFiles.length === 0 && !message.trim())}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2"
              >
                <Send className="w-4 h-4 ml-2" />
                {t('chatInput.send', 'إرسال')}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatInput;