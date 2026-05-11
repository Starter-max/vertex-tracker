import { BottomNav } from '@/components/BottomNav';
import { VoiceCapture } from '@/components/VoiceCapture';
import { InboxCard } from '@/components/InboxCard';
import { getAppState } from '@/lib/storage';

export default function HomePage() {
  const state = getAppState();
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <section className="mx-auto flex min-h-screen max-w-4xl flex-col px-4 pb-24 pt-6">
        <header className="mb-6 flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-400">Mental Flow System</p>
            <h1 className="text-3xl font-semibold">Захват мыслей</h1>
          </div>
          <div className="rounded-full border border-slate-700 px-3 py-1 text-sm text-slate-300">Inbox: {state.thoughts.filter(t => t.category === 'INBOX').length}</div>
        </header>
        <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <VoiceCapture />
          <div className="space-y-3 rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
            <h2 className="text-lg font-medium">Последние мысли</h2>
            {state.thoughts.slice(0, 5).map((thought) => (
              <InboxCard key={thought.id} thought={thought} />
            ))}
            {!state.thoughts.length && <p className="text-sm text-slate-400">Пока пусто. Запиши первую мысль.</p>}
          </div>
        </div>
      </section>
      <BottomNav />
    </main>
  );
}
