import { BottomNav } from '@/components/BottomNav';
import { VoiceCapture } from '@/components/VoiceCapture';
import { InboxCard } from '@/components/InboxCard';
import { getAppState } from '@/lib/storage';

export default function HomePage() {
  const state = getAppState();
  const inboxCount = state.thoughts.filter(t => t.category === 'INBOX').length;
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <section className="mx-auto flex min-h-screen max-w-4xl flex-col px-4 pb-24 pt-6">
        <header className="mb-6 flex items-center justify-between gap-3">
          <div>
            <p className="text-sm text-slate-400">Mental Flow System</p>
            <h1 className="text-3xl font-semibold">Захват мыслей</h1>
            <p className="mt-1 text-sm text-slate-500">Сначала захват, потом один раз в день разбор по 2 вопросам и корзинам.</p>
          </div>
          <div className="rounded-full border border-slate-700 px-3 py-1 text-sm text-slate-300">Inbox (до Q1): {inboxCount}</div>
        </header>
        <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <VoiceCapture />
          <div className="space-y-3 rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
            <h2 className="text-lg font-medium">Последние мысли</h2>
            {state.thoughts.slice(0, 5).map((thought) => <InboxCard key={thought.id} thought={thought} />)}
            {!state.thoughts.length && <p className="text-sm text-slate-400">Пока пусто. Запиши первую мысль.</p>}
          </div>
        </div>
        <div className="mt-4 rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
          <h2 className="text-lg font-medium">Ядро методологии</h2>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-slate-300">
            <li>Q1: Есть телесное сжатие/срочность? → сразу в Парковку.</li>
            <li>Q2: Мысль изнутри или снаружи? → изнутри в активные корзины, снаружи в Архив.</li>
          </ol>
        </div>
        <div className="mt-4 rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
          <h2 className="text-lg font-medium">Быстрый визуальный отчёт</h2>
          <p className="mt-1 text-sm text-slate-400">Открой вкладку отчёта для понимания, куда движется поток мыслей.</p>
          <a className="mt-3 inline-flex rounded-2xl border border-cyan-700 px-4 py-3 text-cyan-300" href="/report">Открыть отчёт</a>
        </div>
      </section>
      <BottomNav />
    </main>
  );
}
