import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '../../lib/utils';
import { useLanguageStore } from '../../store/languageStore';
import { useChatStore } from '../../store/chatStore';
import { Button } from '../ui/Button';
import { 
  MessageSquare, 
  CreditCard, 
  Settings, 
  Home,
  BarChart3,
  Users,
  FileText
} from 'lucide-react';

interface SidebarProps {
  className?: string;
  isOpen?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ className, isOpen = true, onClose }) => {
  const location = useLocation();
  const { language } = useLanguageStore();
  const { conversations } = useChatStore();

  const navigation = [
    {
      name: language === 'ar' ? 'الرئيسية' : 'Home',
      href: '/',
      icon: Home,
      current: location.pathname === '/'
    },
    {
      name: language === 'ar' ? 'المحادثة' : 'Chat',
      href: '/chat',
      icon: MessageSquare,
      current: location.pathname.startsWith('/chat')
    },
    {
      name: language === 'ar' ? 'الإحصائيات' : 'Analytics',
      href: '/dashboard',
      icon: BarChart3,
      current: location.pathname.startsWith('/dashboard')
    },
    {
      name: language === 'ar' ? 'الرصيد' : 'Credits',
      href: '/credit',
      icon: CreditCard,
      current: location.pathname.startsWith('/credit')
    },
    {
      name: language === 'ar' ? 'الملفات' : 'Files',
      href: '/files',
      icon: FileText,
      current: location.pathname.startsWith('/files')
    },
    {
      name: language === 'ar' ? 'الجماعة' : 'Community',
      href: '/community',
      icon: Users,
      current: location.pathname.startsWith('/community')
    }
  ];

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && onClose && (
        <div 
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <div
        className={cn(
          'fixed inset-y-0 right-0 z-50 w-64 bg-background border-l transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0',
          isOpen ? 'translate-x-0' : 'translate-x-full',
          className
        )}
      >
        <div className="flex flex-col h-full">
          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2">
            <div className="space-y-1">
              {navigation.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    onClick={onClose}
                    className={cn(
                      'flex items-center space-x-3 rtl:space-x-reverse px-3 py-2 text-sm font-medium rounded-md transition-colors',
                      item.current
                        ? 'bg-primary text-primary-foreground'
                        : 'text-foreground/60 hover:text-foreground hover:bg-accent'
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </div>

            {/* Recent Conversations */}
            {conversations.length > 0 && (
              <div className="pt-6">
                <h3 className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  {language === 'ar' ? 'المحادثات الأخيرة' : 'Recent Conversations'}
                </h3>
                <div className="mt-2 space-y-1">
                  {conversations.slice(0, 5).map((conversation) => (
                    <Link
                      key={conversation.id}
                      to={`/chat/${conversation.id}`}
                      onClick={onClose}
                      className="flex items-center space-x-3 rtl:space-x-reverse px-3 py-2 text-sm rounded-md text-foreground/60 hover:text-foreground hover:bg-accent transition-colors"
                    >
                      <MessageSquare className="h-4 w-4 flex-shrink-0" />
                      <span className="truncate">{conversation.title}</span>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t">
            <Link
              to="/settings"
              onClick={onClose}
              className="flex items-center space-x-3 rtl:space-x-reverse px-3 py-2 text-sm font-medium rounded-md text-foreground/60 hover:text-foreground hover:bg-accent transition-colors"
            >
              <Settings className="h-4 w-4" />
              <span>{language === 'ar' ? 'الإعدادات' : 'Settings'}</span>
            </Link>
          </div>
        </div>
      </div>
    </>
  );
};