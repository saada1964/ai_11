import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface LanguageState {
  language: 'ar' | 'en';
  rtl: boolean;
  
  // Actions
  setLanguage: (language: 'ar' | 'en') => void;
  toggleLanguage: () => void;
}

export const useLanguageStore = create<LanguageState>()(
  persist(
    (set, get) => ({
      language: 'ar',
      rtl: true,

      setLanguage: (language) => {
        set({ 
          language, 
          rtl: language === 'ar' 
        });
        
        // Apply language and direction to document
        const root = document.documentElement;
        root.setAttribute('lang', language);
        root.setAttribute('dir', language === 'ar' ? 'rtl' : 'ltr');
        root.setAttribute('data-language', language);
      },

      toggleLanguage: () => {
        const currentLanguage = get().language;
        const newLanguage = currentLanguage === 'ar' ? 'en' : 'ar';
        get().setLanguage(newLanguage);
      }
    }),
    {
      name: 'language-storage',
      partialize: (state) => ({
        language: state.language,
        rtl: state.rtl
      })
    }
  )
);

// Initialize language on app start
if (typeof window !== 'undefined') {
  const languageStore = useLanguageStore.getState();
  languageStore.setLanguage(languageStore.language);
}