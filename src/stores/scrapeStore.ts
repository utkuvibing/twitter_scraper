import { create } from 'zustand';
import { invoke } from '@tauri-apps/api/core';

export interface TweetData {
  id: string;
  text: string;
  date: number;
  date_str: string;
  media_urls: string[];
  tweet_url: string;
  has_article: boolean;
  likes: number;
  retweets: number;
  replies: number;
  views: number;
}

export interface ScrapeConfig {
  type: 'profile' | 'bookmarks';
  target: string;
  mode: 'count' | 'days' | 'date_range' | 'all';
  count?: number;
  days?: number;
  startDate?: string;
  endDate?: string;
}

export interface ScrapeProgress {
  collected: number;
  target: number | null;
}

export type ScrapeStatus = 'idle' | 'running' | 'paused' | 'completed' | 'error';

interface ScrapeState {
  status: ScrapeStatus;
  tweets: TweetData[];
  progress: ScrapeProgress;
  currentScrapeId: string | null;
  error: string | null;
  scrapeConfig: ScrapeConfig | null;

  // Actions
  startScrape: (config: ScrapeConfig) => Promise<void>;
  updateProgress: (data: ScrapeProgress) => void;
  addTweet: (tweet: TweetData) => void;
  updateTweet: (tweet: TweetData) => void;
  setComplete: (tweets: TweetData[]) => void;
  setError: (msg: string) => void;
  pause: () => Promise<void>;
  resume: () => Promise<void>;
  cancel: () => Promise<void>;
  reset: () => void;
}

export const useScrapeStore = create<ScrapeState>((set, get) => ({
  status: 'idle',
  tweets: [],
  progress: {
    collected: 0,
    target: null,
  },
  currentScrapeId: null,
  error: null,
  scrapeConfig: null,

  startScrape: async (config: ScrapeConfig) => {
    // Set UI state first
    set({
      status: 'running',
      scrapeConfig: config,
      tweets: [],
      progress: {
        collected: 0,
        target: config.mode === 'count' ? config.count || null : null,
      },
      error: null,
    });

    // Call backend to actually start the scrape
    try {
      const result = await invoke<{ success: boolean; message: string; scrape_id: string | null }>(
        'start_scrape',
        {
          config: {
            type: config.type,
            target: config.target,
            mode: config.mode,
            count: config.count ?? null,
            days: config.days ?? null,
            start_date: config.startDate ?? null,
            end_date: config.endDate ?? null,
          },
        }
      );
      if (result.scrape_id) {
        set({ currentScrapeId: result.scrape_id });
      }
    } catch (err) {
      console.error('Failed to start scrape:', err);
      set({
        status: 'error',
        error: typeof err === 'string' ? err : 'Failed to start scrape',
      });
    }
  },

  updateProgress: (data: ScrapeProgress) => {
    set((state) => ({
      progress: {
        collected: data.collected,
        target: data.target !== undefined ? data.target : state.progress.target,
      },
    }));
  },

  addTweet: (tweet: TweetData) => {
    set((state) => {
      // Check if tweet already exists
      if (state.tweets.some((t) => t.id === tweet.id)) {
        return state; // Skip duplicate
      }
      return {
        tweets: [...state.tweets, tweet],
        progress: {
          ...state.progress,
          collected: state.progress.collected + 1,
        },
      };
    });
  },

  updateTweet: (tweet: TweetData) => {
    set((state) => {
      const idx = state.tweets.findIndex((t) => t.id === tweet.id);
      if (idx === -1) {
        // Not found, add it
        return { tweets: [...state.tweets, tweet] };
      }
      // Replace with updated version (has full text/article content)
      const updated = [...state.tweets];
      updated[idx] = tweet;
      return { tweets: updated };
    });
  },

  setComplete: (tweets: TweetData[]) => {
    set({
      status: 'completed',
      tweets: tweets.length > 0 ? tweets : get().tweets,
      progress: {
        collected: tweets.length > 0 ? tweets.length : get().tweets.length,
        target: tweets.length > 0 ? tweets.length : get().tweets.length,
      },
    });
  },

  setError: (msg: string) => {
    set({
      status: 'error',
      error: msg,
    });
  },

  pause: async () => {
    try {
      await invoke('pause_scrape');
      set({ status: 'paused' });
    } catch (err) {
      console.error('Failed to pause:', err);
    }
  },

  resume: async () => {
    try {
      await invoke('resume_scrape');
      set({ status: 'running' });
    } catch (err) {
      console.error('Failed to resume:', err);
    }
  },

  cancel: async () => {
    try {
      await invoke('cancel_scrape');
    } catch (err) {
      console.error('Failed to cancel:', err);
    }
    set({
      status: 'idle',
      currentScrapeId: null,
    });
  },

  reset: () => {
    set({
      status: 'idle',
      tweets: [],
      progress: {
        collected: 0,
        target: null,
      },
      currentScrapeId: null,
      error: null,
      scrapeConfig: null,
    });
  },
}));
