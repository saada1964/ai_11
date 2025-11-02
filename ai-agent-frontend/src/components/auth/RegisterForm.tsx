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

const registerSchema = z.object({
  username: z.string().min(3, 'اسم المستخدم يجب أن يكون 3 أحرف على الأقل'),
  email: z.string().email('البريد الإلكتروني غير صحيح'),
  password: z.string().min(8, 'كلمة المرور يجب أن تكون 8 أحرف على الأقل'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'كلمتا المرور غير متطابقتان',
  path: ['confirmPassword'],
});

type RegisterFormData = z.infer<typeof registerSchema>;

export const RegisterForm: React.FC = () => {
  const { register: registerUser, isLoading, error, clearError } = useAuthStore();
  const { language } = useLanguageStore();
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    try {
      await registerUser({
        username: data.username,
        email: data.email,
        password: data.password,
        confirm_password: data.confirmPassword,
      });
      navigate('/chat');
    } catch (error) {
      // Error is handled by the store
    }
  };

  React.useEffect(() => {
    return () => clearError();
  }, [clearError]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-muted/20 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">
            {language === 'ar' ? 'إنشاء حساب جديد' : 'Create Account'}
          </CardTitle>
          <CardDescription>
            {language === 'ar' 
              ? 'أنشئ حسابك الجديد للبدء في استخدام النظام' 
              : 'Create your new account to start using the system'
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
              {...register('email')}
              type="email"
              label={language === 'ar' ? 'البريد الإلكتروني' : 'Email'}
              placeholder={language === 'ar' ? 'أدخل البريد الإلكتروني' : 'Enter email'}
              icon={<Mail className="h-4 w-4" />}
              error={errors.email?.message}
              autoComplete="email"
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
              autoComplete="new-password"
            />

            <Input
              {...register('confirmPassword')}
              type={showConfirmPassword ? 'text' : 'password'}
              label={language === 'ar' ? 'تأكيد كلمة المرور' : 'Confirm Password'}
              placeholder={language === 'ar' ? 'أعد إدخال كلمة المرور' : 'Confirm password'}
              icon={<Lock className="h-4 w-4" />}
              rightIcon={
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              }
              error={errors.confirmPassword?.message}
              autoComplete="new-password"
            />

            <Button
              type="submit"
              className="w-full"
              loading={isLoading}
              disabled={isLoading}
            >
              {language === 'ar' ? 'إنشاء الحساب' : 'Create Account'}
            </Button>
          </form>

          <div className="text-center text-sm text-muted-foreground">
            {language === 'ar' ? (
              <>
                لديك حساب بالفعل؟{' '}
                <a href="/login" className="text-primary hover:underline">
                  تسجيل الدخول
                </a>
              </>
            ) : (
              <>
                Already have an account?{' '}
                <a href="/login" className="text-primary hover:underline">
                  Login here
                </a>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};