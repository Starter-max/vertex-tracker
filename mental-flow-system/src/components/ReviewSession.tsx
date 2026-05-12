'use client';
import { useMemo, useState } from 'react';
import { Thought } from '@/lib/types';
import { classifyThought, classifyWithAI } from '@/lib/classifier';
import { useAppState } from '@/lib/use-app-state';
import { moveThought, updateThought } from '@/lib/storage';

const labels: Record<string, string> = {
  ACTIVE_HEALTH: 'Здоровье',
  ACTIVE_FAMILY: 'Семья',
  ACTIVE_BUSINESS: 'Бизнес',
  PARKING: 'Парковка',
  ARCHIVE: 'Архив',
};

type Step = 'q1' | 'q2' | 'done';

export function ReviewSession({ thoughts, index, onAdvance }: { thoughts: Thought[]; index: number; onAdvance: () => void }) {
  const { state, setState } = useAppState();
  const [step, setStep] = useState<Step>('q1');
  const current = thoughts[index];

  const reset = () => setStep('q1');

  const move = (category: any) => {
    setState(moveThought(state, current.id, category));
    setStep('done');
    onAdvance();
    setTimeout(reset, 0);
  };

  const markParking = () => move('PARKING');
  const q1Yes = () => move('PARKING');
  const q1No = () => setStep('q2');
  const q2Inside = () => move(classifyThought(current.text));
  const q2Outside = () => move('ARCHIVE');
  const toggleDone = () => setState(updateThought(state, current.id, { done: !current.done }));

  const aiSort = async () => {
    const out = await classifyWithAI([current], state.settings.claudeApiKey);
    const cat = out?.items?.[0]?.category || classifyThought(current.text);
    move(cat);
  };

  const text = useMemo(() => current?.text ?? '', [current]);

  if (!current) return <p className="py-10 text-slate-400">Инбокс пуст.</p>;

  return (
    <div className="mt-6 space-y-4">
      <div className="rounded-3xl border border-slate-800 bg-slate-950 p-5 text-xl">{text}</div>

      <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
        <p className="mb-3 text-sm uppercase tracking-wide text-slate-500">Q1</p>
        <p className="mb-4 text-slate-200">Есть сжатие в теле или ощущение «надо срочно»?</p>
        <div className="grid gap-3 sm:grid-cols-2">
          <button className="rounded-2xl bg-amber-500 px-4 py-4 font-semibold text-slate-950" onClick={q1Yes}>ДА → Парковка</button>
          <button className="rounded-2xl bg-slate-700 px-4 py-4 font-semibold" onClick={q1No}>НЕТ → Q2</button>
        </div>
      </div>

      {step === 'q2' && (
        <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
          <p className="mb-3 text-sm uppercase tracking-wide text-slate-500">Q2</p>
          <p className="mb-4 text-slate-200">Откуда пришло — изнутри или из чужого контента/примера?</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <button className="rounded-2xl bg-emerald-600 px-4 py-4 font-semibold text-slate-950" onClick={q2Inside}>ИЗНУТРИ → Активная работа</button>
            <button className="rounded-2xl bg-slate-700 px-4 py-4 font-semibold" onClick={q2Outside}>СНАРУЖИ → Архив</button>
          </div>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <button className="rounded-2xl border border-slate-700 px-4 py-3" onClick={aiSort}>Авто-сортировка</button>
        {(['ACTIVE_HEALTH', 'ACTIVE_FAMILY', 'ACTIVE_BUSINESS', 'ARCHIVE'] as const).map((c) => (
          <button key={c} className="rounded-2xl border border-slate-700 px-4 py-3" onClick={() => move(c)}>
            {labels[c]}
          </button>
        ))}
      </div>

      <button className="rounded-2xl border border-emerald-800 px-4 py-3 text-emerald-300" onClick={toggleDone}>
        {current.done ? 'Вернуть в разбор' : 'Готово / В архив'}
      </button>
      <button className="rounded-2xl border border-slate-700 px-4 py-3 text-slate-300" onClick={markParking}>Быстро в парковку</button>
    </div>
  );
}
