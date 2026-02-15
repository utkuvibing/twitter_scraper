import { create } from 'zustand';
import { invoke } from '@tauri-apps/api/core';

export type AuthStatus = 'disconnected' | 'connecting' | 'waiting' | 'connected' | 'error';

interface AuthState {
  status: AuthStatus;
  error: string | null;

  // Actions
  connectManual: () => Promise<void>;
  setConnected: () => void;
  setWaiting: (message: string) => void;
  setError: (message: string) => void;
  disconnect: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  status: 'disconnected',
  error: null,

  connectManual: async () => {
    set({ status: 'connecting', error: null });
    try {
      await invoke('login', {
        credentials: {
          method: 'manual',
        },
      });
      set({ status: 'waiting' });
    } catch (err) {
      console.error('Failed to start login:', err);
      set({
        status: 'error',
        error: typeof err === 'string' ? err : 'Failed to connect',
      });
    }
  },

  setConnected: () => {
    set({ status: 'connected', error: null });
  },

  setWaiting: (message: string) => {
    set({ status: 'waiting', error: null });
    console.log('Login waiting:', message);
  },

  setError: (message: string) => {
    set({ status: 'error', error: message });
  },

  disconnect: () => {
    set({ status: 'disconnected', error: null });
  },
}));
