import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { invoke } from '@tauri-apps/api/core';

interface OnboardingWizardProps {
  onComplete: () => void;
}

export default function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
  const { t } = useTranslation();
  const [currentStep, setCurrentStep] = useState(0);
  const [isChromeInstalled, setIsChromeInstalled] = useState<boolean | null>(
    null
  );
  const [isCheckingChrome, setIsCheckingChrome] = useState(false);

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
    onComplete();
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
                'A local-first tool for archiving tweets you are authorized to access. This quick setup will help you check the basics before your first scrape.'
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
                {t('onboarding.featureTitle', 'Core Archiving Workflow')}
              </h2>
              <p className="text-x-gray">
                {t(
                  'onboarding.featureSubtitle',
                  'The current release focuses on local scraping, review, and export'
                )}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
              <div className="bg-x-dark border border-x-border rounded-lg p-6">
                <div className="text-4xl mb-3">🧭</div>
                <h3 className="text-lg font-semibold text-x-light mb-2">
                  {t('onboarding.featureGuided', 'Guided Scraping')}
                </h3>
                <p className="text-x-gray text-sm">
                  {t(
                    'onboarding.featureGuidedDesc',
                    'Choose profile or bookmarks, then collect by count, recent days, or date range.'
                  )}
                </p>
              </div>

              <div className="bg-x-dark border border-x-border rounded-lg p-6">
                <div className="text-4xl mb-3">🧾</div>
                <h3 className="text-lg font-semibold text-x-light mb-2">
                  {t('onboarding.featureDiagnostics', 'Run Logs')}
                </h3>
                <p className="text-x-gray text-sm">
                  {t(
                    'onboarding.featureDiagnosticsDesc',
                    'Review progress, warnings, and diagnostics when X changes or a scrape is incomplete.'
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
                    'Export your data as JSON, Markdown, or Word documents for local archiving.'
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
                <li>• {t('onboarding.tip3', 'Review run logs if a scrape looks incomplete')}</li>
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
                isChromeInstalled === false)
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
