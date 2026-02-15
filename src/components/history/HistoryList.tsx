import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { invoke } from '@tauri-apps/api/core';
import { useScrapeStore } from '../../stores/scrapeStore';

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

export default function HistoryList() {
  const { t } = useTranslation();
  const lastCompletedAt = useScrapeStore((s) => s.lastCompletedAt);
  const [history, setHistory] = useState<ScrapeRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [exportingId, setExportingId] = useState<string | null>(null);

  const loadHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const records = await invoke<ScrapeRecord[]>('get_scrape_history');
      setHistory(records);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      console.error('Failed to load history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [lastCompletedAt]);

  const filteredHistory = history.filter((item) =>
    item.target_username.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDelete = async (id: string) => {
    try {
      await invoke('delete_scrape', { scrapeId: id });
      setHistory(history.filter((item) => item.id !== id));
      setDeleteConfirmId(null);
      setExpandedId(null);
    } catch (err) {
      console.error('Failed to delete scrape:', err);
    }
  };

  const handleExport = async (item: ScrapeRecord) => {
    try {
      setExportingId(item.id);
      await invoke('export_results', {
        config: {
          format: 'json',
          scrape_id: item.id,
          target: item.target_username,
        },
      });
    } catch (err) {
      console.error('Failed to export:', err);
    } finally {
      setExportingId(null);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-500';
      case 'error':
      case 'cancelled':
        return 'text-red-500';
      case 'running':
        return 'text-yellow-500';
      default:
        return 'text-x-gray';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return '\u2713';
      case 'error':
      case 'cancelled':
        return '\u2715';
      case 'running':
        return '\u26A0';
      default:
        return '\u2022';
    }
  };

  if (loading) {
    return (
      <div className="w-full h-full bg-x-darker p-6 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-x-blue border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-x-gray">{t('common.loading', 'Loading...')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full bg-x-darker p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-x-light mb-2">
              {t('history.title', 'Scrape History')}
            </h1>
            <p className="text-x-gray text-sm">
              {t('history.subtitle', 'View and manage your past scraping sessions')}
            </p>
          </div>
          <button
            onClick={loadHistory}
            className="px-4 py-2 bg-x-dark border border-x-border text-x-light rounded-lg hover:border-x-blue transition-all text-sm font-medium"
          >
            {t('history.refresh', 'Refresh')}
          </button>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mb-4 bg-red-900 bg-opacity-20 border border-red-600 rounded-lg p-3 flex items-center gap-2">
            <span className="text-red-400">{error}</span>
            <button onClick={loadHistory} className="text-x-blue hover:underline text-sm ml-auto">
              {t('common.retry', 'Retry')}
            </button>
          </div>
        )}

        {/* Search Bar */}
        <div className="mb-4">
          <input
            type="text"
            placeholder={t('history.search', 'Search by username...')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-x-dark border border-x-border rounded-lg px-4 py-2.5 text-x-light placeholder-x-gray focus:outline-none focus:border-x-blue transition-colors"
          />
        </div>

        {/* History List */}
        {filteredHistory.length === 0 ? (
          <div className="bg-x-dark border border-x-border rounded-lg p-12 text-center">
            <div className="text-6xl mb-4">📊</div>
            <h3 className="text-xl font-semibold text-x-light mb-2">
              {searchQuery
                ? t('history.noResults', 'No matching history found')
                : t('history.empty', 'No scraping history yet')}
            </h3>
            <p className="text-x-gray">
              {searchQuery
                ? t('history.tryDifferent', 'Try a different search term')
                : t('history.emptyDesc', 'Your completed scrapes will appear here')}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredHistory.map((item) => (
              <div
                key={item.id}
                className="bg-x-dark border border-x-border rounded-lg overflow-hidden hover:border-x-blue transition-colors"
              >
                {/* Main Row */}
                <div
                  className="flex items-center gap-4 p-4 cursor-pointer"
                  onClick={() =>
                    setExpandedId(expandedId === item.id ? null : item.id)
                  }
                >
                  {/* Status Icon */}
                  <div
                    className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-bold ${getStatusColor(
                      item.status
                    )}`}
                  >
                    {getStatusIcon(item.status)}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className="text-lg font-semibold text-x-light">
                        {item.target_username}
                      </h3>
                      <span className="px-2 py-0.5 bg-x-darker text-x-gray text-xs rounded border border-x-border">
                        {item.scrape_type}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-x-gray">
                      <span>{item.started_at}</span>
                      <span>•</span>
                      <span>{item.tweet_count} tweets</span>
                      <span>•</span>
                      <span>{item.mode}</span>
                    </div>
                  </div>

                  {/* Expand Arrow */}
                  <div className="flex-shrink-0 text-x-gray">
                    <svg
                      className={`w-5 h-5 transition-transform ${
                        expandedId === item.id ? 'rotate-180' : ''
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedId === item.id && (
                  <div className="border-t border-x-border bg-x-darker p-4">
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <div className="text-xs text-x-gray mb-1">
                          {t('history.scrapeId', 'Scrape ID')}
                        </div>
                        <div className="text-sm text-x-light font-mono">
                          {item.id}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-x-gray mb-1">
                          {t('history.status', 'Status')}
                        </div>
                        <div className={`text-sm font-medium ${getStatusColor(item.status)}`}>
                          {item.status}
                        </div>
                      </div>
                      {item.completed_at && (
                        <div>
                          <div className="text-xs text-x-gray mb-1">
                            {t('history.completedAt', 'Completed At')}
                          </div>
                          <div className="text-sm text-x-light">
                            {item.completed_at}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-3">
                      {item.status === 'completed' && (
                        <button
                          onClick={() => handleExport(item)}
                          disabled={exportingId === item.id}
                          className="px-4 py-2 bg-x-blue text-white rounded-lg hover:bg-opacity-80 transition-all text-sm font-medium disabled:opacity-50"
                        >
                          {exportingId === item.id
                            ? t('history.exporting', 'Exporting...')
                            : t('history.reExport', 'Re-export Data')}
                        </button>
                      )}

                      {deleteConfirmId === item.id ? (
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleDelete(item.id)}
                            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-all text-sm font-medium"
                          >
                            {t('history.confirmDelete', 'Confirm Delete')}
                          </button>
                          <button
                            onClick={() => setDeleteConfirmId(null)}
                            className="px-4 py-2 bg-x-dark border border-x-border text-x-light rounded-lg hover:border-x-gray transition-all text-sm font-medium"
                          >
                            {t('common.cancel', 'Cancel')}
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setDeleteConfirmId(item.id)}
                          className="px-4 py-2 bg-x-dark border border-red-600 text-red-500 rounded-lg hover:bg-red-600 hover:text-white transition-all text-sm font-medium"
                        >
                          {t('history.delete', 'Delete')}
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
