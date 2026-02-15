import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useScrapeStore, TweetData } from '../../stores/scrapeStore';

type SortField = 'date' | 'likes' | 'retweets' | 'replies' | 'views';
type SortDirection = 'asc' | 'desc';

function ScrapeResults() {
  const { t } = useTranslation();
  const { tweets, reset } = useScrapeStore();

  const [sortField, setSortField] = useState<SortField>('date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [expandedTweetId, setExpandedTweetId] = useState<string | null>(null);

  // Calculate summary stats
  const stats = useMemo(() => {
    if (tweets.length === 0) {
      return {
        total: 0,
        avgLikes: 0,
        avgRetweets: 0,
        avgReplies: 0,
        dateRange: { start: '', end: '' },
      };
    }

    const sortedByDate = [...tweets].sort((a, b) => a.date - b.date);
    const totalLikes = tweets.reduce((sum, t) => sum + t.likes, 0);
    const totalRetweets = tweets.reduce((sum, t) => sum + t.retweets, 0);
    const totalReplies = tweets.reduce((sum, t) => sum + t.replies, 0);

    return {
      total: tweets.length,
      avgLikes: Math.round(totalLikes / tweets.length),
      avgRetweets: Math.round(totalRetweets / tweets.length),
      avgReplies: Math.round(totalReplies / tweets.length),
      dateRange: {
        start: sortedByDate[0].date_str,
        end: sortedByDate[sortedByDate.length - 1].date_str,
      },
    };
  }, [tweets]);

  // Sort tweets
  const sortedTweets = useMemo(() => {
    const sorted = [...tweets].sort((a, b) => {
      let aVal: any, bVal: any;

      switch (sortField) {
        case 'date':
          aVal = a.date;
          bVal = b.date;
          break;
        case 'likes':
          aVal = a.likes;
          bVal = b.likes;
          break;
        case 'retweets':
          aVal = a.retweets;
          bVal = b.retweets;
          break;
        case 'replies':
          aVal = a.replies;
          bVal = b.replies;
          break;
        case 'views':
          aVal = a.views;
          bVal = b.views;
          break;
        default:
          return 0;
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return sorted;
  }, [tweets, sortField, sortDirection]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const handleExport = (format: 'json' | 'markdown' | 'word') => {
    // TODO: Implement export functionality
    console.log(`Exporting as ${format}`);
  };

  const toggleExpand = (tweetId: string) => {
    setExpandedTweetId(expandedTweetId === tweetId ? null : tweetId);
  };

  const handleNewScrape = () => {
    reset();
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <span className="text-x-gray">⇅</span>;
    return sortDirection === 'asc' ? (
      <span className="text-x-blue">↑</span>
    ) : (
      <span className="text-x-blue">↓</span>
    );
  };

  return (
    <div className="p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-x-light mb-2">
              Scrape Results
            </h1>
            <p className="text-x-gray">
              {stats.dateRange.start} - {stats.dateRange.end}
            </p>
          </div>

          {/* Export buttons */}
          <div className="flex gap-2">
            <button
              onClick={() => handleExport('json')}
              className="px-4 py-2 bg-x-dark hover:bg-x-darker border border-x-border text-x-light rounded-lg transition-colors font-medium"
            >
              📄 JSON
            </button>
            <button
              onClick={() => handleExport('markdown')}
              className="px-4 py-2 bg-x-dark hover:bg-x-darker border border-x-border text-x-light rounded-lg transition-colors font-medium"
            >
              📝 Markdown
            </button>
            <button
              onClick={() => handleExport('word')}
              className="px-4 py-2 bg-x-dark hover:bg-x-darker border border-x-border text-x-light rounded-lg transition-colors font-medium"
            >
              📘 Word
            </button>
          </div>
        </div>

        {/* Summary stats */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-x-dark border border-x-border rounded-lg p-4">
            <p className="text-sm text-x-gray mb-1">Total Tweets</p>
            <p className="text-2xl font-bold text-x-light">{stats.total}</p>
          </div>
          <div className="bg-x-dark border border-x-border rounded-lg p-4">
            <p className="text-sm text-x-gray mb-1">Avg Likes</p>
            <p className="text-2xl font-bold text-x-light">{stats.avgLikes}</p>
          </div>
          <div className="bg-x-dark border border-x-border rounded-lg p-4">
            <p className="text-sm text-x-gray mb-1">Avg Retweets</p>
            <p className="text-2xl font-bold text-x-light">{stats.avgRetweets}</p>
          </div>
          <div className="bg-x-dark border border-x-border rounded-lg p-4">
            <p className="text-sm text-x-gray mb-1">Avg Replies</p>
            <p className="text-2xl font-bold text-x-light">{stats.avgReplies}</p>
          </div>
        </div>

        {/* Tweets table */}
        <div className="bg-x-dark border border-x-border rounded-lg overflow-hidden">
          {/* Table header */}
          <div className="grid grid-cols-12 gap-4 px-4 py-3 bg-x-darker border-b border-x-border text-xs font-medium text-x-gray">
            <button
              onClick={() => handleSort('date')}
              className="col-span-2 text-left hover:text-x-light flex items-center gap-1"
            >
              Date <SortIcon field="date" />
            </button>
            <div className="col-span-4">Tweet</div>
            <button
              onClick={() => handleSort('likes')}
              className="text-right hover:text-x-light flex items-center justify-end gap-1"
            >
              Likes <SortIcon field="likes" />
            </button>
            <button
              onClick={() => handleSort('retweets')}
              className="text-right hover:text-x-light flex items-center justify-end gap-1"
            >
              RTs <SortIcon field="retweets" />
            </button>
            <button
              onClick={() => handleSort('replies')}
              className="text-right hover:text-x-light flex items-center justify-end gap-1"
            >
              Replies <SortIcon field="replies" />
            </button>
            <button
              onClick={() => handleSort('views')}
              className="col-span-2 text-right hover:text-x-light flex items-center justify-end gap-1"
            >
              Views <SortIcon field="views" />
            </button>
          </div>

          {/* Table rows */}
          <div className="max-h-[600px] overflow-y-auto">
            {sortedTweets.map((tweet) => (
              <div
                key={tweet.id}
                className="grid grid-cols-12 gap-4 px-4 py-4 border-b border-x-border hover:bg-x-darker transition-colors cursor-pointer"
                onClick={() => toggleExpand(tweet.id)}
              >
                <div className="col-span-2 text-sm text-x-gray">
                  {tweet.date_str}
                </div>
                <div className="col-span-4">
                  <p
                    className={`text-sm text-x-light ${
                      expandedTweetId === tweet.id ? '' : 'line-clamp-2'
                    }`}
                  >
                    {tweet.text}
                  </p>
                  {expandedTweetId === tweet.id && tweet.media_urls.length > 0 && (
                    <div className="mt-2 text-xs text-x-gray">
                      📎 {tweet.media_urls.length} media file(s)
                    </div>
                  )}
                </div>
                <div className="text-right text-sm text-x-light">
                  {tweet.likes.toLocaleString()}
                </div>
                <div className="text-right text-sm text-x-light">
                  {tweet.retweets.toLocaleString()}
                </div>
                <div className="text-right text-sm text-x-light">
                  {tweet.replies.toLocaleString()}
                </div>
                <div className="col-span-2 text-right text-sm text-x-light">
                  {tweet.views.toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* New scrape button */}
        <div className="mt-6 flex justify-center">
          <Link
            to="/scrape"
            onClick={handleNewScrape}
            className="px-6 py-3 bg-x-blue hover:bg-opacity-90 text-white font-semibold rounded-lg transition-all flex items-center gap-2"
          >
            <span>⬇</span>
            <span>New Scrape</span>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default ScrapeResults;
