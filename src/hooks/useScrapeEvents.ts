import { useEffect } from 'react';
import { listen } from '@tauri-apps/api/event';
import { useScrapeStore } from '../stores/scrapeStore';
import { useAuthStore } from '../stores/authStore';

/**
 * Global hook that listens for Tauri sidecar events and updates stores.
 * Must be called once at the App level so events are captured regardless of current page.
 */
export function useScrapeEvents() {
  const { addTweet, updateTweet, updateProgress, setComplete, setError } = useScrapeStore();
  const { setConnected, setWaiting, setError: setAuthError } = useAuthStore();

  useEffect(() => {
    const unlisteners: (() => void)[] = [];

    const setup = async () => {
      // Listen for sidecar log messages
      const unlistenLog = await listen<any>('sidecar-log', (event) => {
        const data = event.payload;
        console.log('[Sidecar]', data.level || 'info', data.message || '');
      });
      unlisteners.push(unlistenLog);

      // Listen for progress updates from sidecar
      const unlisten1 = await listen<any>('scrape-progress', (event) => {
        const data = event.payload;
        if (data.tweet) {
          addTweet({
            id: data.tweet.id || `tweet_${Date.now()}_${Math.random()}`,
            text: data.tweet.text || '',
            date: data.tweet.date || 0,
            date_str: data.tweet.date_str || '',
            media_urls: data.tweet.media_urls || [],
            tweet_url: data.tweet.tweet_url || '',
            has_article: data.tweet.has_article || false,
            likes: data.tweet.likes || 0,
            retweets: data.tweet.retweets || 0,
            replies: data.tweet.replies || 0,
            views: data.tweet.views || 0,
          });
        }
        if (data.collected !== undefined) {
          updateProgress({
            collected: data.collected,
            target: data.target ?? null,
          });
        }
      });
      unlisteners.push(unlisten1);

      // Listen for individual tweet updates (full text/article content)
      const unlisten1b = await listen<any>('tweet-update', (event) => {
        const data = event.payload;
        if (data.tweet) {
          updateTweet({
            id: data.tweet.id || '',
            text: data.tweet.text || '',
            date: data.tweet.date || 0,
            date_str: data.tweet.date_str || '',
            media_urls: data.tweet.media_urls || [],
            tweet_url: data.tweet.tweet_url || '',
            has_article: data.tweet.has_article || false,
            likes: data.tweet.likes || 0,
            retweets: data.tweet.retweets || 0,
            replies: data.tweet.replies || 0,
            views: data.tweet.views || 0,
          });
        }
      });
      unlisteners.push(unlisten1b);

      // Listen for scrape completion (lightweight - no tweets payload)
      const unlisten2 = await listen<any>('scrape-complete', (event) => {
        const data = event.payload;
        console.log('[SCRAPE-COMPLETE EVENT] received:', JSON.stringify(data).slice(0, 200));
        // Complete event is lightweight - tweets already updated via tweet-update events
        // Always call setComplete with empty array to trigger completion using store tweets
        setComplete([]);
      });
      unlisteners.push(unlisten2);

      // Listen for scrape errors
      const unlisten3 = await listen<any>('scrape-error', (event) => {
        const data = event.payload;
        const msg = data.message || data.error || 'Scrape failed';
        // If error is about login, update auth store too
        if (msg.toLowerCase().includes('not logged in') || msg.toLowerCase().includes('login')) {
          setAuthError(msg);
        }
        setError(msg);
      });
      unlisteners.push(unlisten3);

      // Listen for login status events
      const unlisten4 = await listen<any>('login-status', (event) => {
        const data = event.payload;
        if (data.success) {
          setConnected();
        } else {
          setAuthError(data.message || 'Login failed');
        }
      });
      unlisteners.push(unlisten4);

      // Listen for login waiting events (browser opened, waiting for user)
      const unlisten5 = await listen<any>('login-waiting', (event) => {
        const data = event.payload;
        setWaiting(data.message || 'Waiting for login...');
      });
      unlisteners.push(unlisten5);
    };

    setup();

    return () => {
      unlisteners.forEach((fn) => fn());
    };
  }, [addTweet, updateTweet, updateProgress, setComplete, setError, setConnected, setWaiting, setAuthError]);
}
