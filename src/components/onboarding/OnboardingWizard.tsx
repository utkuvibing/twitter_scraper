import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { invoke } from '@tauri-apps/api/core';
import { useSettingsStore } from '../../stores/settingsStore';
import { useLicense } from '../../hooks/useLicense';

interface OnboardingWizardProps {
  onComplete: () => void;
}

export default function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
  const { t } = useTranslation();
  const [currentStep, setCurrentStep] = useState(0);
  const [licenseKey, setLicenseKey] = useState('');
  const [licenseError, setLicenseError] = useState<string | null>(null);
  const [isChromeInstalled, setIsChromeInstalled] = useState<boolean | null>(
    null
  );
  const [isCheckingChrome, setIsCheckingChrome] = useState(false);
  const [isValidatingLicense, setIsValidatingLicense] = useState(false);
  const { validateLicense } = useLicense();

  const steps = [
    {
      id: 'welcome',
      title: t('onboarding.welcome', 'Welcome to Twitter/X Scraper'),
      content: 'welcome',
    },
    {
      id: 'chrome',
      title: t('onboarding.chromeCheck', 'Chrome Browser Check'),
      content: 'chrome',
    },
    {
      id: 'features',
      title: t('onboarding.features', 'Feature Tour'),
      content: 'features',
    },
    {
      id: 'license',
      title: t('onboarding.license', 'License Activation'),
      content: 'license',
    },
    {
      id: 'ready',
      title: t('onboarding.ready', "You're All Set!"),
      content: 'ready',
    },
  ];

  const checkChrome = async () => {
    setIsCheckingChrome(true);
    try {
      const result = await invoke<{ installed: boolean; path: string | null }>('check_chrome');
      setIsChromeInstalled(result.installed);
    } catch (error) {
      // If the command fails (e.g., not in Tauri context), assume not installed
      console.error('Chrome check failed:', error);
      setIsChromeInstalled(false);
    } finally {
      setIsCheckingChrome(false);
    }
  };

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleComplete();
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSkip = () => {
    setCurrentStep(steps.length - 1);
  };

  const handleComplete = async () => {
    if (licenseKey.trim()) {
      setIsValidatingLicense(true);
      try {
        await validateLicense(licenseKey);
      } catch (err) {
        console.error('License validation failed during onboarding:', err);
      } finally {
        setIsValidatingLicense(false);
      }
    }
    onComplete();
  };

  const handleValidateLicenseInline = async () => {
    if (!licenseKey.trim()) return;
    setIsValidatingLicense(true);
    setLicenseError(null);
    try {
      const result = await validateLicense(licenseKey);
      if (!result.valid) {
        setLicenseError(result.message || 'Invalid license key');
      }
    } catch (err) {
      setLicenseError('Failed to validate license');
    } finally {
      setIsValidatingLicense(false);
    }
  };

  const renderStepContent = () => {
    const step = steps[currentStep];

    switch (step.content) {
      case 'welcome':
        return (
          <div className="text-center py-8">
            <div className="text-7xl mb-6">🚀</div>
            <h2 className="text-3xl font-bold text-x-light mb-4">
              {t('onboarding.welcomeTitle', 'Welcome to Twitter/X Scraper')}
            </h2>
            <p className="text-x-gray text-lg max-w-2xl mx-auto leading-relaxed">
              {t(
                'onboarding.welcomeDesc',
                'Your powerful tool for collecting and analyzing tweets. This quick setup will help you get started in just a few steps.'
              )}
            </p>
          </div>
        );

      case 'chrome':
        return (
          <div className="py-8">
            <div className="text-center mb-8">
              <div className="text-6xl mb-4">🌐</div>
              <h2 className="text-2xl font-bold text-x-light mb-3">
                {t('onboarding.chromeTitle', 'Chrome Browser Required')}
              </h2>
              <p className="text-x-gray max-w-xl mx-auto">
                {t(
                  'onboarding.chromeDesc',
                  'This app uses Chrome to scrape tweets. Let\'s verify Chrome is installed on your system.'
                )}
              </p>
            </div>

            <div className="max-w-md mx-auto">
              {isChromeInstalled === null ? (
                <button
                  onClick={checkChrome}
                  disabled={isCheckingChrome}
                  className="w-full px-6 py-4 bg-x-blue text-white rounded-lg hover:bg-opacity-80 transition-all font-medium text-lg disabled:opacity-50"
                >
                  {isCheckingChrome
                    ? t('onboarding.checking', 'Checking...')
                    : t('onboarding.checkChrome', 'Check Chrome Installation')}
                </button>
              ) : isChromeInstalled ? (
                <div className="bg-green-900 bg-opacity-20 border border-green-600 rounded-lg p-6 text-center">
                  <svg
                    className="w-16 h-16 text-green-500 mx-auto mb-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <p className="text-green-400 font-medium">
                    {t('onboarding.chromeFound', 'Chrome is installed and ready!')}
                  </p>
                </div>
              ) : (
                <div className="bg-red-900 bg-opacity-20 border border-red-600 rounded-lg p-6">
                  <div className="text-center mb-4">
                    <svg
                      className="w-16 h-16 text-red-500 mx-auto mb-3"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    <p className="text-red-400 font-medium mb-2">
                      {t('onboarding.chromeNotFound', 'Chrome not found')}
                    </p>
                    <p className="text-x-gray text-sm">
                      {t(
                        'onboarding.installChrome',
                        'Please install Google Chrome to continue'
                      )}
                    </p>
                  </div>
                  <button
                    onClick={() => setIsChromeInstalled(null)}
                    className="block w-full px-6 py-3 bg-x-dark border border-x-border text-x-light rounded-lg hover:border-x-blue transition-all font-medium text-center mt-3"
                  >
                    {t('onboarding.recheckChrome', 'Re-check')}
                  </button>
                </div>
              )}
            </div>
          </div>
        );

      case 'features':
        return (
          <div className="py-8">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-x-light mb-3">
                {t('onboarding.featureTitle', 'Powerful Features')}
              </h2>
              <p className="text-x-gray">
                {t(
                  'onboarding.featureSubtitle',
                  'Everything you need to collect and analyze tweets'
                )}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
              <div className="bg-x-dark border border-x-border rounded-lg p-6">
                <div className="text-4xl mb-3">📊</div>
                <h3 className="text-lg font-semibold text-x-light mb-2">
                  {t('onboarding.featureAnalytics', 'Advanced Analytics')}
                </h3>
                <p className="text-x-gray text-sm">
                  {t(
                    'onboarding.featureAnalyticsDesc',
                    'Visualize engagement metrics, posting patterns, and content insights with interactive charts'
                  )}
                </p>
              </div>

              <div className="bg-x-dark border border-x-border rounded-lg p-6">
                <div className="text-4xl mb-3">🤖</div>
                <h3 className="text-lg font-semibold text-x-light mb-2">
                  {t('onboarding.featureAI', 'AI-Powered Analysis')}
                </h3>
                <p className="text-x-gray text-sm">
                  {t(
                    'onboarding.featureAIDesc',
                    'Get sentiment analysis, topic extraction, and content recommendations using OpenAI'
                  )}
                </p>
              </div>

              <div className="bg-x-dark border border-x-border rounded-lg p-6">
                <div className="text-4xl mb-3">💾</div>
                <h3 className="text-lg font-semibold text-x-light mb-2">
                  {t('onboarding.featureExport', 'Flexible Export')}
                </h3>
                <p className="text-x-gray text-sm">
                  {t(
                    'onboarding.featureExportDesc',
                    'Export your data in JSON, CSV, or Excel formats for further analysis'
                  )}
                </p>
              </div>

              <div className="bg-x-dark border border-x-border rounded-lg p-6">
                <div className="text-4xl mb-3">🔍</div>
                <h3 className="text-lg font-semibold text-x-light mb-2">
                  {t('onboarding.featureFilters', 'Smart Filtering')}
                </h3>
                <p className="text-x-gray text-sm">
                  {t(
                    'onboarding.featureFiltersDesc',
                    'Scrape tweets by count, date range, or time period with flexible options'
                  )}
                </p>
              </div>
            </div>
          </div>
        );

      case 'license':
        return (
          <div className="py-8">
            <div className="text-center mb-8">
              <div className="text-6xl mb-4">🔑</div>
              <h2 className="text-2xl font-bold text-x-light mb-3">
                {t('onboarding.licenseTitle', 'Activate Your License')}
              </h2>
              <p className="text-x-gray max-w-xl mx-auto">
                {t(
                  'onboarding.licenseDesc',
                  'Enter your license key to unlock premium features, or skip to use the free tier'
                )}
              </p>
            </div>

            <div className="max-w-md mx-auto space-y-6">
              <div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="PRO-XXXX-XXXX-XXXX"
                    value={licenseKey}
                    onChange={(e) => setLicenseKey(e.target.value)}
                    className="flex-1 bg-x-dark border border-x-border rounded-lg px-4 py-3 text-x-light placeholder-x-gray focus:outline-none focus:border-x-blue transition-colors font-mono text-center text-lg"
                  />
                  {licenseKey.trim() && (
                    <button
                      onClick={handleValidateLicenseInline}
                      disabled={isValidatingLicense}
                      className="px-4 py-3 bg-x-blue text-white rounded-lg hover:bg-opacity-80 transition-all font-medium disabled:opacity-50"
                    >
                      {isValidatingLicense ? '...' : 'Validate'}
                    </button>
                  )}
                </div>
                {licenseError && (
                  <p className="text-red-400 text-sm mt-2 text-center">{licenseError}</p>
                )}
              </div>

              <div className="bg-x-dark border border-x-border rounded-lg p-6">
                <h4 className="font-semibold text-x-light mb-3 text-center">
                  {t('onboarding.freeTier', 'Free Tier Includes')}
                </h4>
                <ul className="text-sm text-x-gray space-y-2">
                  <li className="flex items-center gap-2">
                    <svg
                      className="w-5 h-5 text-x-blue flex-shrink-0"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    {t('onboarding.freeLimit', 'Up to 50 tweets per scrape')}
                  </li>
                  <li className="flex items-center gap-2">
                    <svg
                      className="w-5 h-5 text-x-blue flex-shrink-0"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    {t('onboarding.freeExport', 'JSON export')}
                  </li>
                  <li className="flex items-center gap-2">
                    <svg
                      className="w-5 h-5 text-x-blue flex-shrink-0"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    {t('onboarding.freeAnalytics', 'Basic analytics')}
                  </li>
                </ul>
              </div>

              <p className="text-center text-xs text-x-gray">
                {t(
                  'onboarding.licenseNote',
                  "Don't have a license? You can purchase one later from Settings"
                )}
              </p>
            </div>
          </div>
        );

      case 'ready':
        return (
          <div className="text-center py-8">
            <div className="text-7xl mb-6">🎉</div>
            <h2 className="text-3xl font-bold text-x-light mb-4">
              {t('onboarding.readyTitle', "You're All Set!")}
            </h2>
            <p className="text-x-gray text-lg max-w-2xl mx-auto leading-relaxed mb-8">
              {t(
                'onboarding.readyDesc',
                'Your Twitter/X Scraper is configured and ready to use. Start by entering a username to scrape their tweets!'
              )}
            </p>

            <div className="max-w-md mx-auto bg-x-dark border border-x-border rounded-lg p-6">
              <h4 className="font-semibold text-x-light mb-3">
                {t('onboarding.quickTips', 'Quick Tips')}
              </h4>
              <ul className="text-sm text-x-gray text-left space-y-2">
                <li>• {t('onboarding.tip1', 'Start with a small test scrape to verify everything works')}</li>
                <li>• {t('onboarding.tip2', 'Use date ranges to focus on specific time periods')}</li>
                <li>• {t('onboarding.tip3', 'Check the Analytics tab after scraping for insights')}</li>
                <li>• {t('onboarding.tip4', 'Configure scroll settings in Settings for optimal performance')}</li>
              </ul>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-90 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-x-darker border border-x-border rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Content */}
        <div className="flex-1 overflow-y-auto p-8">
          {renderStepContent()}
        </div>

        {/* Progress Dots */}
        <div className="flex justify-center gap-2 px-8 py-4 border-t border-x-border">
          {steps.map((step, index) => (
            <div
              key={step.id}
              className={`h-2 rounded-full transition-all ${
                index === currentStep
                  ? 'w-8 bg-x-blue'
                  : index < currentStep
                  ? 'w-2 bg-x-blue bg-opacity-50'
                  : 'w-2 bg-x-border'
              }`}
            />
          ))}
        </div>

        {/* Navigation */}
        <div className="flex justify-between items-center px-8 py-6 border-t border-x-border bg-x-dark">
          <button
            onClick={handleBack}
            disabled={currentStep === 0}
            className="px-6 py-2.5 text-x-gray hover:text-x-light transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {t('onboarding.back', 'Back')}
          </button>

          <div className="flex gap-3">
            {currentStep < steps.length - 1 && currentStep > 0 && (
              <button
                onClick={handleSkip}
                className="px-6 py-2.5 text-x-gray hover:text-x-light transition-colors font-medium"
              >
                {t('onboarding.skip', 'Skip')}
              </button>
            )}
            <button
              onClick={handleNext}
              disabled={
                (steps[currentStep].content === 'chrome' &&
                isChromeInstalled === false) || isValidatingLicense
              }
              className="px-8 py-2.5 bg-x-blue text-white rounded-lg hover:bg-opacity-80 transition-all font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {currentStep === steps.length - 1
                ? t('onboarding.getStarted', 'Get Started')
                : t('onboarding.next', 'Next')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
