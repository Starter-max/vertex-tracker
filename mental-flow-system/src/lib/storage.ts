import { AppState } from './types';

const KEY = 'mental-flow-state';
const defaultState: AppState = { thoughts: [], users: [{ id: 'first', name: 'Owner', role: 'admin' }], settings: { reviewTime: '23:50', claudeApiKey: '' } };

export function getAppState(): AppState { if (typeof window === 'undefined') return defaultState; const raw = localStorage.getItem(KEY); return raw ? { ...defaultState, ...JSON.parse(raw) } : defaultState; }
export function saveAppState(state: AppState) { localStorage.setItem(KEY, JSON.stringify(state)); }
export function exportState(state: AppState) { const blob = new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' }); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'mental-flow-state.json'; a.click(); }
