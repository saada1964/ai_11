import React, { useState } from 'react';
import { useAuthStore } from '../store/authStore';
import { useThemeStore, Theme, ColorScheme } from '../store/themeStore';
import { useLanguageStore } from '../store/languageStore';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { 
  User, 
  Lock, 
  Palette, 
  Globe, 
  Bell, 
  Shield, 
  Download, 
  Trash2,
  Moon,
  Sun,
  Monitor,
  Check
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { user, updateUser, logout } = useAuthStore();
  const { theme, colorScheme, fontSize, animationSpeed, compactMode, setTheme, setColorScheme, setFontSize, setAnimationSpeed, setCompactMode } = useThemeStore();
  const { language, setLanguage } = useLanguageStore();
  
  const [activeTab, setActiveTab] = useState<'profile' | 'security' | 'appearance' | 'notifications'>('profile');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleSaveProfile = async (data: any) => {
    setIsLoading(true);
    try {
      await updateUser(data);
      setMessage({ type: 'success', text: language === 'ar' ? 'تم تحديث الملف الشخصي' : 'Profile updated' });
    } catch (error) {
      setMessage({ type: 'error', text: language === 'ar' ? 'فشل في التحديث' : 'Update failed' });
    } finally {
      setIsLoading(false);
      setTimeout(() => setMessage(null), 3000);
    }
  };

  const handleExportData = () => {
    // TODO: Implement data export
    setMessage({ type: 'success', text: language === 'ar' ? 'سيتم تصدير البيانات قريباً' : 'Data export coming soon' });
    setTimeout(() => setMessage(null), 3000);
  };

  const ThemeSettings = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2 rtl:space-x-reverse">
          <Palette className="h-5 w-5" />
          <span>{language === 'ar' ? 'المظهر' : 'Appearance'}</span>
        </CardTitle>
        <CardDescription>
          {language === 'ar' ? 'خصص مظهر التطبيق' : 'Customize the app appearance'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Theme Selection */}
        <div>
          <label className="text-sm font-medium mb-3 block">
            {language === 'ar' ? 'النمط' : 'Theme'}
          </label>
          <div className="grid grid-cols-3 gap-2">
            {[
              { value: 'light', icon: Sun, label: language === 'ar' ? 'فاتح' : 'Light' },
              { value: 'dark', icon: Moon, label: language === 'ar' ? 'مظلم' : 'Dark' },
              { value: 'system', icon: Monitor, label: language === 'ar' ? 'تلقائي' : 'System' }
            ].map(({ value, icon: Icon, label }) => (
              <Button
                key={value}
                variant={theme === value ? 'default' : 'outline'}
                className="flex flex-col items-center space-y-2 h-auto py-4"
                onClick={() => setTheme(value as Theme)}
              >
                <Icon className="h-5 w-5" />
                <span className="text-xs">{label}</span>
                {theme === value && <Check className="h-3 w-3" />}
              </Button>
            ))}
          </div>
        </div>

        {/* Color Scheme */}
        <div>
          <label className="text-sm font-medium mb-3 block">
            {language === 'ar' ? 'لوحة الألوان' : 'Color Scheme'}
          </label>
          <div className="grid grid-cols-4 gap-2">
            {[
              { value: 'blue', label: 'أزرق', color: 'bg-blue-500' },
              { value: 'green', label: 'أخضر', color: 'bg-green-500' },
              { value: 'purple', label: 'بنفسجي', color: 'bg-purple-500' },
              { value: 'orange', label: 'برتقالي', color: 'bg-orange-500' }
            ].map(({ value, label, color }) => (
              <Button
                key={value}
                variant={colorScheme === value ? 'default' : 'outline'}
                className="flex flex-col items-center space-y-2 h-auto py-4"
                onClick={() => setColorScheme(value as ColorScheme)}
              >
                <div className={`w-5 h-5 rounded-full ${color}`} />
                <span className="text-xs">{label}</span>
                {colorScheme === value && <Check className="h-3 w-3" />}
              </Button>
            ))}
          </div>
        </div>

        {/* Font Size */}
        <div>
          <label className="text-sm font-medium mb-3 block">
            {language === 'ar' ? 'حجم الخط' : 'Font Size'}
          </label>
          <div className="grid grid-cols-3 gap-2">
            {[
              { value: 'small', label: language === 'ar' ? 'صغير' : 'Small' },
              { value: 'medium', label: language === 'ar' ? 'متوسط' : 'Medium' },
              { value: 'large', label: language === 'ar' ? 'كبير' : 'Large' }
            ].map(({ value, label }) => (
              <Button
                key={value}
                variant={fontSize === value ? 'default' : 'outline'}
                onClick={() => setFontSize(value as any)}
              >
                {label}
                {fontSize === value && <Check className="h-3 w-3 mr-1" />}
              </Button>
            ))}
          </div>
        </div>

        {/* Animation Speed */}
        <div>
          <label className="text-sm font-medium mb-3 block">
            {language === 'ar' ? 'سرعة الحركة' : 'Animation Speed'}
          </label>
          <div className="grid grid-cols-3 gap-2">
            {[
              { value: 'slow', label: language === 'ar' ? 'بطيء' : 'Slow' },
              { value: 'normal', label: language === 'ar' ? 'عادي' : 'Normal' },
              { value: 'fast', label: language === 'ar' ? 'سريع' : 'Fast' }
            ].map(({ value, label }) => (
              <Button
                key={value}
                variant={animationSpeed === value ? 'default' : 'outline'}
                onClick={() => setAnimationSpeed(value as any)}
              >
                {label}
                {animationSpeed === value && <Check className="h-3 w-3 mr-1" />}
              </Button>
            ))}
          </div>
        </div>

        {/* Compact Mode */}
        <div className="flex items-center justify-between">
          <div>
            <label className="text-sm font-medium">
              {language === 'ar' ? 'الوضع المضغوط' : 'Compact Mode'}
            </label>
            <p className="text-xs text-muted-foreground">
              {language === 'ar' ? 'تقليل المسافات' : 'Reduce spacing'}
            </p>
          </div>
          <Button
            variant={compactMode ? 'default' : 'outline'}
            onClick={() => setCompactMode(!compactMode)}
          >
            {compactMode ? <Check className="h-3 w-3 mr-1" /> : null}
            {compactMode ? language === 'ar' ? 'مفعل' : 'On' : language === 'ar' ? 'معطل' : 'Off'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  const ProfileSettings = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2 rtl:space-x-reverse">
          <User className="h-5 w-5" />
          <span>{language === 'ar' ? 'الملف الشخصي' : 'Profile'}</span>
        </CardTitle>
        <CardDescription>
          {language === 'ar' ? 'إدارة معلوماتك الشخصية' : 'Manage your personal information'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Input
          label={language === 'ar' ? 'اسم المستخدم' : 'Username'}
          defaultValue={user?.username}
          disabled
        />
        <Input
          label={language === 'ar' ? 'البريد الإلكتروني' : 'Email'}
          type="email"
          defaultValue={user?.email}
        />
        <Button onClick={() => handleSaveProfile({})}>
          {language === 'ar' ? 'حفظ التغييرات' : 'Save Changes'}
        </Button>
      </CardContent>
    </Card>
  );

  const LanguageSettings = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2 rtl:space-x-reverse">
          <Globe className="h-5 w-5" />
          <span>{language === 'ar' ? 'اللغة' : 'Language'}</span>
        </CardTitle>
        <CardDescription>
          {language === 'ar' ? 'اختر لغة الواجهة' : 'Choose interface language'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-2">
          <Button
            variant={language === 'ar' ? 'default' : 'outline'}
            onClick={() => setLanguage('ar')}
            className="flex items-center justify-center space-x-2 rtl:space-x-reverse"
          >
            <span>عر</span>
            {language === 'ar' && <Check className="h-3 w-3" />}
          </Button>
          <Button
            variant={language === 'en' ? 'default' : 'outline'}
            onClick={() => setLanguage('en')}
            className="flex items-center justify-center space-x-2 rtl:space-x-reverse"
          >
            <span>EN</span>
            {language === 'en' && <Check className="h-3 w-3" />}
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  const DangerZone = () => (
    <Card className="border-destructive/50">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2 rtl:space-x-reverse text-destructive">
          <Shield className="h-5 w-5" />
          <span>{language === 'ar' ? 'منطقة الخطر' : 'Danger Zone'}</span>
        </CardTitle>
        <CardDescription>
          {language === 'ar' ? 'إجراءات لا يمكن التراجع عنها' : 'Irreversible actions'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button
          variant="outline"
          onClick={handleExportData}
          className="w-full"
        >
          <Download className="h-4 w-4 mr-2" />
          {language === 'ar' ? 'تصدير البيانات' : 'Export Data'}
        </Button>
        <Button
          variant="destructive"
          onClick={logout}
          className="w-full"
        >
          <Trash2 className="h-4 w-4 mr-2" />
          {language === 'ar' ? 'حذف الحساب' : 'Delete Account'}
        </Button>
      </CardContent>
    </Card>
  );

  const tabs = [
    { id: 'profile', icon: User, label: language === 'ar' ? 'الملف الشخصي' : 'Profile' },
    { id: 'appearance', icon: Palette, label: language === 'ar' ? 'المظهر' : 'Appearance' },
    { id: 'notifications', icon: Bell, label: language === 'ar' ? 'الإشعارات' : 'Notifications' },
    { id: 'security', icon: Lock, label: language === 'ar' ? 'الأمان' : 'Security' }
  ];

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">
          {language === 'ar' ? 'الإعدادات' : 'Settings'}
        </h1>
        <p className="text-muted-foreground">
          {language === 'ar' ? 'إدارة تفضيلاتك وحسابك' : 'Manage your preferences and account'}
        </p>
      </div>

      {message && (
        <div className={`p-4 rounded-md mb-6 ${
          message.type === 'success' 
            ? 'bg-green-50 text-green-700 border border-green-200' 
            : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {message.text}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="lg:col-span-1">
          <nav className="space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`w-full flex items-center space-x-3 rtl:space-x-reverse px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    activeTab === tab.id
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content */}
        <div className="lg:col-span-3 space-y-6">
          {activeTab === 'profile' && (
            <>
              <ProfileSettings />
              <LanguageSettings />
            </>
          )}
          {activeTab === 'appearance' && <ThemeSettings />}
          {activeTab === 'notifications' && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2 rtl:space-x-reverse">
                  <Bell className="h-5 w-5" />
                  <span>{language === 'ar' ? 'الإشعارات' : 'Notifications'}</span>
                </CardTitle>
                <CardDescription>
                  {language === 'ar' ? 'إدارة إشعاراتك' : 'Manage your notifications'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">
                  {language === 'ar' ? 'قريباً...' : 'Coming soon...'}
                </p>
              </CardContent>
            </Card>
          )}
          {activeTab === 'security' && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2 rtl:space-x-reverse">
                    <Lock className="h-5 w-5" />
                    <span>{language === 'ar' ? 'كلمة المرور' : 'Password'}</span>
                  </CardTitle>
                  <CardDescription>
                    {language === 'ar' ? 'تغيير كلمة المرور' : 'Change your password'}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Input type="password" label={language === 'ar' ? 'كلمة المرور الحالية' : 'Current password'} />
                  <Input type="password" label={language === 'ar' ? 'كلمة المرور الجديدة' : 'New password'} />
                  <Input type="password" label={language === 'ar' ? 'تأكيد كلمة المرور' : 'Confirm password'} />
                  <Button>{language === 'ar' ? 'تغيير كلمة المرور' : 'Change Password'}</Button>
                </CardContent>
              </Card>
              <DangerZone />
            </>
          )}
        </div>
      </div>
    </div>
  );
};