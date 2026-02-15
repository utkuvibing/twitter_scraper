import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useScrapeStore } from '../../stores/scrapeStore';
import { useLogStore, formatLogTime } from '../../stores/logStore';
import { Pause, Play, X, Loader2, Heart, Repeat2, MessageCircle, Terminal, Trash2, Eye, EyeOff, ChevronDown, ChevronUp } from 'lucide-react';

function LogPanel() {
  const { logs, clearLogs, showDebug, setShowDebug, getFilteredLogs } = useLogStore();
  const [isCollapsed, setIsCollapsed] = useState(false);

  const filteredLogs = getFilteredLogs();

  const getLevelBadgeColor = (level: string) => {
    switch (level) {
      case 'debug':
        return 'bg-x-gray/20 text-x-gray';
      case 'info':
        return 'bg-x-blue/20 text-x-blue';
      case 'warning':
        return 'bg-amber-400/20 text-amber-400';
      case 'error':
        return 'bg-red-400/20 text-red-400';
      default:
        return 'bg-x-dark text-x-light';
    }
  };

  return (
    <div className="bg-x-dark/60 border border-x-border/40 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-x-border/40">
        <div className="flex items-center gap-2">
          <Terminal size={16} className="text-x-blue" />
          <h2 className="text-sm font-semibold text-x-light">
            Logs ({filteredLogs.length})
          </h2>
        </div>

        <div className="flex items-center gap-2">
          {/* Show Debug Toggle */}
          <button
            onClick={() => setShowDebug(!showDebug)}
            className="p-1.5 hover:bg-x-darker/50 rounded-lg transition-colors text-x-gray hover:text-x-light"
            title={showDebug ? 'Hide debug logs' : 'Show debug logs'}
          >
            {showDebug ? <Eye size={16} /> : <EyeOff size={16} />}
          </button>

          {/* Clear Button */}
          <button
            onClick={clearLogs}
            className="p-1.5 hover:bg-x-darker/50 rounded-lg transition-colors text-x-gray hover:text-red-400"
            title="Clear logs"
          >
            <Trash2 size={16} />
          </button>

          {/* Collapse/Expand Button */}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1.5 hover:bg-x-darker/50 rounded-lg transition-colors text-x-gray hover:text-x-light"
          >
            {isCollapsed ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
          </button>
        </div>
      </div>

      {/* Logs Container */}
      {!isCollapsed && (
        <div className="max-h-60 overflow-y-auto bg-x-darker/30">
          {filteredLogs.length === 0 ? (
            <div className="p-4 text-center text-x-gray text-sm">
              No logs yet
            </div>
          ) : (
            <div className="space-y-1 p-2">
              {filteredLogs.map((log) => (
                <div
                  key={log.id}
                  className="flex items-start gap-2 px-3 py-2 text-xs hover:bg-x-darker/50 rounded transition-colors"
                >
                  {/* Timestamp */}
                  <span className="text-x-gray/60 font-mono flex-shrink-0 min-w-fit">
                    {formatLogTime(log.timestamp)}
                  </span>

                  {/* Level Badge */}
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold flex-shrink-0 ${getLevelBadgeColor(
                      log.level
                    )}`}
                  >
                    {log.level.toUpperCase()}
                  </span>

                  {/* Message */}
                  <span className="text-x-light flex-1 break-words">{log.message}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ScrapeProgress() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { status, tweets, progress, pause, resume, cancel, error } = useScrapeStore();

  const [startTime] = useState(Date.now());
  const [elapsedTime, setElapsedTime] = useState(0);

  // Redirect to scrape config if no scrape is running
  useEffect(() => {
    if (status === 'idle') {
      navigate('/scrape');
    }
  }, [status, navigate]);

  // Update elapsed time every second
  useEffect(() => {
    if (status !== 'running' && status !== 'paused') return;

    const interval = setInterval(() => {
      setElapsedTime(Date.now() - startTime);
    }, 1000);

    return () => clearInterval(interval);
  }, [startTime, status]);

  // Navigate to results when completed
  useEffect(() => {
    console.log(`[ScrapeProgress] Status changed to: ${status}`);
    if (status === 'completed') {
      console.log('[ScrapeProgress] Navigating to results...');
      navigate('/scrape/results');
    }
  }, [status, navigate]);

  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const estimateTimeRemaining = () => {
    if (progress.collected === 0 || !progress.target) return '--:--';
    const rate = progress.collected / (elapsedTime / 1000);
    const remaining = progress.target - progress.collected;
    const secondsRemaining = remaining / rate;
    return formatTime(secondsRemaining * 1000);
  };

  const handleCancel = async () => {
    await cancel();
    navigate('/scrape');
  };

  const progressPercentage = progress.target
    ? Math.min((progress.collected / progress.target) * 100, 100)
    : 0;

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-x-light">
          Scraping in Progress
        </h1>
        <p className="text-sm text-x-gray mt-1">
          {status === 'paused' ? 'Scrape is paused' : status === 'error' ? 'An error occurred' : 'Collecting tweets...'}
        </p>
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Progress card */}
      <div className="bg-x-dark/60 border border-x-border/40 rounded-xl p-5 space-y-4">
        {/* Status + Controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            {status === 'running' ? (
              <>
                <Loader2 size={16} className="text-x-blue animate-spin" />
                <span className="text-sm font-medium text-x-light">Running</span>
              </>
            ) : status === 'paused' ? (
              <>
                <div className="w-3 h-3 bg-amber-400 rounded-full" />
                <span className="text-sm font-medium text-x-light">Paused</span>
              </>
            ) : status === 'error' ? (
              <>
                <div className="w-3 h-3 bg-red-400 rounded-full" />
                <span className="text-sm font-medium text-x-light">Error</span>
              </>
            ) : null}
          </div>

          <div className="flex gap-2">
            {status === 'running' && (
              <button
                onClick={pause}
                className="btn-secondary flex items-center gap-1.5 text-xs py-1.5 px-3"
              >
                <Pause size={14} />
                {t('common.pause')}
              </button>
            )}
            {status === 'paused' && (
              <button
                onClick={resume}
                className="btn-primary flex items-center gap-1.5 text-xs py-1.5 px-3"
              >
                <Play size={14} />
                {t('common.resume')}
              </button>
            )}
            <button
              onClick={handleCancel}
              className="flex items-center gap-1.5 text-xs py-1.5 px-3 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition-colors font-medium"
            >
              <X size={14} />
              Cancel
            </button>
          </div>
        </div>

        {/* Progress bar */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-x-gray">Progress</span>
            <span className="text-xs font-medium text-x-light font-mono">
              {progress.collected} / {progress.target || '--'} tweets
            </span>
          </div>
          <div className="w-full bg-x-darker/80 rounded-full h-2 overflow-hidden">
            <div
              className="h-full bg-x-blue transition-all duration-500 rounded-full"
              style={{
                width: progress.target ? `${progressPercentage}%` : '100%',
              }}
            >
              {!progress.target && (
                <div className="w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse" />
              )}
            </div>
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-x-darker/50 rounded-lg p-3 text-center">
            <p className="text-lg font-semibold text-x-light">{progress.collected}</p>
            <p className="text-[11px] text-x-gray">Collected</p>
          </div>
          <div className="bg-x-darker/50 rounded-lg p-3 text-center">
            <p className="text-lg font-semibold text-x-light font-mono">
              {formatTime(elapsedTime)}
            </p>
            <p className="text-[11px] text-x-gray">Elapsed</p>
          </div>
          <div className="bg-x-darker/50 rounded-lg p-3 text-center">
            <p className="text-lg font-semibold text-x-light font-mono">
              {progress.target ? estimateTimeRemaining() : 'N/A'}
            </p>
            <p className="text-[11px] text-x-gray">Remaining</p>
          </div>
        </div>
      </div>

       {/* Live tweet feed */}
       <div className="bg-x-dark/60 border border-x-border/40 rounded-xl p-5">
         <h2 className="text-sm font-semibold text-x-light mb-3">
           Recently Collected Tweets
         </h2>

         {tweets.length === 0 ? (
           <div className="text-center py-8 text-x-gray">
             <Loader2 size={24} className="mx-auto mb-2 animate-spin opacity-30" />
             <p className="text-sm">Waiting for tweets...</p>
           </div>
         ) : (
           <div className="space-y-2 max-h-80 overflow-y-auto">
             {tweets
               .slice()
               .reverse()
               .slice(0, 10)
               .map((tweet) => (
                 <div
                   key={tweet.id}
                   className="bg-x-darker/50 border border-x-border/30 rounded-lg p-3 animate-fadeIn"
                 >
                   <div className="flex items-start justify-between mb-1.5">
                     <span className="text-[11px] text-x-gray">{tweet.date_str}</span>
                     <div className="flex gap-3 text-[11px] text-x-gray">
                       <span className="flex items-center gap-1"><Heart size={10} /> {tweet.likes}</span>
                       <span className="flex items-center gap-1"><Repeat2 size={10} /> {tweet.retweets}</span>
                       <span className="flex items-center gap-1"><MessageCircle size={10} /> {tweet.replies}</span>
                     </div>
                   </div>
                   <p className="text-x-light text-xs line-clamp-2">
                     {tweet.text}
                   </p>
                 </div>
               ))}
           </div>
         )}
       </div>

       {/* Log Panel */}
       <LogPanel />
     </div>
   );
 }

 export default ScrapeProgress;
