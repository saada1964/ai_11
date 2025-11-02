import React from 'react';
import { useAuthStore } from '../../store/authStore';
import { useThemeStore } from '../../store/themeStore';
import { useLanguageStore } from '../../store/languageStore';
import { Button } from '../ui/Button';
import { Moon, Sun, Monitor, Globe, User, LogOut, Settings } from 'lucide-react';

interface HeaderProps {
  onSettingsClick?: () => void;
  onProfileClick?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onSettingsClick, onProfileClick }) => {
  const { user, logout } = useAuthStore();
  const { theme, setTheme } = useThemeStore();
  const { language, setLanguage } = useLanguageStore();

  const toggleTheme = () => {
    if (theme === 'light') {
      setTheme('dark');
    } else if (theme === 'dark') {
      setTheme('system');
    } else {
      setTheme('light');
    }
  };

  const toggleLanguage = () => {
    setLanguage(language === 'ar' ? 'en' : 'ar');
  };

  const getThemeIcon = () => {
    switch (theme) {
      case 'light':
        return <Sun className="h-4 w-4" />;
      case 'dark':
        return <Moon className="h-4 w-4" />;
      default:
        return <Monitor className="h-4 w-4" />;
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center">
        {/* Logo/Brand */}
        <div className="mr-4 hidden md:flex">
          <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            {language === 'ar' ? 'نواة وكيل الذكاء الاصطناعي' : 'AI Agent Kernel'}
          </h1>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* User Menu */}
        <div className="flex items-center space-x-2 rtl:space-x-reverse">
          {/* Theme Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            className="h-9 w-9"
            title={theme === 'light' ? 'Switch to dark mode' : 
                   theme === 'dark' ? 'Switch to system theme' : 'Switch to light mode'}
          >
            {getThemeIcon()}
          </Button>

          {/* Language Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleLanguage}
            className="h-9 w-9"
            title={language === 'ar' ? 'Switch to English' : 'التبديل للعربية'}
          >
            <Globe className="h-4 w-4" />
            <span className="sr-only">
              {language === 'ar' ? 'Switch to English' : 'التبديل للعربية'}
            </span>
            <span className="ml-1 text-xs font-medium">
              {language === 'ar' ? 'EN' : 'عر'}
            </span>
          </Button>

          {/* Settings */}
          {onSettingsClick && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onSettingsClick}
              className="h-9 w-9"
              title="Settings"
            >
              <Settings className="h-4 w-4" />
            </Button>
          )}

          {/* User Menu */}
          <div className="flex items-center space-x-2 rtl:space-x-reverse">
            <span className="text-sm text-muted-foreground hidden sm:inline">
              {user?.username}
            </span>
            
            <Button
              variant="ghost"
              size="icon"
              onClick={onProfileClick}
              className="h-9 w-9"
              title="Profile"
            >
              <User className="h-4 w-4" />
            </Button>

            <Button
              variant="ghost"
              size="icon"
              onClick={handleLogout}
              className="h-9 w-9"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
};