import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuthStore } from '../../store/authStore';
import { useLanguageStore } from '../../store/languageStore';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/Card';
import { Eye, EyeOff, User, Lock, Mail } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const loginSchema = z.object({
  username: z.string().min(3, 'اسم المستخدم يجب أن يكون 3 أحرف على الأقل'),
  password: z.string().min(8, 'كلمة المرور يجب أن تكون 8 أحرف على الأقل'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export const LoginForm: React.FC = () => {
  const { login, isLoading, error, clearError } = useAuthStore();
  const { language } = useLanguageStore();
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    try {
      await login({ username: data.username, password: data.password });
      navigate('/chat');
    } catch (error) {
      // Error is handled by the store
    }
  };

  const handleDemoLogin = async () => {
    try {
      await login({
        username: 'demo',
        password: 'demo123'
      });
      navigate('/chat');
    } catch (error) {
      console.error('Demo login failed:', error);
    }
  };

  React.useEffect(() => {
    // Clear error when component mounts or form changes
    return () => clearError();
  }, [clearError]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-muted/20 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">
            {language === 'ar' ? 'تسجيل الدخول' : 'Login'}
          </CardTitle>
          <CardDescription>
            {language === 'ar' 
              ? 'أدخل بياناتك للوصول إلى حسابك' 
              : 'Enter your credentials to access your account'
            }
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {error && (
            <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              {...register('username')}
              label={language === 'ar' ? 'اسم المستخدم' : 'Username'}
              placeholder={language === 'ar' ? 'أدخل اسم المستخدم' : 'Enter username'}
              icon={<User className="h-4 w-4" />}
              error={errors.username?.message}
              autoComplete="username"
            />

            <Input
              {...register('password')}
              type={showPassword ? 'text' : 'password'}
              label={language === 'ar' ? 'كلمة المرور' : 'Password'}
              placeholder={language === 'ar' ? 'أدخل كلمة المرور' : 'Enter password'}
              icon={<Lock className="h-4 w-4" />}
              rightIcon={
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              }
              error={errors.password?.message}
              autoComplete="current-password"
            />

            <Button
              type="submit"
              className="w-full"
              loading={isLoading}
              disabled={isLoading}
            >
              {language === 'ar' ? 'تسجيل الدخول' : 'Login'}
            </Button>
          </form>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">
                {language === 'ar' ? 'أو' : 'Or'}
              </span>
            </div>
          </div>

          <Button
            variant="outline"
            className="w-full"
            onClick={handleDemoLogin}
            disabled={isLoading}
          >
            <User className="mr-2 h-4 w-4" />
            {language === 'ar' ? 'مستخدم تجريبي' : 'Demo User'}
          </Button>

          <div className="text-center text-sm text-muted-foreground">
            {language === 'ar' ? (
              <>
                ليس لديك حساب؟{' '}
                <a href="/register" className="text-primary hover:underline">
                  إنشاء حساب جديد
                </a>
              </>
            ) : (
              <>
                Don't have an account?{' '}
                <a href="/register" className="text-primary hover:underline">
                  Create new account
                </a>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};