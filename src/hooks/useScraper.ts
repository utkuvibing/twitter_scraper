import { useEffect, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen, UnlistenFn } from '@tauri-apps/api/event';
import { useScrapeStore, ScrapeConfig, TweetData } from '../stores/scrapeStore';
import { useLicense } from './useLicense';

interface ScrapeProgressEvent {
  collected: number;
  target?: number | null;
}

interface ScrapeCompleteEvent {
  tweets: TweetData[];
}

interface ScrapeErrorEvent {
  message: string;
}

export function useScraper() {
  const {
    status,
    tweets,
    progress,
    error,
    scrapeConfig,
    currentScrapeId,
    startScrape: startScrapeAction,
    updateProgress,
    setComplete,
    setError,
    pause,
    resume,
    cancel,
    reset,
  } = useScrapeStore();

  const { getMaxTweetsPerScrape, canExport } = useLicense();

  const startScrape = useCallback(
    async (config: ScrapeConfig) => {
      // Check license limits before starting
      const maxTweets = getMaxTweetsPerScrape();
      if (maxTweets !== null && config.mode === 'count' && config.count && config.count > maxTweets) {
        setError(
          `Free tier limit: max ${maxTweets} tweets per scrape. Upgrade to Pro for unlimited.`
        );
        return;
      }

      try {
        startScrapeAction(config);
        const result = await invoke<{ success: boolean; scrape_id?: string; message: string }>(
          'start_scrape',
          { config }
        );

        // Store the backend scrape_id if returned
        if (result.scrape_id) {
          useScrapeStore.setState({ currentScrapeId: result.scrape_id });
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : String(err);
        setError(errorMessage);
      }
    },
    [startScrapeAction, setError, getMaxTweetsPerScrape]
  );

  const pauseScrape = useCallback(async () => {
    try {
      await invoke('pause_scrape');
      pause();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setError(errorMessage);
    }
  }, [pause, setError]);

  const resumeScrape = useCallback(async () => {
    try {
      await invoke('resume_scrape');
      resume();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setError(errorMessage);
    }
  }, [resume, setError]);

  const cancelScrape = useCallback(async () => {
    try {
      await invoke('cancel_scrape');
      cancel();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setError(errorMessage);
    }
  }, [cancel, setError]);

  const exportResults = useCallback(
    async (format: 'json' | 'csv' | 'excel') => {
      // Check license for export format
      if (!canExport(format)) {
        throw new Error(
          `Export to ${format.toUpperCase()} requires a Pro license. Only JSON export is available on the free tier.`
        );
      }

      try {
        const result = await invoke<{ path: string }>('export_results', {
          config: { format },
        });
        return result.path;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : String(err);
        throw new Error(errorMessage);
      }
    },
    [canExport]
  );

  useEffect(() => {
    let unlistenProgress: UnlistenFn | undefined;
    let unlistenComplete: UnlistenFn | undefined;
    let unlistenError: UnlistenFn | undefined;

    const setupListeners = async () => {
      unlistenProgress = await listen<ScrapeProgressEvent>('scrape-progress', (event) => {
        updateProgress({
          collected: event.payload.collected,
          target: event.payload.target ?? null,
        });
      });

      unlistenComplete = await listen<ScrapeCompleteEvent>('scrape-complete', async (event) => {
        const completedTweets = event.payload.tweets;
        setComplete(completedTweets);

        // Save tweets to SQLite for persistence
        const scrapeId = useScrapeStore.getState().currentScrapeId;
        if (scrapeId && completedTweets.length > 0) {
          try {
            await invoke('save_scrape_tweets', {
              scrapeId,
              tweets: completedTweets,
            });
          } catch (err) {
            console.error('Failed to save tweets to DB:', err);
          }
        }
      });

      unlistenError = await listen<ScrapeErrorEvent>('scrape-error', (event) => {
        setError(event.payload.message);
      });
    };

    setupListeners();

    return () => {
      if (unlistenProgress) unlistenProgress();
      if (unlistenComplete) unlistenComplete();
      if (unlistenError) unlistenError();
    };
  }, [updateProgress, setComplete, setError]);

  return {
    status,
    tweets,
    progress,
    error,
    scrapeConfig,
    currentScrapeId,
    startScrape,
    pauseScrape,
    resumeScrape,
    cancelScrape,
    exportResults,
    reset,
  };
}
