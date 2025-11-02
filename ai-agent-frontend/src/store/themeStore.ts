import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Theme = 'light' | 'dark' | 'system';
export type ColorScheme = 'blue' | 'green' | 'purple' | 'orange' | 'pink';

interface ThemeState {
  theme: Theme;
  colorScheme: ColorScheme;
  fontSize: 'small' | 'medium' | 'large';
  compactMode: boolean;
  animationSpeed: 'slow' | 'normal' | 'fast';
  
  // Actions
  setTheme: (theme: Theme) => void;
  setColorScheme: (colorScheme: ColorScheme) => void;
  setFontSize: (fontSize: 'small' | 'medium' | 'large') => void;
  setCompactMode: (compact: boolean) => void;
  setAnimationSpeed: (speed: 'slow' | 'normal' | 'fast') => void;
  resetTheme: () => void;
}

const defaultSettings = {
  theme: 'system' as Theme,
  colorScheme: 'blue' as ColorScheme,
  fontSize: 'medium' as 'small' | 'medium' | 'large',
  compactMode: false,
  animationSpeed: 'normal' as 'slow' | 'normal' | 'fast'
};

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      ...defaultSettings,

      setTheme: (theme) => {
        set({ theme });
        
        // Apply theme to document
        const root = document.documentElement;
        
        if (theme === 'dark') {
          root.classList.add('dark');
        } else if (theme === 'light') {
          root.classList.remove('dark');
        } else {
          // System theme
          const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
          if (isDark) {
            root.classList.add('dark');
          } else {
            root.classList.remove('dark');
          }
        }
      },

      setColorScheme: (colorScheme) => {
        set({ colorScheme });
        
        // Apply color scheme to document
        const root = document.documentElement;
        root.setAttribute('data-color-scheme', colorScheme);
      },

      setFontSize: (fontSize) => {
        set({ fontSize });
        
        // Apply font size to document
        const root = document.documentElement;
        root.setAttribute('data-font-size', fontSize);
      },

      setCompactMode: (compact) => {
        set({ compactMode: compact });
        
        // Apply compact mode to document
        const root = document.documentElement;
        if (compact) {
          root.classList.add('compact');
        } else {
          root.classList.remove('compact');
        }
      },

      setAnimationSpeed: (animationSpeed) => {
        set({ animationSpeed });
        
        // Apply animation speed to document
        const root = document.documentElement;
        root.setAttribute('data-animation-speed', animationSpeed);
      },

      resetTheme: () => {
        set({ ...defaultSettings });
        
        // Reset document classes
        const root = document.documentElement;
        root.classList.remove('dark', 'compact');
        root.removeAttribute('data-color-scheme');
        root.removeAttribute('data-font-size');
        root.removeAttribute('data-animation-speed');
      }
    }),
    {
      name: 'theme-storage',
      partialize: (state) => ({
        theme: state.theme,
        colorScheme: state.colorScheme,
        fontSize: state.fontSize,
        compactMode: state.compactMode,
        animationSpeed: state.animationSpeed
      })
    }
  )
);

// Initialize theme on app start
if (typeof window !== 'undefined') {
  const themeStore = useThemeStore.getState();
  themeStore.setTheme(themeStore.theme);
}