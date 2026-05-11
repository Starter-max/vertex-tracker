import { Thought } from '@/lib/types';
export function InboxCard({ thought }: { thought: Thought }) {
  return <article className="rounded-2xl border border-slate-800 bg-slate-950 p-3">
    <p className="text-sm text-slate-100">{thought.text}</p>
    <div className="mt-2 flex items-center justify-between text-xs text-slate-500"><span>{new Date(thought.createdAt).toLocaleString('ru-RU')}</span><span>{thought.source}</span></div>
  </article>;
}
