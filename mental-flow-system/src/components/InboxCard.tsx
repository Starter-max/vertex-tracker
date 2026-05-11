import { Thought } from '@/lib/types';
export function InboxCard({ thought }: { thought: Thought }) { return <div className="rounded-2xl border border-slate-800 bg-slate-950 p-3 text-sm text-slate-200"><div>{thought.text}</div><div className="mt-2 text-xs text-slate-500">{new Date(thought.createdAt).toLocaleString('ru-RU')}</div></div>; }
