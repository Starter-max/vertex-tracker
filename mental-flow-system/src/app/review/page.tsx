'use client';
import { useMemo, useState } from 'react';
import { BottomNav } from '@/components/BottomNav';
import { ReviewSession } from '@/components/ReviewSession';
import { useAppState } from '@/lib/use-app-state';
import { classifyWithAI } from '@/lib/classifier';
import { moveThought } from '@/lib/storage';

export default function ReviewPage() {
  const { state, setState } = useAppState();
  const inbox = useMemo(() => state.thoughts.filter(t => t.category === 'INBOX'), [state.thoughts]);
  const [index, setIndex] = useState(0);
  const progress = inbox.length ? ((index) / inbox.length) * 100 : 0;

  const autoSortAll = async () => {
    const api = state.settings.claudeApiKey;
    const res = await classifyWithAI(inbox, api);
    const items = Array.isArray(res?.items) ? res.items : [];
    if (items.length) {
      setState({
        ...state,
        thoughts: state.thoughts.map(t => {
          const found = items.find((x:any) => x.id === t.id);
          return found ? { ...t, category: found.category } : t;
        })
      });
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 px-4 pb-24 pt-6 text-slate-100">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-3xl font-semibold">Ежедневный разбор</h1>
        <p className="mt-2 text-slate-400">Одна мысль за раз. Сначала Q1, потом Q2, затем раскладка по корзинам.</p>
        <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/70 p-3 text-sm text-slate-300">
          Q1: есть сжатие/срочность → Парковка. Q2: изнутри/снаружи → Активные корзины или Архив.
        </div>
        <div className="mt-6 rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
          <div className="mb-4 flex items-center justify-between text-sm text-slate-400"><span>Осталось: {inbox.length}</span><span>{inbox.length ? `${Math.min(index + 1, inbox.length)}/${inbox.length}` : '0/0'}</span></div>
          <div className="h-2 rounded-full bg-slate-800"><div className="h-2 rounded-full bg-emerald-500" style={{ width: `${progress}%` }} /></div>
          <div className="mt-4 flex gap-3"><button className="rounded-2xl bg-emerald-600 px-4 py-3 font-medium" onClick={autoSortAll}>Авто-сортировка</button><button className="rounded-2xl border border-slate-700 px-4 py-3 font-medium" onClick={() => setIndex(0)}>Сначала</button></div>
          <ReviewSession thoughts={inbox} index={index} onAdvance={() => setIndex(i => Math.min(i + 1, Math.max(0, inbox.length - 1)))} />
        </div>
      </div>
      <BottomNav />
    </main>
  );
}
