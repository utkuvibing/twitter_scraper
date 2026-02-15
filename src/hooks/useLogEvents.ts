import { useEffect } from 'react';
import { listen, UnlistenFn } from '@tauri-apps/api/event';
import { useLogStore, LogLevel } from '../stores/logStore';

interface SidecarLogEvent {
  type?: string;
  level?: string;
  message?: string;
  [key: string]: any;
}

export function useLogEvents() {
  const { addLog } = useLogStore();

  useEffect(() => {
    let unlisten: UnlistenFn | undefined;

    const setupListener = async () => {
      unlisten = await listen<SidecarLogEvent>('sidecar-log', (event) => {
        const payload = event.payload;

        if (!payload || typeof payload !== 'object') return;

        // Handle log events
        if (payload.type === 'log' || payload.message) {
          const level = (payload.level as LogLevel) || 'info';
          const message = payload.message || '';
          
          if (message) {
            addLog(level, message, 'scraper');
          }
        }
      });
    };

    setupListener();

    return () => {
      if (unlisten) unlisten();
    };
  }, [addLog]);
}
