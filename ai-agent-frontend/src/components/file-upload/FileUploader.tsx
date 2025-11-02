import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { apiService } from '../../services/api/api';
import { Button } from '../ui/Button';
import { Card, CardContent } from '../ui/Card';
import { 
  Upload, 
  File, 
  Image, 
  FileText, 
  Video, 
  Music, 
  X,
  Loader2,
  CheckCircle,
  AlertCircle
} from 'lucide-react';

interface FileUploadProps {
  onFileUploaded?: (file: { url: string; filename: string }) => void;
  onUploadProgress?: (progress: number) => void;
  maxFiles?: number;
  maxSize?: number; // in bytes
  acceptedTypes?: string[];
  className?: string;
}

interface UploadingFile {
  file: File;
  id: string;
  progress: number;
  status: 'uploading' | 'success' | 'error';
  url?: string;
  error?: string;
}

export const FileUploader: React.FC<FileUploadProps> = ({
  onFileUploaded,
  onUploadProgress,
  maxFiles = 5,
  maxSize = 10 * 1024 * 1024, // 10MB
  acceptedTypes = ['image/*', 'application/pdf', 'text/*', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
  className = ''
}) => {
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    setIsUploading(true);
    const newUploadingFiles: UploadingFile[] = acceptedFiles.map(file => ({
      file,
      id: `${file.name}-${Date.now()}`,
      progress: 0,
      status: 'uploading'
    }));

    setUploadingFiles(prev => [...prev, ...newUploadingFiles]);

    // Upload files one by one
    for (const uploadingFile of newUploadingFiles) {
      try {
        const result = await apiService.uploadFile(uploadingFile.file, (progress) => {
          setUploadingFiles(prev => 
            prev.map(uf => 
              uf.id === uploadingFile.id 
                ? { ...uf, progress }
                : uf
            )
          );
          if (onUploadProgress) {
            onUploadProgress(progress);
          }
        });

        setUploadingFiles(prev => 
          prev.map(uf => 
            uf.id === uploadingFile.id 
              ? { ...uf, status: 'success', progress: 100, url: result.url }
              : uf
          )
        );

        if (onFileUploaded) {
          onFileUploaded(result);
        }
      } catch (error: any) {
        setUploadingFiles(prev => 
          prev.map(uf => 
            uf.id === uploadingFile.id 
              ? { ...uf, status: 'error', error: error.message || 'فشل في رفع الملف' }
              : uf
          )
        );
      }
    }

    setIsUploading(false);
  }, [onFileUploaded, onUploadProgress]);

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    maxFiles,
    maxSize,
    multiple: true,
    onDragEnter: () => {},
    onDragLeave: () => {},
    onDragOver: () => {},
    accept: acceptedTypes.reduce((acc, type) => {
      acc[type] = [];
      return acc;
    }, {} as Record<string, string[]>)
  } as any);

  const removeFile = (fileId: string) => {
    setUploadingFiles(prev => prev.filter(uf => uf.id !== fileId));
  };

  const getFileIcon = (file: File) => {
    if (file.type.startsWith('image/')) return <Image className="h-5 w-5" />;
    if (file.type.startsWith('video/')) return <Video className="h-5 w-5" />;
    if (file.type.startsWith('audio/')) return <Music className="h-5 w-5" />;
    if (file.type.includes('pdf') || file.type.includes('document')) return <FileText className="h-5 w-5" />;
    return <File className="h-5 w-5" />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          isDragActive 
            ? 'border-primary bg-primary/10' 
            : 'border-border hover:border-primary/50'
        } ${isUploading ? 'pointer-events-none opacity-50' : ''}`}
      >
        <input {...(getInputProps() as any)} />
        <div className="space-y-4">
          <Upload className="h-12 w-12 mx-auto text-muted-foreground" />
          <div>
            <p className="text-lg font-medium">
              {isDragActive 
                ? 'اترك الملف هنا...' 
                : 'اسحب وأفلت الملفات هنا أو انقر للاختيار'
              }
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              يمكنك رفع حتى {maxFiles} ملف (أقصى حجم: {formatFileSize(maxSize)})
            </p>
          </div>
          {!isUploading && (
            <Button variant="outline" type="button">
              اختر الملفات
            </Button>
          )}
          {isUploading && (
            <div className="flex items-center justify-center space-x-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>جاري الرفع...</span>
            </div>
          )}
        </div>
      </div>

      {/* File Rejection Errors */}
      {fileRejections.length > 0 && (
        <div className="space-y-2">
          {fileRejections.map(({ file, errors }) => (
            <div key={file.name} className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
              <div className="flex items-center space-x-2">
                <AlertCircle className="h-4 w-4 text-destructive" />
                <span className="text-sm font-medium">{file.name}</span>
              </div>
              <ul className="mt-2 text-sm text-destructive">
                {errors.map(error => (
                  <li key={error.code}>
                    {error.code === 'file-too-large' && `الملف كبير جداً (أقصى ${formatFileSize(maxSize)})`}
                    {error.code === 'file-invalid-type' && 'نوع الملف غير مدعوم'}
                    {error.code === 'too-many-files' && `يمكن رفع أقصى ${maxFiles} ملف`}
                    {error.message}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {/* Uploading Files */}
      {uploadingFiles.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium">الملفات المرفوعة:</h4>
          {uploadingFiles.map((uploadingFile) => (
            <Card key={uploadingFile.id} className="p-4">
              <CardContent className="p-0">
                <div className="flex items-center space-x-3">
                  {getFileIcon(uploadingFile.file)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {uploadingFile.file.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatFileSize(uploadingFile.file.size)}
                    </p>
                    
                    {uploadingFile.status === 'uploading' && (
                      <div className="mt-2">
                        <div className="flex items-center justify-between text-xs">
                          <span>{uploadingFile.progress}%</span>
                          <span>جاري الرفع...</span>
                        </div>
                        <div className="w-full bg-muted rounded-full h-2 mt-1">
                          <div 
                            className="bg-primary h-2 rounded-full transition-all duration-300"
                            style={{ width: `${uploadingFile.progress}%` }}
                          />
                        </div>
                      </div>
                    )}
                    
                    {uploadingFile.status === 'success' && (
                      <div className="flex items-center space-x-2 text-green-600 mt-2">
                        <CheckCircle className="h-4 w-4" />
                        <span className="text-xs">تم الرفع بنجاح</span>
                      </div>
                    )}
                    
                    {uploadingFile.status === 'error' && (
                      <div className="flex items-center space-x-2 text-destructive mt-2">
                        <AlertCircle className="h-4 w-4" />
                        <span className="text-xs">{uploadingFile.error}</span>
                      </div>
                    )}
                  </div>
                  
                  {uploadingFile.status !== 'uploading' && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => removeFile(uploadingFile.id)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};