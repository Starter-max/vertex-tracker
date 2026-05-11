'use client';

import { BottomNav } from '@/components/BottomNav';
import { useAppState } from '@/lib/use-app-state';
import { exportState } from '@/lib/storage';

export default function SettingsPage() {
  const { state, setState } = useAppState();
  return (
    <main className="min-h-screen bg-slate-950 px-4 pb-24 pt-6 text-slate-100">
      <div className="mx-auto max-w-3xl space-y-4">
        <h1 className="text-3xl font-semibold">Настройки</h1>
        <button className="rounded-2xl bg-slate-800 px-4 py-3" onClick={() => exportState(state)}>Экспорт JSON</button>
        <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
          <label className="text-sm text-slate-400">Время напоминания</label>
          <input className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" value={state.settings.reviewTime} onChange={e => setState({ ...state, settings: { ...state.settings, reviewTime: e.target.value } })} />
        </div>
        <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
          <label className="text-sm text-slate-400">Claude API key</label>
          <input className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" value={state.settings.claudeApiKey} onChange={e => setState({ ...state, settings: { ...state.settings, claudeApiKey: e.target.value } })} />
        </div>
      </div>
      <BottomNav />
    </main>
  );
}
