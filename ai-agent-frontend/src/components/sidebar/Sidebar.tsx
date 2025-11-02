import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { MessageSquarePlus, Search, Trash2, MoreVertical, X } from 'lucide-react';
import { useChat } from '../../contexts/ChatContext';
import { useApp } from '../../contexts/AppContext';
import type { Conversation } from '../../types';
import { formatDistanceToNow } from 'date-fns';
import { ar, enUS } from 'date-fns/locale';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();
  const { language } = useApp();
  const {
    conversations,
    currentConversation,
    loadConversations,
    createNewConversation,
    deleteConversation,
    loadConversation,
  } = useChat();

  const [searchQuery, setSearchQuery] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const filteredConversations = conversations.filter((conv) =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const groupedConversations = {
    today: [] as Conversation[],
    yesterday: [] as Conversation[],
    thisWeek: [] as Conversation[],
    older: [] as Conversation[],
  };

  const now = new Date();
  const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  const twoDaysAgo = new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000);
  const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

  filteredConversations.forEach((conv) => {
    const convDate = new Date(conv.updated_at);
    if (convDate > oneDayAgo) {
      groupedConversations.today.push(conv);
    } else if (convDate > twoDaysAgo) {
      groupedConversations.yesterday.push(conv);
    } else if (convDate > oneWeekAgo) {
      groupedConversations.thisWeek.push(conv);
    } else {
      groupedConversations.older.push(conv);
    }
  });

  const handleNewChat = async () => {
    await createNewConversation();
  };

  const handleSelectConversation = (conversation: Conversation) => {
    loadConversation(conversation.id);
    if (window.innerWidth < 768) {
      onClose();
    }
  };

  const handleDeleteConversation = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (deleteConfirmId === id) {
      await deleteConversation(id);
      setDeleteConfirmId(null);
    } else {
      setDeleteConfirmId(id);
    }
  };

  const ConversationGroup = ({ title, conversations }: { title: string; conversations: Conversation[] }) => {
    if (conversations.length === 0) return null;

    return (
      <div className="mb-6">
        <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2 px-3">
          {title}
        </h3>
        <div className="space-y-1">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => handleSelectConversation(conv)}
              className={`group relative flex items-center px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                currentConversation?.id === conv.id
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'
              }`}
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{conv.title}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {conv.total_messages} {t('chat.messages', 'رسائل')}
                </p>
              </div>
              
              <button
                onClick={(e) => handleDeleteConversation(conv.id, e)}
                className={`ml-2 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity ${
                  deleteConfirmId === conv.id
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-gray-400 hover:text-red-600 dark:hover:text-red-400'
                }`}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <div
        className={`fixed md:relative inset-y-0 ${
          language === 'ar' ? 'right-0' : 'left-0'
        } z-50 w-80 bg-white dark:bg-gray-900 border-${
          language === 'ar' ? 'l' : 'r'
        } border-gray-200 dark:border-gray-800 transform transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : language === 'ar' ? 'translate-x-full md:translate-x-0' : '-translate-x-full md:translate-x-0'
        } flex flex-col h-full`}
      >
        {/* Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              {t('app.title')}
            </h2>
            <button
              onClick={onClose}
              className="md:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
          >
            <MessageSquarePlus className="w-5 h-5" />
            {t('chat.newChat')}
          </button>
        </div>

        {/* Search */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-800">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('chat.searchConversations')}
              className="w-full pl-10 pr-4 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 dark:text-white"
            />
          </div>
        </div>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto p-4">
          <ConversationGroup title={t('chat.today')} conversations={groupedConversations.today} />
          <ConversationGroup title={t('chat.yesterday')} conversations={groupedConversations.yesterday} />
          <ConversationGroup title={t('chat.thisWeek')} conversations={groupedConversations.thisWeek} />
          <ConversationGroup title={t('chat.older')} conversations={groupedConversations.older} />
          
          {filteredConversations.length === 0 && (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              {searchQuery ? t('chat.noResults', 'لا توجد نتائج') : t('chat.noConversations', 'لا توجد محادثات')}
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default Sidebar;
