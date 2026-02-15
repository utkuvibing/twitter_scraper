import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export type Language = 'en' | 'tr';
export type LicenseStatus = 'free' | 'pro' | 'pro_plus';
export type Theme = 'dark' | 'light';

interface SettingsState {
  language: Language;
  chromePath: string;
  scrollPauseMin: number;
  scrollPauseMax: number;
  outputDir: string;
  licenseKey: string;
  licenseStatus: LicenseStatus;
  theme: Theme;

  // Actions
  setLanguage: (language: Language) => void;
  setChromePath: (path: string) => void;
  setScrollSettings: (min: number, max: number) => void;
  setOutputDir: (dir: string) => void;
  setLicenseKey: (key: string) => void;
  setLicenseStatus: (status: LicenseStatus) => void;
  setTheme: (theme: Theme) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      language: 'en',
      chromePath: '',
      scrollPauseMin: 2,
      scrollPauseMax: 4,
      outputDir: '',
      licenseKey: '',
      licenseStatus: 'free',
      theme: 'dark',

      setLanguage: (language: Language) => {
        set({ language });
      },

      setChromePath: (path: string) => {
        set({ chromePath: path });
      },

      setScrollSettings: (min: number, max: number) => {
        set({
          scrollPauseMin: min,
          scrollPauseMax: max,
        });
      },

      setOutputDir: (dir: string) => {
        set({ outputDir: dir });
      },

      setLicenseKey: (key: string) => {
        set({ licenseKey: key });
      },

      setLicenseStatus: (status: LicenseStatus) => {
        set({ licenseStatus: status });
      },

      setTheme: (theme: Theme) => {
        set({ theme });
      },
    }),
    {
      name: 'twitter-scraper-settings',
      storage: createJSONStorage(() => localStorage),
    }
  )
);
