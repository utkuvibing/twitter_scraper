import { useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useSettingsStore, LicenseStatus } from '../stores/settingsStore';

export type Feature =
  | 'unlimited_tweets'
  | 'unlimited_scrapes'
  | 'csv_export'
  | 'excel_export'
  | 'ai_analysis';

interface LicenseValidationResult {
  valid: boolean;
  status: LicenseStatus;
  message?: string;
}

interface FeatureLimits {
  maxTweetsPerScrape: number | null;
  maxScrapesPerDay: number | null;
  allowedExportFormats: string[];
  hasAIAnalysis: boolean;
}

const FREE_LIMITS: FeatureLimits = {
  maxTweetsPerScrape: 50,
  maxScrapesPerDay: 3,
  allowedExportFormats: ['json'],
  hasAIAnalysis: false,
};

const PRO_LIMITS: FeatureLimits = {
  maxTweetsPerScrape: null,
  maxScrapesPerDay: null,
  allowedExportFormats: ['json', 'csv', 'excel'],
  hasAIAnalysis: false,
};

const PRO_PLUS_LIMITS: FeatureLimits = {
  maxTweetsPerScrape: null,
  maxScrapesPerDay: null,
  allowedExportFormats: ['json', 'csv', 'excel'],
  hasAIAnalysis: true,
};

export function useLicense() {
  const { licenseKey, licenseStatus, setLicenseKey, setLicenseStatus } = useSettingsStore();

  const validateLicense = useCallback(
    async (key: string) => {
      try {
        const result = await invoke<LicenseValidationResult>('validate_license', { key });

        if (result.valid) {
          setLicenseKey(key);
          setLicenseStatus(result.status);
        }

        return result;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to validate license';
        return {
          valid: false,
          status: 'free' as LicenseStatus,
          message: errorMessage,
        };
      }
    },
    [setLicenseKey, setLicenseStatus]
  );

  const getLimits = useCallback((): FeatureLimits => {
    switch (licenseStatus) {
      case 'pro':
        return PRO_LIMITS;
      case 'pro_plus':
        return PRO_PLUS_LIMITS;
      default:
        return FREE_LIMITS;
    }
  }, [licenseStatus]);

  const isFeatureAvailable = useCallback(
    (feature: Feature): boolean => {
      const limits = getLimits();

      switch (feature) {
        case 'unlimited_tweets':
          return limits.maxTweetsPerScrape === null;
        case 'unlimited_scrapes':
          return limits.maxScrapesPerDay === null;
        case 'csv_export':
          return limits.allowedExportFormats.includes('csv');
        case 'excel_export':
          return limits.allowedExportFormats.includes('excel');
        case 'ai_analysis':
          return limits.hasAIAnalysis;
        default:
          return false;
      }
    },
    [getLimits]
  );

  const canExport = useCallback(
    (format: string): boolean => {
      const limits = getLimits();
      return limits.allowedExportFormats.includes(format);
    },
    [getLimits]
  );

  const getMaxTweetsPerScrape = useCallback((): number | null => {
    return getLimits().maxTweetsPerScrape;
  }, [getLimits]);

  const getMaxScrapesPerDay = useCallback((): number | null => {
    return getLimits().maxScrapesPerDay;
  }, [getLimits]);

  return {
    licenseKey,
    licenseStatus,
    validateLicense,
    isFeatureAvailable,
    canExport,
    getMaxTweetsPerScrape,
    getMaxScrapesPerDay,
    getLimits,
  };
}
