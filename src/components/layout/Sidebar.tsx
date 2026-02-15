import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useScrapeStore } from '../../stores/scrapeStore';
import {
  LayoutDashboard,
  Download,
  Clock,
  BarChart3,
  Sparkles,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
  Loader2,
} from 'lucide-react';

interface NavItem {
  path: string;
  labelKey: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { path: '/', labelKey: 'sidebar.dashboard', icon: <LayoutDashboard size={20} /> },
  { path: '/scrape', labelKey: 'sidebar.newScrape', icon: <Download size={20} /> },
  { path: '/history', labelKey: 'sidebar.history', icon: <Clock size={20} /> },
  { path: '/analytics', labelKey: 'sidebar.analytics', icon: <BarChart3 size={20} /> },
  { path: '/ai', labelKey: 'sidebar.aiAnalysis', icon: <Sparkles size={20} /> },
  { path: '/settings', labelKey: 'sidebar.settings', icon: <Settings size={20} /> },
];

function Sidebar() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [isExpanded, setIsExpanded] = useState(true);
  const { status, progress } = useScrapeStore();
  const isScrapingActive = status === 'running' || status === 'paused';

  return (
    <aside
      className={`${
        isExpanded ? 'w-56' : 'w-[68px]'
      } bg-x-dark/50 backdrop-blur-sm border-r border-x-border/50 flex flex-col transition-all duration-300 ease-in-out`}
    >
      {/* Toggle button */}
      <div className="h-12 flex items-center justify-end px-3">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-2 rounded-lg hover:bg-white/5 transition-colors text-x-gray hover:text-x-light"
          aria-label="Toggle sidebar"
        >
          {isExpanded ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
        </button>
      </div>

      {/* Active scrape indicator */}
      {isScrapingActive && (
        <div className="px-2 mb-2">
          <button
            onClick={() => navigate('/scrape/progress')}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-all ${
              status === 'running'
                ? 'bg-x-blue/10 border border-x-blue/20'
                : 'bg-amber-500/10 border border-amber-500/20'
            }`}
          >
            <Loader2 size={14} className={`flex-shrink-0 ${status === 'running' ? 'text-x-blue animate-spin' : 'text-amber-400'}`} />
            {isExpanded && (
              <div className="text-left min-w-0">
                <p className={`text-[11px] font-medium ${status === 'running' ? 'text-x-blue' : 'text-amber-400'}`}>
                  {status === 'running' ? 'Scraping...' : 'Paused'}
                </p>
                <p className="text-[10px] text-x-gray font-mono">
                  {progress.collected}{progress.target ? `/${progress.target}` : ''} tweets
                </p>
              </div>
            )}
          </button>
        </div>
      )}

      {/* Navigation items */}
      <nav className="flex-1 px-2 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group relative ${
                isActive
                  ? 'bg-x-blue/10 text-x-blue'
                  : 'text-x-gray hover:text-x-light hover:bg-white/5'
              }`
            }
            title={!isExpanded ? t(item.labelKey) : undefined}
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-x-blue rounded-r-full" />
                )}
                <span className="flex-shrink-0 w-5 flex items-center justify-center">
                  {item.icon}
                </span>
                {isExpanded && (
                  <span className="text-sm font-medium truncate">{t(item.labelKey)}</span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Version */}
      <div className="px-3 py-3 border-t border-x-border/30">
        <div className="text-[10px] text-x-gray/60 text-center font-mono">
          {isExpanded ? 'v1.0.0' : 'v1'}
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
