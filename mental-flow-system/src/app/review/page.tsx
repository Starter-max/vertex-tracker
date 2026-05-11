'use client';

import { useMemo, useState } from 'react';
import { BottomNav } from '@/components/BottomNav';
import { ReviewSession } from '@/components/ReviewSession';
import { useAppState } from '@/lib/use-app-state';

export default function ReviewPage() {
  const { state } = useAppState();
  const inbox = useMemo(() => state.thoughts.filter(t => t.category === 'INBOX'), [state]);
  const [index, setIndex] = useState(0);
  return (
    <main className="min-h-screen bg-slate-950 px-4 pb-24 pt-6 text-slate-100">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-3xl font-semibold">Ежедневный разбор</h1>
        <p className="mt-2 text-slate-400">Одна мысль за раз, быстрый перевод в нужную корзину.</p>
        <div className="mt-6 rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
          <div className="mb-4 flex items-center justify-between text-sm text-slate-400">
            <span>Осталось: {inbox.length}</span>
            <span>{inbox.length ? `${index + 1}/${inbox.length}` : '0/0'}</span>
          </div>
          <div className="h-2 rounded-full bg-slate-800"><div className="h-2 rounded-full bg-emerald-500" style={{ width: inbox.length ? `${((index + 1) / inbox.length) * 100}%` : '0%' }} /></div>
          <ReviewSession thoughts={inbox} index={index} onAdvance={() => setIndex(i => Math.min(i + 1, Math.max(0, inbox.length - 1)))} />
        </div>
      </div>
      <BottomNav />
    </main>
  );
}
