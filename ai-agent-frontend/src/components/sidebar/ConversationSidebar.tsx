import React, { useState, useEffect } from 'react';
import { useChatStore } from '../../store/chatStore';
import { useLanguageStore } from '../../store/languageStore';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Card } from '../ui/Card';
import { 
  Plus, 
  Search, 
  MessageSquare, 
  Trash2, 
  Edit3, 
  MoreVertical,
  Clock,
  Check,
  X
} from 'lucide-react';
import { Conversation } from '../../types/api';

export const ConversationSidebar: React.FC = () => {
  const { 
    conversations, 
    currentConversation, 
    isLoading, 
    createConversation,
    deleteConversation,
    renameConversation,
    loadConversations,
    setCurrentConversation
  } = useChatStore();
  
  const { language } = useLanguageStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [editingConversation, setEditingConversation] = useState<number | null>(null);
  const [editingTitle, setEditingTitle] = useState('');

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const filteredConversations = conversations.filter(conv =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleNewConversation = async () => {
    try {
      await createConversation();
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleDeleteConversation = async (conversationId: number) => {
    if (window.confirm(language === 'ar' ? 'هل أنت متأكد من حذف هذه المحادثة؟' : 'Are you sure you want to delete this conversation?')) {
      try {
        await deleteConversation(conversationId);
      } catch (error) {
        console.error('Failed to delete conversation:', error);
      }
    }
  };

  const handleRenameConversation = async (conversationId: number, newTitle: string) => {
    try {
      await renameConversation(conversationId, newTitle);
      setEditingConversation(null);
      setEditingTitle('');
    } catch (error) {
      console.error('Failed to rename conversation:', error);
    }
  };

  const startEditing = (conversation: Conversation) => {
    setEditingConversation(conversation.id);
    setEditingTitle(conversation.title);
  };

  const cancelEditing = () => {
    setEditingConversation(null);
    setEditingTitle('');
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);
    
    if (diffInHours < 24) {
      return date.toLocaleTimeString(language === 'ar' ? 'ar-SA' : 'en-US', {
        hour: '2-digit',
        minute: '2-digit'
      });
    } else if (diffInHours < 24 * 7) {
      return date.toLocaleDateString(language === 'ar' ? 'ar-SA' : 'en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric'
      });
    } else {
      return date.toLocaleDateString(language === 'ar' ? 'ar-SA' : 'en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    }
  };

  const ConversationItem: React.FC<{ conversation: Conversation }> = ({ conversation }) => {
    const isActive = currentConversation?.id === conversation.id;
    const isEditing = editingConversation === conversation.id;

    return (
      <div
        className={`group p-3 rounded-lg cursor-pointer transition-all duration-200 ${
          isActive
            ? 'bg-primary text-primary-foreground'
            : 'hover:bg-muted'
        }`}
        onClick={() => !isEditing && setCurrentConversation(conversation)}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            {isEditing ? (
              <div className="space-y-2">
                <Input
                  value={editingTitle}
                  onChange={(e) => setEditingTitle(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      handleRenameConversation(conversation.id, editingTitle);
                    } else if (e.key === 'Escape') {
                      cancelEditing();
                    }
                  }}
                  onBlur={() => handleRenameConversation(conversation.id, editingTitle)}
                  className="text-sm"
                  autoFocus
                />
              </div>
            ) : (
              <>
                <h3 className={`text-sm font-medium truncate ${
                  isActive ? 'text-primary-foreground' : 'text-foreground'
                }`}>
                  {conversation.title}
                </h3>
                <div className="flex items-center justify-between mt-1">
                  <div className="flex items-center space-x-1 rtl:space-x-reverse text-xs opacity-70">
                    <Clock className="h-3 w-3" />
                    <span>{formatDate(conversation.updated_at)}</span>
                  </div>
                  {conversation.message_count > 0 && (
                    <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                      isActive 
                        ? 'bg-primary-foreground/20 text-primary-foreground' 
                        : 'bg-muted text-muted-foreground'
                    }`}>
                      {conversation.message_count}
                    </span>
                  )}
                </div>
              </>
            )}
          </div>
          
          {!isEditing && (
            <div className="flex items-center space-x-1 rtl:space-x-reverse opacity-0 group-hover:opacity-100 transition-opacity">
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={(e) => {
                  e.stopPropagation();
                  startEditing(conversation);
                }}
                title={language === 'ar' ? 'إعادة تسمية' : 'Rename'}
              >
                <Edit3 className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-destructive hover:text-destructive"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteConversation(conversation.id);
                }}
                title={language === 'ar' ? 'حذف' : 'Delete'}
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          )}
          
          {isEditing && (
            <div className="flex items-center space-x-1 rtl:space-x-reverse">
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-green-600 hover:text-green-700"
                onClick={(e) => {
                  e.stopPropagation();
                  handleRenameConversation(conversation.id, editingTitle);
                }}
                title={language === 'ar' ? 'حفظ' : 'Save'}
              >
                <Check className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-destructive hover:text-destructive"
                onClick={(e) => {
                  e.stopPropagation();
                  cancelEditing();
                }}
                title={language === 'ar' ? 'إلغاء' : 'Cancel'}
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="w-80 bg-background border-r flex flex-col">
      {/* Header */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">
            {language === 'ar' ? 'المحادثات' : 'Conversations'}
          </h2>
          <Button
            onClick={handleNewConversation}
            size="icon"
            disabled={isLoading}
            title={language === 'ar' ? 'محادثة جديدة' : 'New conversation'}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={language === 'ar' ? 'البحث في المحادثات...' : 'Search conversations...'}
            className="pl-9"
          />
        </div>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : filteredConversations.length === 0 ? (
          <div className="text-center py-8">
            {searchQuery ? (
              <div className="text-muted-foreground">
                {language === 'ar' ? 'لا توجد محادثات تطابق البحث' : 'No conversations match your search'}
              </div>
            ) : (
              <div className="text-muted-foreground">
                <MessageSquare className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>{language === 'ar' ? 'لا توجد محادثات بعد' : 'No conversations yet'}</p>
                <Button
                  onClick={handleNewConversation}
                  className="mt-2"
                  size="sm"
                >
                  {language === 'ar' ? 'ابدأ محادثة جديدة' : 'Start new conversation'}
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            {filteredConversations.map((conversation) => (
              <ConversationItem
                key={conversation.id}
                conversation={conversation}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t">
        <div className="text-xs text-muted-foreground text-center">
          {language === 'ar' 
            ? `${conversations.length} محادثة`
            : `${conversations.length} conversations`
          }
        </div>
      </div>
    </div>
  );
};