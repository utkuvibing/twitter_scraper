import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { invoke } from '@tauri-apps/api/core';
import { listen, UnlistenFn } from '@tauri-apps/api/event';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import type { TweetData } from '../../stores/scrapeStore';

interface AIAnalysisProps {
  tweets?: TweetData[];
}

interface ScrapeRecord {
  id: string;
  target_username: string;
  scrape_type: string;
  mode: string;
  started_at: string;
  completed_at: string | null;
  tweet_count: number;
  status: string;
}

interface AnalysisResult {
  sentiment: {
    positive: number;
    negative: number;
    neutral: number;
  };
  topics: string[];
  writingStyle: string;
  recommendations: string[];
  summary: string;
}

export default function AIAnalysis({ tweets: propTweets }: AIAnalysisProps) {
  const { t } = useTranslation();
  const [apiKey, setApiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scrapeHistory, setScrapeHistory] = useState<ScrapeRecord[]>([]);
  const [selectedScrapeId, setSelectedScrapeId] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(true);

  // Load scrape history for the selector
  useEffect(() => {
    const loadHistory = async () => {
      try {
        setHistoryLoading(true);
        const records = await invoke<ScrapeRecord[]>('get_scrape_history');
        const completed = records.filter((r) => r.status === 'completed' && r.tweet_count > 0);
        setScrapeHistory(completed);
        if (completed.length > 0) {
          setSelectedScrapeId(completed[0].id);
        }
      } catch (err) {
        console.error('Failed to load scrape history:', err);
      } finally {
        setHistoryLoading(false);
      }
    };
    loadHistory();
  }, []);

  // Listen for analysis results from the sidecar
  useEffect(() => {
    let unlisten: UnlistenFn | undefined;

    const setup = async () => {
      unlisten = await listen<any>('analysis-result', (event) => {
        const data = event.payload;
        if (data.error) {
          setError(data.error);
          setIsAnalyzing(false);
          return;
        }

        // Parse the analysis result from sidecar
        try {
          const result: AnalysisResult = {
            sentiment: data.sentiment || { positive: 0, negative: 0, neutral: 0 },
            topics: data.topics || [],
            writingStyle: data.writing_style || data.writingStyle || '',
            recommendations: data.recommendations || [],
            summary: data.summary || '',
          };
          setAnalysisResult(result);
          setError(null);
        } catch (err) {
          setError('Failed to parse analysis results');
        }
        setIsAnalyzing(false);
      });
    };

    setup();
    return () => {
      if (unlisten) unlisten();
    };
  }, []);

  const handleAnalyze = async () => {
    if (!apiKey.trim()) {
      setError(t('ai.errorNoKey', 'Please enter your OpenAI API key'));
      return;
    }

    if (!selectedScrapeId) {
      setError(t('ai.errorNoScrape', 'Please select a scrape to analyze'));
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    setAnalysisResult(null);

    try {
      await invoke('analyze_with_ai', {
        scrapeId: selectedScrapeId,
        apiKey: apiKey,
      });
      // Results will come via the 'analysis-result' event listener
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setError(errorMessage);
      setIsAnalyzing(false);
    }
  };

  const sentimentData = analysisResult
    ? [
        {
          name: t('ai.positive', 'Positive'),
          value: analysisResult.sentiment.positive,
          color: '#10b981',
        },
        {
          name: t('ai.negative', 'Negative'),
          value: analysisResult.sentiment.negative,
          color: '#ef4444',
        },
        {
          name: t('ai.neutral', 'Neutral'),
          value: analysisResult.sentiment.neutral,
          color: '#6b7280',
        },
      ]
    : [];

  return (
    <div className="w-full h-full bg-x-darker p-6 overflow-y-auto">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-x-light mb-2">
            {t('ai.title', 'AI Analysis')}
          </h1>
          <p className="text-x-gray text-sm">
            {t(
              'ai.subtitle',
              'Get AI-powered insights about tweet content and engagement'
            )}
          </p>
        </div>

        {/* Scrape Selector */}
        {scrapeHistory.length > 0 && (
          <div className="bg-x-dark border border-x-border rounded-lg p-4 mb-6">
            <label className="block text-sm font-medium text-x-gray mb-2">
              {t('ai.selectScrape', 'Select Scrape to Analyze')}
            </label>
            <select
              value={selectedScrapeId || ''}
              onChange={(e) => setSelectedScrapeId(e.target.value || null)}
              className="w-full bg-x-darker border border-x-border rounded-lg px-4 py-2.5 text-x-light focus:outline-none focus:border-x-blue transition-colors cursor-pointer"
            >
              <option value="">{t('ai.selectPlaceholder', '-- Select a scrape --')}</option>
              {scrapeHistory.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.target_username} - {item.tweet_count} tweets ({item.started_at})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* API Key Input */}
        <div className="bg-x-dark border border-x-border rounded-lg p-6 mb-6">
          <h3 className="text-lg font-semibold text-x-light mb-4">
            {t('ai.apiKeySection', 'OpenAI API Configuration')}
          </h3>
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <input
                type={showApiKey ? 'text' : 'password'}
                placeholder={t('ai.apiKeyPlaceholder', 'sk-...')}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full bg-x-darker border border-x-border rounded-lg px-4 py-2.5 pr-12 text-x-light placeholder-x-gray focus:outline-none focus:border-x-blue transition-colors font-mono text-sm"
              />
              <button
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-x-gray hover:text-x-light transition-colors"
              >
                {showApiKey ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                )}
              </button>
            </div>
            <button
              onClick={handleAnalyze}
              disabled={isAnalyzing || !apiKey.trim() || !selectedScrapeId}
              className="px-6 py-2.5 bg-x-blue text-white rounded-lg hover:bg-opacity-80 transition-all font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isAnalyzing ? (
                <>
                  <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  {t('ai.analyzing', 'Analyzing...')}
                </>
              ) : (
                t('ai.runAnalysis', 'Run Analysis')
              )}
            </button>
          </div>
          <p className="text-xs text-x-gray mt-2">
            {t('ai.apiKeyNote', 'Your API key is stored locally and never sent to our servers')}
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-900 bg-opacity-20 border border-red-600 rounded-lg p-4 mb-6 flex items-start gap-3">
            <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {isAnalyzing && (
          <div className="bg-x-dark border border-x-border rounded-lg p-12 text-center">
            <div className="w-16 h-16 border-4 border-x-blue border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-x-light font-medium">
              {t('ai.analyzingTweets', 'Analyzing your tweets...')}
            </p>
            <p className="text-x-gray text-sm mt-1">
              {t('ai.analyzingDesc', 'This may take a moment')}
            </p>
          </div>
        )}

        {/* Analysis Results */}
        {!isAnalyzing && analysisResult && (
          <div className="space-y-6">
            {/* Executive Summary */}
            <div className="bg-x-dark border border-x-border rounded-lg p-6">
              <h3 className="text-lg font-semibold text-x-light mb-3 flex items-center gap-2">
                <span className="text-2xl">📝</span>
                {t('ai.executiveSummary', 'Executive Summary')}
              </h3>
              <p className="text-x-light leading-relaxed">
                {analysisResult.summary}
              </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Sentiment Analysis */}
              <div className="bg-x-dark border border-x-border rounded-lg p-6">
                <h3 className="text-lg font-semibold text-x-light mb-4 flex items-center gap-2">
                  <span className="text-2xl">😊</span>
                  {t('ai.sentimentAnalysis', 'Sentiment Analysis')}
                </h3>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={sentimentData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, value }) => `${name}: ${value}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {sentimentData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#15202b',
                        border: '1px solid #2f3336',
                        borderRadius: '8px',
                        color: '#e7e9ea',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Topics */}
              <div className="bg-x-dark border border-x-border rounded-lg p-6">
                <h3 className="text-lg font-semibold text-x-light mb-4 flex items-center gap-2">
                  <span className="text-2xl">🏷️</span>
                  {t('ai.topics', 'Main Topics')}
                </h3>
                <div className="flex flex-wrap gap-2">
                  {analysisResult.topics.map((topic, index) => (
                    <span
                      key={index}
                      className="px-4 py-2 bg-x-blue bg-opacity-20 text-x-blue border border-x-blue rounded-full text-sm font-medium"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Writing Style */}
            <div className="bg-x-dark border border-x-border rounded-lg p-6">
              <h3 className="text-lg font-semibold text-x-light mb-3 flex items-center gap-2">
                <span className="text-2xl">✍️</span>
                {t('ai.writingStyle', 'Writing Style Analysis')}
              </h3>
              <p className="text-x-light leading-relaxed">
                {analysisResult.writingStyle}
              </p>
            </div>

            {/* Recommendations */}
            <div className="bg-x-dark border border-x-border rounded-lg p-6">
              <h3 className="text-lg font-semibold text-x-light mb-4 flex items-center gap-2">
                <span className="text-2xl">💡</span>
                {t('ai.recommendations', 'Content Recommendations')}
              </h3>
              <ul className="space-y-3">
                {analysisResult.recommendations.map((rec, index) => (
                  <li
                    key={index}
                    className="flex items-start gap-3 p-3 bg-x-darker rounded-lg border border-x-border"
                  >
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-x-blue bg-opacity-20 text-x-blue flex items-center justify-center text-sm font-bold">
                      {index + 1}
                    </span>
                    <span className="flex-1 text-x-light">{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!isAnalyzing && !analysisResult && !error && (
          <div className="bg-x-dark border border-x-border rounded-lg p-12 text-center">
            <div className="text-6xl mb-4">🤖</div>
            <h3 className="text-xl font-semibold text-x-light mb-2">
              {t('ai.readyToAnalyze', 'Ready to Analyze')}
            </h3>
            <p className="text-x-gray">
              {selectedScrapeId
                ? t('ai.readyDesc', 'Enter your OpenAI API key and click Run Analysis to get started')
                : t('ai.noScrapeSelected', 'Select a completed scrape above, then enter your API key')}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
