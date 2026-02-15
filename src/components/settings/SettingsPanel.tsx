import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useSettingsStore } from '../../stores/settingsStore';
import { useLicense } from '../../hooks/useLicense';
import { useSettings } from '../../hooks/useSettings';
import { open } from '@tauri-apps/plugin-dialog';
import {
  KeyRound,
  Chrome,
  FolderOutput,
  Globe,
  Info,
  Shield,
  ShieldCheck,
  ShieldPlus,
  CheckCircle2,
  FolderOpen,
} from 'lucide-react';

export default function SettingsPanel() {
  const { t, i18n } = useTranslation();
  const {
    language,
    chromePath,
    outputDir,
    licenseKey,
    licenseStatus,
    setLanguage,
    setChromePath,
    setOutputDir,
  } = useSettingsStore();

  const { validateLicense } = useLicense();
  const { saveSettings } = useSettings();

  const [localLicenseKey, setLocalLicenseKey] = useState(licenseKey);
  const [isValidatingLicense, setIsValidatingLicense] = useState(false);
  const [licenseError, setLicenseError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  useEffect(() => {
    i18n.changeLanguage(language);
  }, [language, i18n]);

  useEffect(() => {
    setLocalLicenseKey(licenseKey);
  }, [licenseKey]);

  const handleValidateLicense = async () => {
    if (!localLicenseKey.trim()) {
      setLicenseError(t('settings.licenseRequired', 'Please enter a license key'));
      return;
    }

    setIsValidatingLicense(true);
    setLicenseError(null);

    try {
      const result = await validateLicense(localLicenseKey);

      if (result.valid && result.status !== 'free') {
        showSaveStatus(result.message || 'License validated successfully');
      } else if (!result.valid) {
        setLicenseError(result.message || t('settings.invalidLicense', 'Invalid license key'));
      }
    } catch (error) {
      setLicenseError(
        t('settings.licenseValidationError', 'Failed to validate license')
      );
      console.error(error);
    } finally {
      setIsValidatingLicense(false);
    }
  };

  const showSaveStatus = (message: string) => {
    setSaveStatus(message);
    setTimeout(() => setSaveStatus(null), 2000);
  };

  const handleChromePathChange = (value: string) => {
    setChromePath(value);
  };

  const handleChromePathBlur = () => {
    saveSettings();
    if (chromePath) showSaveStatus('Chrome path updated');
  };

  const handleOutputDirChange = (value: string) => {
    setOutputDir(value);
  };

  const handleOutputDirBlur = () => {
    saveSettings();
    if (outputDir) showSaveStatus('Output directory updated');
  };

  const handleBrowseOutputDir = async () => {
    try {
      const selected = await open({ directory: true, multiple: false });
      if (selected) {
        setOutputDir(selected as string);
        saveSettings();
        showSaveStatus('Output directory updated');
      }
    } catch (e) {
      console.error('Failed to open folder picker:', e);
    }
  };

  const getTierInfo = () => {
    switch (licenseStatus) {
      case 'pro':
        return {
          icon: <ShieldCheck size={18} />,
          label: 'PRO',
          className: 'bg-x-blue/15 text-x-blue border-x-blue/30',
        };
      case 'pro_plus':
        return {
          icon: <ShieldPlus size={18} />,
          label: 'PRO+',
          className: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
        };
      default:
        return {
          icon: <Shield size={18} />,
          label: 'FREE',
          className: 'bg-white/5 text-x-gray border-x-border/50',
        };
    }
  };

  const tier = getTierInfo();

  return (
    <div className="w-full h-full bg-x-darker p-6 overflow-y-auto">
      <div className="max-w-2xl mx-auto space-y-5">
        {/* Header */}
        <div>
          <h1 className="text-xl font-semibold text-x-light">
            {t('settings.title', 'Settings')}
          </h1>
          <p className="text-x-gray text-sm mt-1">
            {t('settings.subtitle', 'Configure your scraper preferences')}
          </p>
        </div>

        {/* Save Status Toast */}
        {saveStatus && (
          <div className="flex items-center gap-2 px-4 py-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400 text-sm animate-fadeIn">
            <CheckCircle2 size={16} />
            {saveStatus}
          </div>
        )}

        {/* License */}
        <section className="bg-x-dark/60 border border-x-border/40 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <KeyRound size={18} className="text-x-gray" />
              <h3 className="text-sm font-semibold text-x-light">
                {t('settings.license', 'License')}
              </h3>
            </div>
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full border ${tier.className}`}>
              {tier.icon}
              {tier.label}
            </span>
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              placeholder="PRO-XXXX-XXXX-XXXX"
              value={localLicenseKey}
              onChange={(e) => setLocalLicenseKey(e.target.value)}
              className="flex-1 bg-x-darker/80 border border-x-border/40 rounded-lg px-3.5 py-2 text-sm text-x-light placeholder-x-gray/50 focus:outline-none focus:border-x-blue/50 transition-colors font-mono"
            />
            <button
              onClick={handleValidateLicense}
              disabled={isValidatingLicense}
              className="px-4 py-2 bg-x-blue text-white text-sm rounded-lg hover:bg-x-blue/80 transition-colors font-medium disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {isValidatingLicense
                ? t('settings.validating', 'Validating...')
                : t('settings.validate', 'Validate')}
            </button>
          </div>
          {licenseError && (
            <p className="text-red-400 text-xs">{licenseError}</p>
          )}

          {/* Plan features */}
          <div className="bg-x-darker/50 rounded-lg p-3.5 space-y-1.5">
            <p className="text-xs font-medium text-x-gray mb-2">
              {t('settings.currentPlan', 'Current Plan Features')}
            </p>
            {licenseStatus === 'free' && (
              <ul className="text-xs text-x-gray/80 space-y-1">
                <li className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-x-gray/50" />
                  {t('settings.freeLimitTweets', 'Up to 50 tweets per scrape')}
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-x-gray/50" />
                  {t('settings.freeLimitExport', 'JSON export only')}
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-x-gray/50" />
                  {t('settings.freeLimitBasic', 'Basic analytics')}
                </li>
              </ul>
            )}
            {licenseStatus === 'pro' && (
              <ul className="text-xs text-x-gray/80 space-y-1">
                <li className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-x-blue" />
                  {t('settings.proUnlimitedTweets', 'Unlimited tweets')}
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-x-blue" />
                  {t('settings.proExportFormats', 'All export formats (JSON, CSV, Excel)')}
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-x-blue" />
                  {t('settings.proAdvancedAnalytics', 'Advanced analytics')}
                </li>
              </ul>
            )}
            {licenseStatus === 'pro_plus' && (
              <ul className="text-xs text-x-gray/80 space-y-1">
                <li className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-purple-400" />
                  {t('settings.proplusEverything', 'Everything in Pro')}
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-purple-400" />
                  {t('settings.proplusAI', 'AI-powered analysis')}
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-purple-400" />
                  {t('settings.proplusScheduled', 'Scheduled scraping')}
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-purple-400" />
                  {t('settings.proplusPriority', 'Priority support')}
                </li>
              </ul>
            )}
          </div>
        </section>

        {/* Browser */}
        <section className="bg-x-dark/60 border border-x-border/40 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2.5">
            <Chrome size={18} className="text-x-gray" />
            <h3 className="text-sm font-semibold text-x-light">
              {t('settings.browser', 'Browser')}
            </h3>
          </div>
          <div>
            <label className="block text-xs text-x-gray mb-1.5">
              {t('settings.chromePath', 'Chrome Executable Path')}
            </label>
            <input
              type="text"
              placeholder="C:\Program Files\Google\Chrome\Application\chrome.exe"
              value={chromePath}
              onChange={(e) => handleChromePathChange(e.target.value)}
              onBlur={handleChromePathBlur}
              className="w-full bg-x-darker/80 border border-x-border/40 rounded-lg px-3.5 py-2 text-sm text-x-light placeholder-x-gray/40 focus:outline-none focus:border-x-blue/50 transition-colors font-mono"
            />
            <p className="text-[11px] text-x-gray/60 mt-1.5">
              {t('settings.chromePathNote', 'Leave empty to use default Chrome installation')}
            </p>
          </div>
        </section>

        {/* Output */}
        <section className="bg-x-dark/60 border border-x-border/40 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2.5">
            <FolderOutput size={18} className="text-x-gray" />
            <h3 className="text-sm font-semibold text-x-light">
              {t('settings.output', 'Output')}
            </h3>
          </div>
          <div>
            <label className="block text-xs text-x-gray mb-1.5">
              {t('settings.defaultOutputDir', 'Default Output Directory')}
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder={t('settings.selectDirectory', 'Paste or type a directory path...')}
                value={outputDir}
                onChange={(e) => handleOutputDirChange(e.target.value)}
                onBlur={handleOutputDirBlur}
                className="flex-1 bg-x-darker/80 border border-x-border/40 rounded-lg px-3.5 py-2 text-sm text-x-light placeholder-x-gray/40 focus:outline-none focus:border-x-blue/50 transition-colors font-mono"
              />
              <button
                onClick={handleBrowseOutputDir}
                className="px-3 py-2 bg-x-dark border border-x-border/40 rounded-lg hover:bg-white/5 transition-colors text-x-gray hover:text-x-light flex items-center gap-1.5"
                title={t('settings.browse', 'Browse')}
              >
                <FolderOpen size={16} />
                <span className="text-sm">{t('settings.browse', 'Browse')}</span>
              </button>
            </div>
            <p className="text-[11px] text-x-gray/60 mt-1.5">
              {t('settings.outputDirNote', 'Default location for exported data files')}
            </p>
          </div>
        </section>

        {/* Language */}
        <section className="bg-x-dark/60 border border-x-border/40 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2.5">
            <Globe size={18} className="text-x-gray" />
            <h3 className="text-sm font-semibold text-x-light">
              {t('settings.language', 'Language')}
            </h3>
          </div>
          <div>
            <label className="block text-xs text-x-gray mb-1.5">
              {t('settings.interfaceLanguage', 'Interface Language')}
            </label>
            <select
              value={language}
              onChange={(e) => {
                setLanguage(e.target.value as any);
                saveSettings();
                showSaveStatus('Language updated');
              }}
              className="w-full bg-x-darker/80 border border-x-border/40 rounded-lg px-3.5 py-2 text-sm text-x-light focus:outline-none focus:border-x-blue/50 transition-colors cursor-pointer appearance-none"
              style={{ backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%2371767b' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`, backgroundPosition: 'right 0.5rem center', backgroundRepeat: 'no-repeat', backgroundSize: '1.5em 1.5em', paddingRight: '2.5rem' }}
            >
              <option value="en">English</option>
              <option value="tr">Turkce</option>
            </select>
          </div>
        </section>

        {/* About */}
        <section className="bg-x-dark/60 border border-x-border/40 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2.5">
            <Info size={18} className="text-x-gray" />
            <h3 className="text-sm font-semibold text-x-light">
              {t('settings.about', 'About')}
            </h3>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-x-gray">{t('settings.version', 'Version')}</span>
              <span className="text-x-light font-mono text-xs">1.0.0</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-x-gray">{t('settings.releaseDate', 'Release Date')}</span>
              <span className="text-x-light text-xs">February 2026</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
