import { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { invoke } from '@tauri-apps/api/core';
import { useScrapeStore } from '../../stores/scrapeStore';
import {
  BarChart,
  Bar,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import type { TweetData } from '../../stores/scrapeStore';

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

interface AnalyticsDashboardProps {
  tweets?: TweetData[];
}

export default function AnalyticsDashboard({
  tweets: propTweets,
}: AnalyticsDashboardProps) {
  const { t } = useTranslation();
  const lastCompletedAt = useScrapeStore((s) => s.lastCompletedAt);
  const [scrapeHistory, setScrapeHistory] = useState<ScrapeRecord[]>([]);
  const [selectedScrapeId, setSelectedScrapeId] = useState<string | null>(null);
  const [loadedTweets, setLoadedTweets] = useState<TweetData[]>([]);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);

  // Use loaded tweets from DB, or fall back to prop tweets (from current scrape in memory)
  const tweets = selectedScrapeId ? loadedTweets : (propTweets || []);

  // Load scrape history for the selector
  useEffect(() => {
    const loadHistory = async () => {
      try {
        setHistoryLoading(true);
        const records = await invoke<ScrapeRecord[]>('get_scrape_history');
        const completed = records.filter((r) => r.status === 'completed' && r.tweet_count > 0);
        setScrapeHistory(completed);

        // Auto-select first completed scrape if no prop tweets
        if (completed.length > 0 && (!propTweets || propTweets.length === 0)) {
          setSelectedScrapeId(completed[0].id);
        }
      } catch (err) {
        console.error('Failed to load scrape history:', err);
      } finally {
        setHistoryLoading(false);
      }
    };
    loadHistory();
  }, [lastCompletedAt]);

  // Load tweets when scrape is selected
  useEffect(() => {
    if (!selectedScrapeId) {
      setLoadedTweets([]);
      return;
    }

    const loadTweets = async () => {
      setLoading(true);
      try {
        const rawTweets = await invoke<any[]>('get_tweets_for_scrape', {
          scrapeId: selectedScrapeId,
        });
        // Map from DB format to TweetData
        const mapped: TweetData[] = rawTweets.map((t) => ({
          id: t.id || '',
          text: t.text || '',
          date: t.date ? new Date(t.date).getTime() : Date.now(),
          date_str: t.date_str || '',
          media_urls: t.media_urls || [],
          tweet_url: t.tweet_url || '',
          has_article: t.has_article || false,
          likes: t.likes || 0,
          retweets: t.retweets || 0,
          replies: t.replies || 0,
          views: t.views || 0,
        }));
        setLoadedTweets(mapped);
      } catch (err) {
        console.error('Failed to load tweets:', err);
        setLoadedTweets([]);
      } finally {
        setLoading(false);
      }
    };
    loadTweets();
  }, [selectedScrapeId]);

  // Calculate analytics
  const analytics = useMemo(() => {
    if (tweets.length === 0) return null;

    const totalLikes = tweets.reduce((sum, t) => sum + (t.likes || 0), 0);
    const totalRetweets = tweets.reduce((sum, t) => sum + (t.retweets || 0), 0);
    const totalReplies = tweets.reduce((sum, t) => sum + (t.replies || 0), 0);
    const totalViews = tweets.reduce((sum, t) => sum + (t.views || 0), 0);

    // Tweet frequency by date
    const dateFrequency: { [key: string]: number } = {};
    tweets.forEach((tweet) => {
      const date = tweet.date_str || new Date(tweet.date).toISOString().split('T')[0];
      dateFrequency[date] = (dateFrequency[date] || 0) + 1;
    });

    const frequencyData = Object.entries(dateFrequency)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, count]) => ({
        date: new Date(date).toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
        }),
        tweets: count,
      }))
      .slice(-14);

    // Posting times heatmap
    const heatmapData: number[][] = Array.from({ length: 7 }, () =>
      Array(24).fill(0)
    );
    tweets.forEach((tweet) => {
      const d = new Date(tweet.date);
      if (!isNaN(d.getTime())) {
        heatmapData[d.getDay()][d.getHours()]++;
      }
    });

    // Extract hashtags
    const hashtagMap: { [key: string]: number } = {};
    tweets.forEach((tweet) => {
      const hashtags = tweet.text.match(/#\w+/g) || [];
      hashtags.forEach((tag) => {
        const normalized = tag.toLowerCase();
        hashtagMap[normalized] = (hashtagMap[normalized] || 0) + 1;
      });
    });

    const topHashtags = Object.entries(hashtagMap)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([tag, count]) => ({ tag, count }));

    // Extract mentions
    const mentionMap: { [key: string]: number } = {};
    tweets.forEach((tweet) => {
      const mentions = tweet.text.match(/@\w+/g) || [];
      mentions.forEach((mention) => {
        const normalized = mention.toLowerCase();
        mentionMap[normalized] = (mentionMap[normalized] || 0) + 1;
      });
    });

    const topMentions = Object.entries(mentionMap)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([mention, count]) => ({ mention, count }));

    const avgLength =
      tweets.reduce((sum, t) => sum + t.text.length, 0) / tweets.length;
    const mediaCount = tweets.filter((t) => t.media_urls.length > 0).length;
    const articleCount = tweets.filter((t) => t.has_article).length;

    return {
      avgLikes: Math.round(totalLikes / tweets.length),
      avgRetweets: Math.round(totalRetweets / tweets.length),
      avgReplies: Math.round(totalReplies / tweets.length),
      avgViews: Math.round(totalViews / tweets.length),
      frequencyData,
      heatmapData,
      topHashtags,
      topMentions,
      avgLength: Math.round(avgLength),
      mediaPercent: Math.round((mediaCount / tweets.length) * 100),
      articleCount,
    };
  }, [tweets]);

  if (loading || historyLoading) {
    return (
      <div className="w-full h-full bg-x-darker p-6 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-x-blue border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-x-gray">{t('common.loading', 'Loading...')}</p>
        </div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="w-full h-full bg-x-darker p-6">
        <div className="max-w-7xl mx-auto">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-x-light mb-2">
              {t('analytics.title', 'Analytics Dashboard')}
            </h1>
          </div>

          {/* Scrape Selector */}
          {scrapeHistory.length > 0 && (
            <div className="mb-6">
              <ScrapeSelector
                history={scrapeHistory}
                selectedId={selectedScrapeId}
                onSelect={setSelectedScrapeId}
                t={t}
              />
            </div>
          )}

          <div className="bg-x-dark border border-x-border rounded-lg p-12 text-center">
            <div className="text-6xl mb-4">📈</div>
            <h3 className="text-xl font-semibold text-x-light mb-2">
              {t('analytics.noData', 'No data available')}
            </h3>
            <p className="text-x-gray">
              {t(
                'analytics.noDataDesc',
                'Complete a scrape to see analytics and insights'
              )}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const maxHeatmapValue = Math.max(...analytics.heatmapData.flat());

  const getHeatmapColor = (value: number) => {
    if (value === 0) return 'bg-x-dark';
    const intensity = value / maxHeatmapValue;
    if (intensity < 0.25) return 'bg-x-blue bg-opacity-25';
    if (intensity < 0.5) return 'bg-x-blue bg-opacity-50';
    if (intensity < 0.75) return 'bg-x-blue bg-opacity-75';
    return 'bg-x-blue';
  };

  return (
    <div className="w-full h-full bg-x-darker p-6 overflow-y-auto">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-x-light mb-2">
            {t('analytics.title', 'Analytics Dashboard')}
          </h1>
          <p className="text-x-gray text-sm">
            {t('analytics.subtitle', `Insights from ${tweets.length} tweets`)}
          </p>
        </div>

        {/* Scrape Selector */}
        {scrapeHistory.length > 0 && (
          <div className="mb-6">
            <ScrapeSelector
              history={scrapeHistory}
              selectedId={selectedScrapeId}
              onSelect={setSelectedScrapeId}
              t={t}
            />
          </div>
        )}

        {/* Engagement Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-x-dark border border-x-border rounded-lg p-4">
            <div className="text-x-gray text-sm mb-1">
              {t('analytics.avgLikes', 'Avg Likes')}
            </div>
            <div className="text-3xl font-bold text-x-blue">
              {analytics.avgLikes.toLocaleString()}
            </div>
          </div>
          <div className="bg-x-dark border border-x-border rounded-lg p-4">
            <div className="text-x-gray text-sm mb-1">
              {t('analytics.avgRetweets', 'Avg Retweets')}
            </div>
            <div className="text-3xl font-bold text-x-blue">
              {analytics.avgRetweets.toLocaleString()}
            </div>
          </div>
          <div className="bg-x-dark border border-x-border rounded-lg p-4">
            <div className="text-x-gray text-sm mb-1">
              {t('analytics.avgReplies', 'Avg Replies')}
            </div>
            <div className="text-3xl font-bold text-x-blue">
              {analytics.avgReplies.toLocaleString()}
            </div>
          </div>
          <div className="bg-x-dark border border-x-border rounded-lg p-4">
            <div className="text-x-gray text-sm mb-1">
              {t('analytics.avgViews', 'Avg Views')}
            </div>
            <div className="text-3xl font-bold text-x-blue">
              {analytics.avgViews.toLocaleString()}
            </div>
          </div>
        </div>

        {/* Tweet Frequency Chart */}
        <div className="bg-x-dark border border-x-border rounded-lg p-6 mb-6">
          <h3 className="text-lg font-semibold text-x-light mb-4">
            {t('analytics.tweetFrequency', 'Tweet Frequency')}
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={analytics.frequencyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2f3336" />
              <XAxis dataKey="date" stroke="#71767b" />
              <YAxis stroke="#71767b" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#15202b',
                  border: '1px solid #2f3336',
                  borderRadius: '8px',
                  color: '#e7e9ea',
                }}
              />
              <Bar dataKey="tweets" fill="#1d9bf0" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Posting Times Heatmap */}
        <div className="bg-x-dark border border-x-border rounded-lg p-6 mb-6">
          <h3 className="text-lg font-semibold text-x-light mb-4">
            {t('analytics.postingTimes', 'Posting Times Heatmap')}
          </h3>
          <div className="overflow-x-auto">
            <div className="inline-block min-w-full">
              <div className="flex gap-1 mb-2">
                <div className="w-12"></div>
                {Array.from({ length: 24 }, (_, i) => (
                  <div
                    key={i}
                    className="w-6 text-xs text-x-gray text-center"
                  >
                    {i}
                  </div>
                ))}
              </div>
              {analytics.heatmapData.map((dayData, dayIndex) => (
                <div key={dayIndex} className="flex gap-1 mb-1">
                  <div className="w-12 text-xs text-x-gray flex items-center">
                    {dayLabels[dayIndex]}
                  </div>
                  {dayData.map((value, hourIndex) => (
                    <div
                      key={hourIndex}
                      className={`w-6 h-6 rounded ${getHeatmapColor(
                        value
                      )} border border-x-border transition-all hover:scale-110 cursor-pointer`}
                      title={`${dayLabels[dayIndex]} ${hourIndex}:00 - ${value} tweets`}
                    />
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Top Hashtags */}
          <div className="bg-x-dark border border-x-border rounded-lg p-6">
            <h3 className="text-lg font-semibold text-x-light mb-4">
              {t('analytics.topHashtags', 'Top Hashtags')}
            </h3>
            {analytics.topHashtags.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart
                  data={analytics.topHashtags}
                  layout="vertical"
                  margin={{ left: 80 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#2f3336" />
                  <XAxis type="number" stroke="#71767b" />
                  <YAxis type="category" dataKey="tag" stroke="#71767b" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#15202b',
                      border: '1px solid #2f3336',
                      borderRadius: '8px',
                      color: '#e7e9ea',
                    }}
                  />
                  <Bar dataKey="count" fill="#1d9bf0" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center text-x-gray py-12">
                {t('analytics.noHashtags', 'No hashtags found')}
              </div>
            )}
          </div>

          {/* Top Mentions */}
          <div className="bg-x-dark border border-x-border rounded-lg p-6">
            <h3 className="text-lg font-semibold text-x-light mb-4">
              {t('analytics.topMentions', 'Top Mentions')}
            </h3>
            {analytics.topMentions.length > 0 ? (
              <div className="space-y-2">
                {analytics.topMentions.map((item, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between py-2 px-3 bg-x-darker rounded-lg border border-x-border"
                  >
                    <span className="text-x-blue font-medium">
                      {item.mention}
                    </span>
                    <span className="text-x-gray text-sm">
                      {item.count} times
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-x-gray py-12">
                {t('analytics.noMentions', 'No mentions found')}
              </div>
            )}
          </div>
        </div>

        {/* Content Stats */}
        <div className="bg-x-dark border border-x-border rounded-lg p-6">
          <h3 className="text-lg font-semibold text-x-light mb-4">
            {t('analytics.contentStats', 'Content Statistics')}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-4xl font-bold text-x-blue mb-2">
                {analytics.avgLength}
              </div>
              <div className="text-x-gray text-sm">
                {t('analytics.avgTweetLength', 'Avg Tweet Length (chars)')}
              </div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-x-blue mb-2">
                {analytics.mediaPercent}%
              </div>
              <div className="text-x-gray text-sm">
                {t('analytics.tweetsWithMedia', 'Tweets with Media')}
              </div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-x-blue mb-2">
                {analytics.articleCount}
              </div>
              <div className="text-x-gray text-sm">
                {t('analytics.tweetsWithArticles', 'Tweets with Articles')}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Scrape Selector Component
function ScrapeSelector({
  history,
  selectedId,
  onSelect,
  t,
}: {
  history: ScrapeRecord[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  t: (key: string, fallback: string) => string;
}) {
  return (
    <div className="bg-x-dark border border-x-border rounded-lg p-4">
      <label className="block text-sm font-medium text-x-gray mb-2">
        {t('analytics.selectScrape', 'Select Scrape to Analyze')}
      </label>
      <select
        value={selectedId || ''}
        onChange={(e) => onSelect(e.target.value || null)}
        className="w-full bg-x-darker border border-x-border rounded-lg px-4 py-2.5 text-x-light focus:outline-none focus:border-x-blue transition-colors cursor-pointer"
      >
        <option value="">
          {t('analytics.currentSession', '-- Current Session Tweets --')}
        </option>
        {history.map((item) => (
          <option key={item.id} value={item.id}>
            {item.target_username} - {item.tweet_count} tweets ({item.started_at})
          </option>
        ))}
      </select>
    </div>
  );
}
