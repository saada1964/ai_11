import React, { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Play, Pause, Square, Trash2, Download, Volume2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

interface AudioRecorderProps {
  onRecordingComplete?: (audioBlob: Blob, transcript?: string) => void;
  onRecordingStart?: () => void;
  onRecordingStop?: () => void;
  maxDuration?: number; // في الثواني
  language?: string;
  className?: string;
}

interface AudioRecordingState {
  isRecording: boolean;
  isPaused: boolean;
  duration: number;
  audioUrl: string | null;
  audioBlob: Blob | null;
  transcript: string;
  isPlaying: boolean;
}

const AudioRecorder: React.FC<AudioRecorderProps> = ({
  onRecordingComplete,
  onRecordingStart,
  onRecordingStop,
  maxDuration = 300, // 5 دقائق كحد أقصى
  language = 'ar-SA',
  className = ''
}) => {
  const { t } = useTranslation();
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [state, setState] = useState<AudioRecordingState>({
    isRecording: false,
    isPaused: false,
    duration: 0,
    audioUrl: null,
    audioBlob: null,
    transcript: '',
    isPlaying: false
  });

  // بدء التسجيل
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
      });
      
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const audioUrl = URL.createObjectURL(audioBlob);
        
        let transcript = '';
        try {
          // محاولة تحويل الصوت إلى نص إذا كان مدعوماً
          if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            transcript = await transcribeAudio(audioBlob);
          }
        } catch (error) {
          console.warn('فشل تحويل الصوت إلى نص:', error);
        }

        setState(prev => ({
          ...prev,
          audioBlob,
          audioUrl,
          transcript,
          isRecording: false,
          isPaused: false
        }));

        onRecordingComplete?.(audioBlob, transcript);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start(100); // جمع البيانات كل 100ms
      startTimer();
      
      setState(prev => ({
        ...prev,
        isRecording: true,
        isPaused: false,
        duration: 0,
        audioUrl: null,
        audioBlob: null,
        transcript: ''
      }));

      onRecordingStart?.();
    } catch (error) {
      console.error('خطأ في بدء التسجيل:', error);
      alert('لا يمكن الوصول إلى الميكروفون. يرجى التحقق من الأذونات.');
    }
  };

  // إيقاف التسجيل مؤقتاً
  const pauseRecording = () => {
    if (mediaRecorderRef.current && state.isRecording) {
      if (state.isPaused) {
        mediaRecorderRef.current.resume();
        startTimer();
        setState(prev => ({ ...prev, isPaused: false }));
      } else {
        mediaRecorderRef.current.pause();
        stopTimer();
        setState(prev => ({ ...prev, isPaused: true }));
      }
    }
  };

  // إيقاف التسجيل نهائياً
  const stopRecording = () => {
    if (mediaRecorderRef.current && state.isRecording) {
      mediaRecorderRef.current.stop();
      stopTimer();
      onRecordingStop?.();
    }
  };

  // بدء المؤقت
  const startTimer = () => {
    intervalRef.current = setInterval(() => {
      setState(prev => {
        const newDuration = prev.duration + 1;
        if (newDuration >= maxDuration) {
          stopRecording();
          return { ...prev, duration: maxDuration };
        }
        return { ...prev, duration: newDuration };
      });
    }, 1000);
  };

  // إيقاف المؤقت
  const stopTimer = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  // تنظيف الموارد عند إلغاء المكون
  useEffect(() => {
    return () => {
      stopTimer();
      if (state.audioUrl) {
        URL.revokeObjectURL(state.audioUrl);
      }
      if (mediaRecorderRef.current && state.isRecording) {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  // تحويل الصوت إلى نص
  const transcribeAudio = (audioBlob: Blob): Promise<string> => {
    return new Promise((resolve, reject) => {
      const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
      
      if (!SpeechRecognition) {
        reject(new Error('Speech recognition not supported'));
        return;
      }

      const recognition = new SpeechRecognition();
      recognition.lang = language;
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      const audioURL = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioURL);

      audio.onloadeddata = () => {
        recognition.onresult = (event: any) => {
          const transcript = event.results[0][0].transcript;
          resolve(transcript);
          URL.revokeObjectURL(audioURL);
        };

        recognition.onerror = (event: any) => {
          reject(new Error(event.error));
          URL.revokeObjectURL(audioURL);
        };

        recognition.start();
        audio.play();
      };

      audio.onerror = () => {
        reject(new Error('فشل تحميل الصوت'));
        URL.revokeObjectURL(audioURL);
      };
    });
  };

  // تشغيل الصوت المسجل
  const playAudio = () => {
    if (state.audioUrl && audioRef.current) {
      if (state.isPlaying) {
        audioRef.current.pause();
        setState(prev => ({ ...prev, isPlaying: false }));
      } else {
        audioRef.current.play();
        setState(prev => ({ ...prev, isPlaying: true }));
      }
    }
  };

  // حذف التسجيل
  const deleteRecording = () => {
    if (state.audioUrl) {
      URL.revokeObjectURL(state.audioUrl);
    }
    setState({
      isRecording: false,
      isPaused: false,
      duration: 0,
      audioUrl: null,
      audioBlob: null,
      transcript: '',
      isPlaying: false
    });
  };

  // تنزيل الصوت
  const downloadAudio = () => {
    if (state.audioBlob && state.audioUrl) {
      const link = document.createElement('a');
      link.href = state.audioUrl;
      link.download = `recording_${new Date().toISOString().slice(0, 19)}.webm`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  // تنسيق الوقت
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // إعادة التسجيل
  const reRecord = () => {
    deleteRecording();
    startRecording();
  };

  return (
    <Card className={`p-6 ${className}`}>
      <div className="space-y-6">
        {/* عنوان المكون */}
        <div className="text-center">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {t('audioRecorder.title', 'تسجيل صوتي')}
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {t('audioRecorder.description', 'اضغط لبدء التسجيل الصوتي')}
          </p>
        </div>

        {/* واجهة التسجيل */}
        <div className="flex flex-col items-center space-y-4">
          {/* مؤشر التسجيل البصري */}
          <div className="relative">
            <div className={`w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 ${
              state.isRecording 
                ? state.isPaused 
                  ? 'bg-yellow-500 animate-pulse' 
                  : 'bg-red-500 animate-pulse scale-110' 
                : 'bg-gray-200 dark:bg-gray-700'
            }`}>
              {state.isRecording ? (
                state.isPaused ? (
                  <Mic className="w-8 h-8 text-white" />
                ) : (
                  <MicOff className="w-8 h-8 text-white" />
                )
              ) : (
                <Mic className="w-8 h-8 text-gray-500 dark:text-gray-400" />
              )}
            </div>
            
            {/* تأثير الموجات الصوتية عند التسجيل */}
            {state.isRecording && !state.isPaused && (
              <div className="absolute inset-0 rounded-full">
                <div className="absolute inset-0 rounded-full bg-red-500 animate-ping opacity-75"></div>
                <div className="absolute inset-2 rounded-full bg-red-500 animate-pulse opacity-50"></div>
              </div>
            )}
          </div>

          {/* عرض الوقت */}
          <div className="text-center">
            <div className={`text-2xl font-mono font-bold ${
              state.duration >= maxDuration * 0.9 
                ? 'text-red-600 dark:text-red-400' 
                : 'text-gray-900 dark:text-gray-100'
            }`}>
              {formatTime(state.duration)}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              {t('audioRecorder.maxDuration', 'الحد الأقصى: {{duration}}', { 
                duration: formatTime(maxDuration) 
              })}
            </div>
          </div>

          {/* أزرار التحكم */}
          <div className="flex items-center space-x-4">
            {!state.isRecording && !state.audioUrl && (
              <Button
                onClick={startRecording}
                className="bg-red-600 hover:bg-red-700 text-white px-6 py-3"
              >
                <Mic className="w-5 h-5 ml-2" />
                {t('audioRecorder.start', 'بدء التسجيل')}
              </Button>
            )}

            {state.isRecording && (
              <>
                <Button
                  onClick={pauseRecording}
                  variant="outline"
                  className="px-4 py-2"
                >
                  {state.isPaused ? (
                    <>
                      <Play className="w-4 h-4 ml-2" />
                      {t('audioRecorder.resume', 'متابعة')}
                    </>
                  ) : (
                    <>
                      <Pause className="w-4 h-4 ml-2" />
                      {t('audioRecorder.pause', 'إيقاف مؤقت')}
                    </>
                  )}
                </Button>

                <Button
                  onClick={stopRecording}
                  variant="outline"
                  className="px-4 py-2"
                >
                  <Square className="w-4 h-4 ml-2" />
                  {t('audioRecorder.stop', 'إيقاف')}
                </Button>
              </>
            )}
          </div>
        </div>

        {/* معاينة التسجيل */}
        {state.audioUrl && (
          <div className="space-y-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            {/* مشغل الصوت */}
            <div className="flex items-center space-x-4">
              <Button
                onClick={playAudio}
                variant="outline"
                className="px-4 py-2"
              >
                {state.isPlaying ? (
                  <Pause className="w-4 h-4 ml-2" />
                ) : (
                  <Play className="w-4 h-4 ml-2" />
                )}
                {state.isPlaying ? 
                  t('audioRecorder.pause', 'إيقاف مؤقت') : 
                  t('audioRecorder.play', 'تشغيل')
                }
              </Button>

              <div className="flex-1">
                <audio
                  ref={audioRef}
                  src={state.audioUrl}
                  onEnded={() => setState(prev => ({ ...prev, isPlaying: false }))}
                  className="hidden"
                />
              </div>

              <div className="flex items-center space-x-2">
                <Button
                  onClick={downloadAudio}
                  variant="outline"
                  className="px-3 py-2"
                  title={t('audioRecorder.download', 'تنزيل')}
                >
                  <Download className="w-4 h-4" />
                </Button>

                <Button
                  onClick={deleteRecording}
                  variant="outline"
                  className="px-3 py-2 text-red-600 hover:text-red-700"
                  title={t('audioRecorder.delete', 'حذف')}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>

                <Button
                  onClick={reRecord}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-2"
                  title={t('audioRecorder.reRecord', 'إعادة التسجيل')}
                >
                  <Mic className="w-4 h-4 ml-1" />
                  {t('audioRecorder.reRecord', 'إعادة التسجيل')}
                </Button>
              </div>
            </div>

            {/* النص المحول */}
            {state.transcript && (
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <Volume2 className="w-4 h-4 text-blue-600" />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {t('audioRecorder.transcript', 'النص المحول:')}
                  </span>
                </div>
                <div className="p-3 bg-white dark:bg-gray-700 rounded border">
                  <p className="text-sm text-gray-800 dark:text-gray-200">
                    {state.transcript}
                  </p>
                </div>
              </div>
            )}

            {/* معلومات الملف */}
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {t('audioRecorder.recordingInfo', 'المدة: {{duration}} | الحجم: {{size}}', {
                duration: formatTime(state.duration),
                size: state.audioBlob ? `${(state.audioBlob.size / 1024).toFixed(1)} KB` : 'غير محدد'
              })}
            </div>
          </div>
        )}

        {/* شريط التقدم */}
        {state.isRecording && (
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div 
              className="bg-red-600 h-2 rounded-full transition-all duration-1000"
              style={{ 
                width: `${(state.duration / maxDuration) * 100}%` 
              }}
            />
          </div>
        )}
      </div>
    </Card>
  );
};

export default AudioRecorder;