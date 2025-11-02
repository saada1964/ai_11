import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Camera, CameraOff, RotateCcw, Download, Trash2, Check, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

interface ImageCaptureProps {
  onCaptureComplete?: (imageBlob: Blob, imageUrl: string) => void;
  onCaptureStart?: () => void;
  onCaptureStop?: () => void;
  maxWidth?: number;
  maxHeight?: number;
  quality?: number; // 0.1 to 1.0
  format?: 'jpeg' | 'png' | 'webp';
  className?: string;
}

interface ImageCaptureState {
  isCapturing: boolean;
  stream: MediaStream | null;
  capturedImage: string | null;
  capturedBlob: Blob | null;
  error: string | null;
  facingMode: 'user' | 'environment'; // كاميرا أمامية أو خلفية
}

const ImageCapture: React.FC<ImageCaptureProps> = ({
  onCaptureComplete,
  onCaptureStart,
  onCaptureStop,
  maxWidth = 1920,
  maxHeight = 1080,
  quality = 0.8,
  format = 'jpeg',
  className = ''
}) => {
  const { t } = useTranslation();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [state, setState] = useState<ImageCaptureState>({
    isCapturing: false,
    stream: null,
    capturedImage: null,
    capturedBlob: null,
    error: null,
    facingMode: 'user'
  });

  // بدء تشغيل الكاميرا
  const startCamera = useCallback(async (facingMode: 'user' | 'environment' = 'user') => {
    try {
      setState(prev => ({ ...prev, error: null }));

      const constraints = {
        video: {
          facingMode,
          width: { ideal: maxWidth },
          height: { ideal: maxHeight }
        },
        audio: false
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      
      setState(prev => ({
        ...prev,
        stream,
        facingMode,
        isCapturing: true
      }));

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }

      onCaptureStart?.();
    } catch (error) {
      console.error('خطأ في تشغيل الكاميرا:', error);
      setState(prev => ({
        ...prev,
        error: t('imageCapture.cameraError', 'لا يمكن الوصول إلى الكاميرا. يرجى التحقق من الأذونات.')
      }));
    }
  }, [maxWidth, maxHeight, onCaptureStart, t]);

  // إيقاف الكاميرا
  const stopCamera = useCallback(() => {
    if (state.stream) {
      state.stream.getTracks().forEach(track => track.stop());
    }
    
    setState(prev => ({
      ...prev,
      stream: null,
      isCapturing: false
    }));

    onCaptureStop?.();
  }, [state.stream, onCaptureStop]);

  // تبديل الكاميرا (أمامية/خلفية)
  const toggleCamera = useCallback(async () => {
    const newFacingMode = state.facingMode === 'user' ? 'environment' : 'user';
    
    if (state.isCapturing) {
      stopCamera();
      setTimeout(() => startCamera(newFacingMode), 100);
    }
  }, [state.facingMode, state.isCapturing, stopCamera, startCamera]);

  // التقاط الصورة
  const captureImage = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');

    if (!context) return;

    // ضبط أبعاد الكانفاس
    const aspectRatio = video.videoWidth / video.videoHeight;
    let canvasWidth = video.videoWidth;
    let canvasHeight = video.videoHeight;

    // تصغير الصورة إذا كانت أكبر من الحد الأقصى
    if (canvasWidth > maxWidth) {
      canvasWidth = maxWidth;
      canvasHeight = canvasWidth / aspectRatio;
    }
    if (canvasHeight > maxHeight) {
      canvasHeight = maxHeight;
      canvasWidth = canvasHeight * aspectRatio;
    }

    canvas.width = canvasWidth;
    canvas.height = canvasHeight;

    // رسم الصورة على الكانفاس
    context.drawImage(video, 0, 0, canvasWidth, canvasHeight);

    // تحويل إلى blob
    canvas.toBlob(
      (blob) => {
        if (blob) {
          const imageUrl = URL.createObjectURL(blob);
          setState(prev => ({
            ...prev,
            capturedImage: imageUrl,
            capturedBlob: blob
          }));
          
          onCaptureComplete?.(blob, imageUrl);
        }
      },
      `image/${format}`,
      quality
    );
  }, [maxWidth, maxHeight, quality, format, onCaptureComplete]);

  // حذف الصورة الملتقطة
  const deleteCapture = useCallback(() => {
    if (state.capturedImage) {
      URL.revokeObjectURL(state.capturedImage);
    }
    
    setState(prev => ({
      ...prev,
      capturedImage: null,
      capturedBlob: null
    }));
  }, [state.capturedImage]);

  // تنزيل الصورة
  const downloadImage = useCallback(() => {
    if (state.capturedBlob && state.capturedImage) {
      const link = document.createElement('a');
      link.href = state.capturedImage;
      link.download = `captured_image_${new Date().toISOString().slice(0, 19)}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  }, [state.capturedBlob, state.capturedImage, format]);

  // تنظيف الموارد عند إلغاء المكون
  useEffect(() => {
    return () => {
      if (state.stream) {
        state.stream.getTracks().forEach(track => track.stop());
      }
      if (state.capturedImage) {
        URL.revokeObjectURL(state.capturedImage);
      }
    };
  }, [state.stream, state.capturedImage]);

  return (
    <Card className={`p-6 ${className}`}>
      <div className="space-y-6">
        {/* عنوان المكون */}
        <div className="text-center">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {t('imageCapture.title', 'التقاط صورة')}
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {t('imageCapture.description', 'استخدم الكاميرا لالتقاط صورة')}
          </p>
        </div>

        {/* منطقة عرض الكاميرا/الصورة */}
        <div className="relative">
          <div className="relative bg-gray-900 rounded-lg overflow-hidden" style={{ aspectRatio: '4/3' }}>
            {state.isCapturing && !state.capturedImage && (
              <video
                ref={videoRef}
                className="w-full h-full object-cover"
                autoPlay
                playsInline
                muted
              />
            )}

            {state.capturedImage && (
              <img
                src={state.capturedImage}
                alt={t('imageCapture.capturedImage', 'صورة ملتقطة')}
                className="w-full h-full object-cover"
              />
            )}

            {!state.isCapturing && !state.capturedImage && (
              <div className="flex items-center justify-center h-full">
                <div className="text-center text-gray-400">
                  <Camera className="w-16 h-16 mx-auto mb-4" />
                  <p className="text-lg">
                    {t('imageCapture.ready', 'جاهز للتقاط الصورة')}
                  </p>
                </div>
              </div>
            )}

            {/* مؤشر التحميل */}
            {state.isCapturing && !state.capturedImage && (
              <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center">
                <div className="bg-white dark:bg-gray-800 rounded-lg p-4">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                    {t('imageCapture.loading', 'جاري تشغيل الكاميرا...')}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* أزرار التحكم في الكاميرا */}
          {state.isCapturing && !state.capturedImage && (
            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex items-center space-x-4">
              <Button
                onClick={toggleCamera}
                variant="outline"
                className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm p-3 rounded-full"
                title={t('imageCapture.toggleCamera', 'تبديل الكاميرا')}
              >
                <RotateCcw className="w-5 h-5" />
              </Button>

              <Button
                onClick={captureImage}
                className="bg-blue-600 hover:bg-blue-700 text-white p-4 rounded-full shadow-lg"
                title={t('imageCapture.capture', 'التقاط')}
              >
                <Camera className="w-6 h-6" />
              </Button>

              <Button
                onClick={stopCamera}
                variant="outline"
                className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm p-3 rounded-full"
                title={t('imageCapture.stop', 'إيقاف')}
              >
                <CameraOff className="w-5 h-5" />
              </Button>
            </div>
          )}

          {/* أزرار التحكم في الصورة الملتقطة */}
          {state.capturedImage && (
            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex items-center space-x-3">
              <Button
                onClick={deleteCapture}
                variant="outline"
                className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm p-3 rounded-full text-red-600 hover:text-red-700"
                title={t('imageCapture.delete', 'حذف')}
              >
                <Trash2 className="w-5 h-5" />
              </Button>

              <Button
                onClick={downloadImage}
                variant="outline"
                className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm p-3 rounded-full"
                title={t('imageCapture.download', 'تنزيل')}
              >
                <Download className="w-5 h-5" />
              </Button>

              <Button
                onClick={() => {
                  deleteCapture();
                  startCamera(state.facingMode);
                }}
                className="bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-full"
                title={t('imageCapture.retake', 'إعادة التقاط')}
              >
                <RotateCcw className="w-5 h-5" />
              </Button>
            </div>
          )}
        </div>

        {/* بدء تشغيل الكاميرا */}
        {!state.isCapturing && !state.capturedImage && (
          <div className="text-center space-y-4">
            <Button
              onClick={() => startCamera('user')}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3"
            >
              <Camera className="w-5 h-5 ml-2" />
              {t('imageCapture.startFrontCamera', 'الكاميرا الأمامية')}
            </Button>

            <Button
              onClick={() => startCamera('environment')}
              variant="outline"
              className="px-6 py-3"
            >
              <Camera className="w-5 h-5 ml-2" />
              {t('imageCapture.startBackCamera', 'الكاميرا الخلفية')}
            </Button>
          </div>
        )}

        {/* رسائل الخطأ */}
        {state.error && (
          <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <div className="flex items-center space-x-2">
              <X className="w-5 h-5 text-red-600" />
              <p className="text-red-800 dark:text-red-400 text-sm">
                {state.error}
              </p>
            </div>
          </div>
        )}

        {/* معلومات الصورة */}
        {state.capturedBlob && (
          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg space-y-2">
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {t('imageCapture.imageInfo', 'معلومات الصورة:')}
            </h4>
            <div className="grid grid-cols-2 gap-4 text-xs text-gray-600 dark:text-gray-400">
              <div>
                <span className="font-medium">
                  {t('imageCapture.format', 'التنسيق:')}
                </span>
                <br />
                {format.toUpperCase()}
              </div>
              <div>
                <span className="font-medium">
                  {t('imageCapture.quality', 'الجودة:')}
                </span>
                <br />
                {Math.round(quality * 100)}%
              </div>
              <div>
                <span className="font-medium">
                  {t('imageCapture.size', 'الحجم:')}
                </span>
                <br />
                {(state.capturedBlob.size / 1024).toFixed(1)} KB
              </div>
              <div>
                <span className="font-medium">
                  {t('imageCapture.camera', 'الكاميرا:')}
                </span>
                <br />
                {state.facingMode === 'user' ? 
                  t('imageCapture.front', 'أمامية') : 
                  t('imageCapture.back', 'خلفية')
                }
              </div>
            </div>
          </div>
        )}

        {/* Canvas مخفي لمعالجة الصورة */}
        <canvas ref={canvasRef} className="hidden" />
      </div>
    </Card>
  );
};

export default ImageCapture;