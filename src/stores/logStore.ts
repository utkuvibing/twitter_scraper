import { create } from 'zustand';

export type LogLevel = 'debug' | 'info' | 'warning' | 'error';

export interface LogEntry {
  id: string;
  timestamp: number;
  level: LogLevel;
  message: string;
  source?: string;
}

interface LogState {
  logs: LogEntry[];
  maxLogs: number;
  showDebug: boolean;

  // Actions
  addLog: (level: LogLevel, message: string, source?: string) => void;
  clearLogs: () => void;
  setMaxLogs: (max: number) => void;
  setShowDebug: (show: boolean) => void;
  getFilteredLogs: () => LogEntry[];
}

export const useLogStore = create<LogState>((set, get) => ({
  logs: [],
  maxLogs: 500,
  showDebug: false,

  addLog: (level: LogLevel, message: string, source?: string) => {
    const entry: LogEntry = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      level,
      message,
      source: source || 'scraper',
    };

    set((state) => {
      const newLogs = [entry, ...state.logs].slice(0, state.maxLogs);
      return { logs: newLogs };
    });
  },

  clearLogs: () => set({ logs: [] }),

  setMaxLogs: (max: number) => set({ maxLogs: max }),

  setShowDebug: (show: boolean) => set({ showDebug: show }),

  getFilteredLogs: () => {
    const { logs, showDebug } = get();
    if (showDebug) return logs;
    return logs.filter((log) => log.level !== 'debug');
  },
}));

// Helper function to get level color
export const getLogLevelColor = (level: LogLevel): string => {
  switch (level) {
    case 'debug':
      return 'text-x-gray';
    case 'info':
      return 'text-x-blue';
    case 'warning':
      return 'text-amber-400';
    case 'error':
      return 'text-red-400';
    default:
      return 'text-x-light';
  }
};

// Helper function to get level bg color
export const getLogLevelBgColor = (level: LogLevel): string => {
  switch (level) {
    case 'debug':
      return 'bg-x-gray/10';
    case 'info':
      return 'bg-x-blue/10';
    case 'warning':
      return 'bg-amber-400/10';
    case 'error':
      return 'bg-red-400/10';
    default:
      return 'bg-x-dark';
  }
};

// Helper function to format timestamp
export const formatLogTime = (timestamp: number): string => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('tr-TR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};
