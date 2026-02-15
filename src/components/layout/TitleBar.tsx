import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { Minus, Square, Copy, X } from 'lucide-react';

const routeTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/scrape': 'New Scrape',
  '/scrape/progress': 'Scrape in Progress',
  '/scrape/results': 'Scrape Results',
  '/history': 'History',
  '/analytics': 'Analytics',
  '/ai': 'AI Analysis',
  '/settings': 'Settings',
};

function TitleBar() {
  const location = useLocation();
  const [isMaximized, setIsMaximized] = useState(false);
  const appWindow = getCurrentWindow();

  useEffect(() => {
    const checkMaximized = async () => {
      try {
        const maximized = await appWindow.isMaximized();
        setIsMaximized(maximized);
      } catch (e) {
        console.error('Failed to check maximized state:', e);
      }
    };
    checkMaximized();
  }, []);

  const handleMinimize = async () => {
    try {
      await appWindow.minimize();
    } catch (e) {
      console.error('Failed to minimize:', e);
    }
  };

  const handleMaximize = async () => {
    try {
      await appWindow.toggleMaximize();
      const maximized = await appWindow.isMaximized();
      setIsMaximized(maximized);
    } catch (e) {
      console.error('Failed to toggle maximize:', e);
    }
  };

  const handleClose = async () => {
    try {
      await appWindow.close();
    } catch (e) {
      console.error('Failed to close:', e);
    }
  };

  const pageTitle = routeTitles[location.pathname] || 'X Scraper';

  return (
    <div
      data-tauri-drag-region
      className="h-10 bg-x-dark/80 backdrop-blur-sm border-b border-x-border/50 flex items-center justify-between select-none"
    >
      <div
        data-tauri-drag-region
        className="flex items-center gap-3 px-4 flex-1"
      >
        <svg viewBox="0 0 24 24" className="w-4 h-4 fill-x-blue flex-shrink-0" aria-hidden="true">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
        </svg>
        <span className="text-x-blue font-bold text-sm tracking-wide">Scraper</span>
        <span className="text-x-border">|</span>
        <span className="text-xs text-x-gray font-medium">{pageTitle}</span>
      </div>

      <div className="flex h-full">
        <button
          onClick={handleMinimize}
          className="h-full w-12 flex items-center justify-center hover:bg-white/5 transition-colors text-x-gray hover:text-x-light"
          aria-label="Minimize"
        >
          <Minus size={14} />
        </button>

        <button
          onClick={handleMaximize}
          className="h-full w-12 flex items-center justify-center hover:bg-white/5 transition-colors text-x-gray hover:text-x-light"
          aria-label={isMaximized ? 'Restore' : 'Maximize'}
        >
          {isMaximized ? <Copy size={12} /> : <Square size={12} />}
        </button>

        <button
          onClick={handleClose}
          className="h-full w-12 flex items-center justify-center hover:bg-red-500/90 transition-colors text-x-gray hover:text-white"
          aria-label="Close"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}

export default TitleBar;
