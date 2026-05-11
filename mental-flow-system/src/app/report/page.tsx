import { BottomNav } from '@/components/BottomNav';
import { AIClassify } from '@/components/AIClassify';
import { getAppState } from '@/lib/storage';

const categories = [
  { key: 'ACTIVE_HEALTH', label: 'Здоровье', color: 'bg-emerald-500' },
  { key: 'ACTIVE_FAMILY', label: 'Семья', color: 'bg-emerald-500' },
  { key: 'ACTIVE_BUSINESS', label: 'Бизнес', color: 'bg-emerald-500' },
  { key: 'PARKING', label: 'Парковка', color: 'bg-amber-500' },
  { key: 'ARCHIVE', label: 'Архив', color: 'bg-slate-500' },
] as const;

export default function ReportPage() {
  const state = getAppState();
  const counts = Object.fromEntries(categories.map((c) => [c.key, state.thoughts.filter((t) => t.category === c.key).length]));
  const total = state.thoughts.length || 1;
  const inbox = state.thoughts.filter((t) => t.category === 'INBOX').length;
  const reviewable = state.thoughts.filter((t) => t.category === 'INBOX');
  const active = state.thoughts.filter((t) => t.category.startsWith('ACTIVE_')).length;
  const parking = counts.PARKING;
  const archive = counts.ARCHIVE;
  const attention = [
    ...state.thoughts.filter((t) => t.category === 'INBOX').slice(0, 3),
    ...state.thoughts.filter((t) => t.category === 'PARKING').slice(0, 3),
  ];

  return (
    <main className="min-h-screen bg-slate-950 px-4 pb-24 pt-6 text-slate-100">
      <div className="mx-auto max-w-5xl space-y-6">
        <div>
          <p className="text-sm text-slate-400">Mental Flow System</p>
          <h1 className="text-3xl font-semibold">Визуальный отчёт</h1>
          <p className="mt-2 text-sm text-slate-500">Показывает, как 2 вопроса превращают поток мыслей в понятные корзины действий.</p>
        </div>

        <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
          <h2 className="text-xl font-medium">Путь методологии</h2>
          <p className="mt-2 text-sm text-slate-300">Q1: сжатие/срочность → Парковка. Q2: изнутри/снаружи → Активная работа или Архив.</p>
        </section>

        <section className="grid gap-4 md:grid-cols-4">
          <Metric label="Inbox" value={inbox} hint="ожидает разбора" />
          <Metric label="Активная работа" value={active} hint="здоровье / семья / бизнес" />
          <Metric label="Парковка" value={parking} hint="на паузе" />
          <Metric label="Архив" value={archive} hint="шум / старое" />
        </section>

        <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-medium">Распределение по корзинам</h2>
            <p className="text-sm text-slate-400">Всего: {state.thoughts.length}</p>
          </div>
          <div className="space-y-3">
            {categories.map((c) => {
              const count = counts[c.key] as number;
              const pct = Math.round((count / total) * 100);
              return (
                <div key={c.key}>
                  <div className="mb-1 flex items-center justify-between text-sm text-slate-300">
                    <span>{c.label}</span>
                    <span>{count} · {pct}%</span>
                  </div>
                  <div className="h-3 overflow-hidden rounded-full bg-slate-800">
                    <div className={`${c.color} h-full`} style={{ width: `${Math.max(pct, count ? 8 : 0)}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
            <h2 className="text-xl font-medium">Сейчас на разбор</h2>
            <p className="mt-2 text-sm text-slate-400">Инбокс карточек: {reviewable.length}</p>
            <p className="mt-2 text-sm text-slate-500">Это то, что требует ежедневного ручного или AI разбора.</p>
          </div>
          <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
            <h2 className="text-xl font-medium">Эпицентр</h2>
            <p className="mt-2 text-sm text-slate-400">Исследование → синтез → передача людям</p>
            <p className="mt-2 text-sm text-slate-500">Здоровье, семья и бизнес — только инструменты для этого фокуса.</p>
          </div>
        </section>

        <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
          <h2 className="text-xl font-medium">Что требует внимания</h2>
          <div className="mt-4 space-y-2">
            {attention.length ? attention.map((t) => (
              <div key={t.id} className="rounded-2xl border border-slate-800 bg-slate-950 p-3 text-sm">
                <p>{t.text}</p>
                <p className="mt-1 text-xs text-slate-500">{t.category} · {new Date(t.createdAt).toLocaleDateString('ru-RU')}</p>
              </div>
            )) : <p className="text-sm text-slate-500">Сейчас ничего не ждёт внимания.</p>}
          </div>
        </section>

        <AIClassify thoughts={reviewable.slice(0, 10)} />
      </div>
      <BottomNav />
    </main>
  );
}

function Metric({ label, value, hint }: { label: string; value: number; hint: string }) {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-2 text-3xl font-semibold">{value}</p>
      <p className="mt-2 text-xs text-slate-500">{hint}</p>
    </div>
  );
}
