import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Download, Clock, BarChart3, ArrowRight } from 'lucide-react';

function Dashboard() {
  const { t } = useTranslation();

  const stats = {
    totalScrapes: 0,
    totalTweets: 0,
    lastScrapeDate: null as string | null,
  };

  const recentScrapes: any[] = [];

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      {/* Welcome */}
      <div>
        <h1 className="text-2xl font-semibold text-x-light">
          {t('dashboard.welcome')}
        </h1>
        <p className="text-sm text-x-gray mt-1">
          Scrape tweets from profiles and bookmarks with ease
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="bg-x-dark/60 border border-x-border/40 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-x-gray uppercase tracking-wider">Total Scrapes</span>
            <div className="w-8 h-8 rounded-lg bg-x-blue/10 flex items-center justify-center">
              <BarChart3 size={16} className="text-x-blue" />
            </div>
          </div>
          <p className="text-2xl font-semibold text-x-light">{stats.totalScrapes}</p>
        </div>

        <div className="bg-x-dark/60 border border-x-border/40 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-x-gray uppercase tracking-wider">
              {t('dashboard.totalTweets')}
            </span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
              <Download size={16} className="text-emerald-400" />
            </div>
          </div>
          <p className="text-2xl font-semibold text-x-light">{stats.totalTweets}</p>
        </div>

        <div className="bg-x-dark/60 border border-x-border/40 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-x-gray uppercase tracking-wider">Last Scrape</span>
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center">
              <Clock size={16} className="text-amber-400" />
            </div>
          </div>
          <p className="text-lg font-semibold text-x-light">
            {stats.lastScrapeDate || 'Never'}
          </p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 gap-3">
        <Link
          to="/scrape"
          className="group bg-x-blue/10 hover:bg-x-blue/15 border border-x-blue/20 hover:border-x-blue/40 text-x-blue font-medium py-4 px-5 rounded-xl transition-all flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <Download size={20} />
            <span>{t('sidebar.newScrape')}</span>
          </div>
          <ArrowRight size={16} className="opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
        </Link>

        <Link
          to="/history"
          className="group bg-white/[0.02] hover:bg-white/[0.05] border border-x-border/40 hover:border-x-border/60 text-x-light font-medium py-4 px-5 rounded-xl transition-all flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <Clock size={20} className="text-x-gray" />
            <span>View History</span>
          </div>
          <ArrowRight size={16} className="opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all text-x-gray" />
        </Link>
      </div>

      {/* Recent Scrapes */}
      <div className="bg-x-dark/60 border border-x-border/40 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-x-light mb-4">
          {t('dashboard.recentScrapes')}
        </h2>

        {recentScrapes.length === 0 ? (
          <div className="text-center py-10">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-white/[0.03] flex items-center justify-center">
              <Download size={20} className="text-x-gray/50" />
            </div>
            <p className="text-x-gray text-sm mb-1">No scrapes yet</p>
            <p className="text-x-gray/60 text-xs mb-4">
              Start your first scrape to see it here
            </p>
            <Link
              to="/scrape"
              className="inline-flex items-center gap-1.5 text-x-blue hover:text-x-blue/80 text-sm font-medium transition-colors"
            >
              Create your first scrape
              <ArrowRight size={14} />
            </Link>
          </div>
        ) : (
          <div className="space-y-2">
            {recentScrapes.map((scrape) => (
              <div
                key={scrape.id}
                className="flex items-center justify-between p-3.5 bg-x-darker/50 rounded-lg hover:bg-x-darker/80 transition-colors"
              >
                <div>
                  <p className="font-medium text-sm text-x-light">{scrape.target}</p>
                  <p className="text-xs text-x-gray mt-0.5">{scrape.date}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-x-light">
                    {scrape.tweetCount} tweets
                  </p>
                  <p className="text-xs text-x-gray">{scrape.status}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
