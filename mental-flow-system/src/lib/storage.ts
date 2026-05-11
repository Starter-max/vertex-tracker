import { AppState, Category, Thought } from './types';

const KEY = 'mental-flow-state';
const defaultState: AppState = {
  thoughts: [],
  users: [{ id: 'first', name: 'Owner', role: 'admin' }],
  settings: { reviewTime: '23:50', claudeApiKey: '', dailyReminderEnabled: true },
};

export function getDefaultState(): AppState { return defaultState; }
export function getAppState(): AppState {
  if (typeof window === 'undefined') return defaultState;
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? { ...defaultState, ...JSON.parse(raw) } : defaultState;
  } catch { return defaultState; }
}
export function saveAppState(state: AppState) { if (typeof window !== 'undefined') localStorage.setItem(KEY, JSON.stringify(state)); }
export function exportState(state: AppState) {
  const blob = new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'mental-flow-state.json'; a.click();
}
export function addThought(state: AppState, text: string, source: 'voice'|'text'): AppState {
  const thought: Thought = { id: crypto.randomUUID(), text: text.trim(), createdAt: new Date().toISOString(), category: 'INBOX', source };
  return { ...state, thoughts: [thought, ...state.thoughts] };
}
export function updateThought(state: AppState, id: string, patch: Partial<Thought>): AppState {
  return { ...state, thoughts: state.thoughts.map(t => t.id===id ? { ...t, ...patch } : t) };
}
export function moveThought(state: AppState, id: string, category: Category): AppState { return updateThought(state, id, { category }); }
export function removeOldArchive(state: AppState, days = 30): AppState {
  const cutoff = Date.now() - days * 86400000;
  return { ...state, thoughts: state.thoughts.filter(t => t.category !== 'ARCHIVE' || new Date(t.createdAt).getTime() >= cutoff) };
}
export function staleParking(state: AppState, days = 7) {
  const cutoff = Date.now() - days * 86400000;
  return state.thoughts.filter(t => t.category === 'PARKING' && new Date(t.createdAt).getTime() < cutoff);
}
export function searchArchive(state: AppState, query: string) {
  const q = query.trim().toLowerCase();
  return state.thoughts.filter(t => t.category === 'ARCHIVE' && (!q || t.text.toLowerCase().includes(q) || (t.note || '').toLowerCase().includes(q)));
}
