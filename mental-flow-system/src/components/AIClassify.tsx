'use client';
import { useState } from 'react';
import { Thought } from '@/lib/types';
import { classifyWithAI, classifyThought } from '@/lib/classifier';
import { useAppState } from '@/lib/use-app-state';
import { moveThought } from '@/lib/storage';

export function AIClassify({ thoughts }: { thoughts: Thought[] }) {
  const { state, setState } = useAppState();
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<Array<{ id: string; text: string; category: string; confidence: number }>>([]);

  const run = async () => {
    if (!thoughts.length) return;
    setLoading(true);
    try {
      const result = await classifyWithAI(thoughts, state.settings.claudeApiKey);
      const items = result?.items?.length
        ? result.items
        : thoughts.map((thought) => ({ id: thought.id, category: classifyThought(thought.text), confidence: 0.72 }));
      setPreview(items.map((item: any) => ({
        id: item.id,
        text: thoughts.find((t) => t.id === item.id)?.text || item.id,
        category: item.category,
        confidence: Number(item.confidence ?? 0.72),
      })));
    } finally {
      setLoading(false);
    }
  };

  const apply = () => {
    if (!preview.length) return;
    let next = state;
    for (const item of preview) {
      next = moveThought(next, item.id, item.category as any);
    }
    setState(next);
    setPreview([]);
  };

  return (
    <section className="rounded-3xl border border-cyan-900 bg-cyan-950/20 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold">AI-сортировка</h3>
          <p className="text-sm text-slate-400">Claude предложит категории, потом можно применить одним кликом.</p>
        </div>
        <button
          className="rounded-2xl bg-cyan-500 px-4 py-3 font-semibold text-slate-950 disabled:opacity-60"
          onClick={run}
          disabled={loading || !thoughts.length}
        >
          {loading ? 'Сортирую…' : 'Запустить AI'}
        </button>
      </div>
      {!!preview.length && (
        <div className="mt-4 space-y-2">
          {preview.map((item) => (
            <div key={item.id} className="rounded-2xl border border-slate-800 bg-slate-950 p-3 text-sm">
              <p className="text-slate-200">{item.text}</p>
              <p className="mt-1 text-xs text-slate-500">{item.category} · confidence {Math.round(item.confidence * 100)}%</p>
            </div>
          ))}
          <button className="rounded-2xl border border-emerald-700 px-4 py-3 font-medium text-emerald-300" onClick={apply}>
            Применить результаты
          </button>
        </div>
      )}
    </section>
  );
}
