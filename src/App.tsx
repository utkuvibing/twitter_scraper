import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import TitleBar from './components/layout/TitleBar';
import Dashboard from './components/dashboard/Dashboard';
import ScrapeConfig from './components/scrape/ScrapeConfig';
import ScrapeProgress from './components/scrape/ScrapeProgress';
import ScrapeResults from './components/scrape/ScrapeResults';
import HistoryList from './components/history/HistoryList';
import AnalyticsDashboard from './components/analytics/AnalyticsDashboard';
import AIAnalysis from './components/ai/AIAnalysis';
import SettingsPanel from './components/settings/SettingsPanel';
import OnboardingWizard from './components/onboarding/OnboardingWizard';
import { useScrapeStore } from './stores/scrapeStore';
import { useScrapeEvents } from './hooks/useScrapeEvents';
import { useLogEvents } from './hooks/useLogEvents';

function App() {
  const [showOnboarding, setShowOnboarding] = useState(
    !localStorage.getItem('onboarding_completed')
  );
  const { tweets } = useScrapeStore();

  // Global event listeners - work regardless of which page user is on
  useScrapeEvents();
  useLogEvents();

  const handleOnboardingComplete = () => {
    localStorage.setItem('onboarding_completed', 'true');
    setShowOnboarding(false);
  };

  return (
    <BrowserRouter>
      {showOnboarding && (
        <OnboardingWizard onComplete={handleOnboardingComplete} />
      )}
      <div className="h-screen flex flex-col bg-x-darker text-x-light overflow-hidden">
        <TitleBar />
        <div className="flex-1 flex overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/scrape" element={<ScrapeConfig />} />
              <Route path="/scrape/progress" element={<ScrapeProgress />} />
              <Route path="/scrape/results" element={<ScrapeResults />} />
              <Route path="/history" element={<HistoryList />} />
              <Route path="/analytics" element={<AnalyticsDashboard tweets={tweets} />} />
              <Route path="/ai" element={<AIAnalysis />} />
              <Route path="/settings" element={<SettingsPanel />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
