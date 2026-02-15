import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useScrapeStore, ScrapeConfig as ScrapeConfigType } from '../../stores/scrapeStore';
import { useAuthStore } from '../../stores/authStore';
import {
  User,
  Bookmark,
  Play,
  Chrome,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Wifi,
  WifiOff,
} from 'lucide-react';

type SourceType = 'profile' | 'bookmarks';
type ModeType = 'count' | 'days' | 'date_range';

function ScrapeConfig() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { startScrape } = useScrapeStore();
  const { status: authStatus, error: authError, connectManual } = useAuthStore();

  const [source, setSource] = useState<SourceType>('profile');
  const [target, setTarget] = useState('');
  const [mode, setMode] = useState<ModeType>('count');
  const [count, setCount] = useState(100);
  const [days, setDays] = useState(7);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [outputFormats, setOutputFormats] = useState({
    json: true,
    markdown: false,
    word: false,
  });

  const isConnected = authStatus === 'connected';
  const isConnecting = authStatus === 'connecting' || authStatus === 'waiting';

  const isValid = () => {
    if (!isConnected) return false;
    if (source === 'profile' && !target.trim()) return false;
    if (mode === 'count' && count <= 0) return false;
    if (mode === 'days' && days <= 0) return false;
    if (mode === 'date_range' && (!startDate || !endDate)) return false;
    if (!outputFormats.json && !outputFormats.markdown && !outputFormats.word) return false;
    return true;
  };

  const handleStart = async () => {
    if (!isValid()) return;

    const config: ScrapeConfigType = {
      type: source,
      target: source === 'profile' ? target : '',
      mode: mode === 'count' ? 'count' : mode === 'days' ? 'days' : 'date_range',
      ...(mode === 'count' && { count }),
      ...(mode === 'days' && { days }),
      ...(mode === 'date_range' && { startDate, endDate }),
    };

    await startScrape(config);
    navigate('/scrape/progress');
  };

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-4">
      <h1 className="text-xl font-semibold text-x-light">
        {t('sidebar.newScrape')}
      </h1>

      {/* Step 1: Connect to Twitter */}
      <div className="bg-x-dark/60 border border-x-border/40 rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            {isConnected ? (
              <Wifi size={16} className="text-green-400" />
            ) : (
              <WifiOff size={16} className="text-x-gray" />
            )}
            <h2 className="text-sm font-semibold text-x-light">
              {t('scrape.connectTitle', 'Connect to Twitter/X')}
            </h2>
          </div>
          {isConnected && (
            <span className="flex items-center gap-1.5 text-xs text-green-400 font-medium bg-green-500/10 px-2.5 py-1 rounded-full">
              <CheckCircle2 size={12} />
              Connected
            </span>
          )}
        </div>

        {authStatus === 'disconnected' && (
          <div className="space-y-3">
            <p className="text-xs text-x-gray">
              {t('scrape.connectDesc', 'A Chrome window will open. Log into your X account there, then come back here.')}
            </p>
            <button
              onClick={connectManual}
              className="w-full py-2.5 px-4 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 bg-x-blue hover:bg-x-blue/80 text-white"
            >
              <Chrome size={16} />
              {t('scrape.connectButton', 'Open Browser & Login')}
            </button>
          </div>
        )}

        {authStatus === 'connecting' && (
          <div className="flex items-center gap-2.5 py-2">
            <Loader2 size={16} className="text-x-blue animate-spin" />
            <span className="text-sm text-x-gray">Starting browser...</span>
          </div>
        )}

        {authStatus === 'waiting' && (
          <div className="space-y-2">
            <div className="flex items-center gap-2.5 py-2">
              <Loader2 size={16} className="text-amber-400 animate-spin" />
              <span className="text-sm text-amber-400 font-medium">Waiting for login...</span>
            </div>
            <p className="text-xs text-x-gray">
              {t('scrape.waitingDesc', 'Log into your X account in the Chrome window that opened. This page will update automatically when you\'re done.')}
            </p>
          </div>
        )}

        {authStatus === 'connected' && (
          <p className="text-xs text-x-gray">
            {t('scrape.connectedDesc', 'You\'re connected. Configure your scrape below and hit Start.')}
          </p>
        )}

        {authStatus === 'error' && (
          <div className="space-y-3">
            <div className="flex items-start gap-2 py-1">
              <AlertCircle size={14} className="text-red-400 mt-0.5 flex-shrink-0" />
              <span className="text-xs text-red-400">{authError}</span>
            </div>
            <button
              onClick={connectManual}
              className="w-full py-2.5 px-4 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 bg-x-blue hover:bg-x-blue/80 text-white"
            >
              <Chrome size={16} />
              Try Again
            </button>
          </div>
        )}
      </div>

      {/* Step 2: Scrape Configuration */}
      <div className={`bg-x-dark/60 border border-x-border/40 rounded-xl p-5 space-y-5 transition-opacity ${isConnected ? 'opacity-100' : 'opacity-40 pointer-events-none'}`}>
        {/* Source */}
        <div>
          <label className="block text-xs font-medium text-x-gray mb-2">
            {t('scrape.source')}
          </label>
          <div className="flex gap-2">
            <button
              onClick={() => setSource('profile')}
              className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
                source === 'profile'
                  ? 'bg-x-blue text-white'
                  : 'bg-x-darker/80 text-x-gray hover:text-x-light border border-x-border/40'
              }`}
            >
              <User size={16} />
              {t('scrape.profile')}
            </button>
            <button
              onClick={() => setSource('bookmarks')}
              className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
                source === 'bookmarks'
                  ? 'bg-x-blue text-white'
                  : 'bg-x-darker/80 text-x-gray hover:text-x-light border border-x-border/40'
              }`}
            >
              <Bookmark size={16} />
              {t('scrape.bookmarks')}
            </button>
          </div>
        </div>

        {/* Target */}
        {source === 'profile' && (
          <div>
            <label htmlFor="target" className="block text-xs font-medium text-x-gray mb-1.5">
              {t('scrape.targetUsername')}
            </label>
            <div className="flex items-center gap-2">
              <span className="text-x-gray text-sm">@</span>
              <input
                id="target"
                type="text"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="username"
                className="flex-1 input-field"
              />
            </div>
          </div>
        )}

        {/* Mode */}
        <div>
          <label className="block text-xs font-medium text-x-gray mb-2">
            {t('scrape.mode')}
          </label>
          <div className="flex gap-1 bg-x-darker/80 p-1 rounded-lg">
            <button
              onClick={() => setMode('count')}
              className={`flex-1 py-2 px-3 rounded-md text-xs font-medium transition-colors ${
                mode === 'count'
                  ? 'bg-x-blue text-white'
                  : 'text-x-gray hover:text-x-light'
              }`}
            >
              By Count
            </button>
            <button
              onClick={() => setMode('days')}
              className={`flex-1 py-2 px-3 rounded-md text-xs font-medium transition-colors ${
                mode === 'days'
                  ? 'bg-x-blue text-white'
                  : 'text-x-gray hover:text-x-light'
              }`}
            >
              Last N Days
            </button>
            <button
              onClick={() => setMode('date_range')}
              className={`flex-1 py-2 px-3 rounded-md text-xs font-medium transition-colors ${
                mode === 'date_range'
                  ? 'bg-x-blue text-white'
                  : 'text-x-gray hover:text-x-light'
              }`}
            >
              Date Range
            </button>
          </div>
        </div>

        {/* Mode inputs */}
        {mode === 'count' && (
          <div>
            <label htmlFor="count" className="block text-xs font-medium text-x-gray mb-1.5">
              Number of Tweets
            </label>
            <input
              id="count"
              type="number"
              value={count}
              onChange={(e) => setCount(parseInt(e.target.value) || 0)}
              min="1"
              className="input-field"
            />
          </div>
        )}

        {mode === 'days' && (
          <div>
            <label htmlFor="days" className="block text-xs font-medium text-x-gray mb-1.5">
              Number of Days
            </label>
            <input
              id="days"
              type="number"
              value={days}
              onChange={(e) => setDays(parseInt(e.target.value) || 0)}
              min="1"
              className="input-field"
            />
          </div>
        )}

        {mode === 'date_range' && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="startDate" className="block text-xs font-medium text-x-gray mb-1.5">
                {t('scrape.startDate')}
              </label>
              <input
                id="startDate"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="input-field"
              />
            </div>
            <div>
              <label htmlFor="endDate" className="block text-xs font-medium text-x-gray mb-1.5">
                {t('scrape.endDate')}
              </label>
              <input
                id="endDate"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="input-field"
              />
            </div>
          </div>
        )}

        {/* Output format */}
        <div>
          <label className="block text-xs font-medium text-x-gray mb-2">
            {t('scrape.outputFormat')}
          </label>
          <div className="space-y-1.5">
            {(['json', 'markdown', 'word'] as const).map((fmt) => (
              <label
                key={fmt}
                className="flex items-center gap-3 p-2.5 bg-x-darker/50 rounded-lg cursor-pointer hover:bg-x-darker/80 transition-colors"
              >
                <input
                  type="checkbox"
                  checked={outputFormats[fmt]}
                  onChange={(e) =>
                    setOutputFormats({ ...outputFormats, [fmt]: e.target.checked })
                  }
                  className="w-3.5 h-3.5 accent-x-blue rounded"
                />
                <span className="text-sm text-x-light capitalize">
                  {fmt === 'word' ? 'Word Document' : fmt.charAt(0).toUpperCase() + fmt.slice(1)}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Start */}
        <button
          onClick={handleStart}
          disabled={!isValid()}
          className={`w-full py-3 px-5 rounded-lg text-sm font-semibold transition-all flex items-center justify-center gap-2 ${
            isValid()
              ? 'bg-x-blue hover:bg-x-blue/80 text-white'
              : 'bg-x-border/30 text-x-gray cursor-not-allowed'
          }`}
        >
          <Play size={16} />
          {t('common.start')} Scrape
        </button>
      </div>
    </div>
  );
}

export default ScrapeConfig;
