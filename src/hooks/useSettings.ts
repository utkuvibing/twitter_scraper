import { useCallback, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useSettingsStore, Language, LicenseStatus, Theme } from '../stores/settingsStore';

interface BackendSettings {
  language: string;
  chrome_path: string;
  scroll_pause_min: number;
  scroll_pause_max: number;
  output_dir: string;
  license_key: string;
  license_status: string;
  theme: string;
}

export function useSettings() {
  const {
    language,
    chromePath,
    scrollPauseMin,
    scrollPauseMax,
    outputDir,
    licenseKey,
    licenseStatus,
    theme,
    setLanguage,
    setChromePath,
    setScrollSettings,
    setOutputDir,
    setLicenseKey,
    setLicenseStatus,
    setTheme,
  } = useSettingsStore();

  const loadSettings = useCallback(async () => {
    try {
      const settings = await invoke<BackendSettings>('load_settings');

      setLanguage(settings.language as Language);
      setChromePath(settings.chrome_path);
      setScrollSettings(settings.scroll_pause_min, settings.scroll_pause_max);
      setOutputDir(settings.output_dir);
      setLicenseKey(settings.license_key);
      setLicenseStatus(settings.license_status as LicenseStatus);
      setTheme(settings.theme as Theme);

      return settings;
    } catch (err) {
      console.error('Failed to load settings from backend:', err);
      throw err;
    }
  }, [
    setLanguage,
    setChromePath,
    setScrollSettings,
    setOutputDir,
    setLicenseKey,
    setLicenseStatus,
    setTheme,
  ]);

  const saveSettings = useCallback(async () => {
    try {
      const settings: BackendSettings = {
        language,
        chrome_path: chromePath,
        scroll_pause_min: scrollPauseMin,
        scroll_pause_max: scrollPauseMax,
        output_dir: outputDir,
        license_key: licenseKey,
        license_status: licenseStatus,
        theme,
      };

      await invoke('save_settings', { settings });
    } catch (err) {
      console.error('Failed to save settings to backend:', err);
      throw err;
    }
  }, [
    language,
    chromePath,
    scrollPauseMin,
    scrollPauseMax,
    outputDir,
    licenseKey,
    licenseStatus,
    theme,
  ]);

  const updateLanguage = useCallback(
    async (newLanguage: Language) => {
      setLanguage(newLanguage);
      await saveSettings();
    },
    [setLanguage, saveSettings]
  );

  const updateChromePath = useCallback(
    async (path: string) => {
      setChromePath(path);
      await saveSettings();
    },
    [setChromePath, saveSettings]
  );

  const updateScrollSettings = useCallback(
    async (min: number, max: number) => {
      setScrollSettings(min, max);
      await saveSettings();
    },
    [setScrollSettings, saveSettings]
  );

  const updateOutputDir = useCallback(
    async (dir: string) => {
      setOutputDir(dir);
      await saveSettings();
    },
    [setOutputDir, saveSettings]
  );

  const updateTheme = useCallback(
    async (newTheme: Theme) => {
      setTheme(newTheme);
      await saveSettings();
    },
    [setTheme, saveSettings]
  );

  useEffect(() => {
    loadSettings().catch((err) => {
      console.warn('Could not load settings from backend on mount:', err);
    });
  }, [loadSettings]);

  return {
    language,
    chromePath,
    scrollPauseMin,
    scrollPauseMax,
    outputDir,
    licenseKey,
    licenseStatus,
    theme,
    loadSettings,
    saveSettings,
    updateLanguage,
    updateChromePath,
    updateScrollSettings,
    updateOutputDir,
    updateTheme,
  };
}
