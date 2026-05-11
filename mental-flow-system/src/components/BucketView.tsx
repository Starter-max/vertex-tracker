import { AppState, Category } from '@/lib/types';
import { useAppState } from '@/lib/use-app-state';
import { moveThought, removeOldArchive, searchArchive, staleParking, updateThought } from '@/lib/storage';
import { useMemo, useState } from 'react';

const bucketStyles: Record<string, string> = { emerald: 'border-emerald-900 bg-emerald-950/30', amber: 'border-amber-900 bg-amber-950/30', slate: 'border-slate-800 bg-slate-900/70' };
const label = (c: Category) => ({ACTIVE_HEALTH:'Здоровье',ACTIVE_FAMILY:'Семья',ACTIVE_BUSINESS:'Бизнес',PARKING:'Парковка',ARCHIVE:'Архив',INBOX:'Inbox'}[c]);

export function BucketView({ state }: { state: AppState }) {
  const { setState } = useAppState();
  const [archiveQuery, setArchiveQuery] = useState('');

  const active = state.thoughts.filter(t=>t.category.startsWith('ACTIVE_'));
  const parking = state.thoughts.filter(t=>t.category==='PARKING');
  const archive = searchArchive(state, archiveQuery);
  const health = active.filter(t=>t.category==='ACTIVE_HEALTH');
  const family = active.filter(t=>t.category==='ACTIVE_FAMILY');
  const business = active.filter(t=>t.category==='ACTIVE_BUSINESS');

  const weekly = () => alert((staleParking(state).map(t=>t.text).join('\n\n')) || 'Старых мыслей в парковке нет');
  const cleanArchive = () => setState(removeOldArchive(state));
  const activeBuckets = [{title:'Здоровье',items:health,color:'emerald' as const},{title:'Семья',items:family,color:'emerald' as const},{title:'Бизнес',items:business,color:'emerald' as const}];

  return <div className="space-y-6">
    <section className={`rounded-3xl border ${bucketStyles.emerald} p-4`}>
      <div className="mb-3 flex items-center justify-between"><h2 className="text-xl font-medium">Активная работа</h2><p className="text-sm text-slate-400">Здоровье / Семья / Бизнес</p></div>
      <div className="grid gap-4 md:grid-cols-3">{activeBuckets.map((b) => <Bucket key={b.title} title={b.title} color={b.color} items={b.items} onDone={(id: string)=>setState(updateThought(state,id,{done:true,category:'ARCHIVE'}))} onMove={(id: string,cat: Category)=>setState(moveThought(state,id,cat))} onNote={(id: string, note: string)=>setState(updateThought(state, id, { note }))} />)}</div>
    </section>

    <section className={`rounded-3xl border ${bucketStyles.amber} p-4`}>
      <div className="mb-3 flex items-center justify-between"><h2 className="text-xl font-medium">Парковка</h2><button className="rounded-xl border border-amber-700 px-3 py-2 text-sm" onClick={weekly}>Недельный обзор</button></div>
      <Bucket title="" color="amber" items={parking} onDone={(id: string)=>setState(moveThought(state,id,'ARCHIVE'))} onMove={(id: string,cat: Category)=>setState(moveThought(state,id,cat))} onNote={(id: string, note: string)=>setState(updateThought(state, id, { note }))} />
    </section>

    <section className={`rounded-3xl border ${bucketStyles.slate} p-4`}>
      <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-xl font-medium">Архив</h2>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <input className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm" value={archiveQuery} onChange={e => setArchiveQuery(e.target.value)} placeholder="Поиск в архиве" />
          <button className="rounded-xl border border-slate-700 px-3 py-2 text-sm" onClick={cleanArchive}>Очистка старше 30 дней</button>
        </div>
      </div>
      <Bucket title="" color="slate" items={archive} onDone={() => {}} onMove={(id: string,cat: Category)=>setState(moveThought(state,id,cat))} onNote={(id: string, note: string)=>setState(updateThought(state, id, { note }))} />
    </section>
  </div>;
}

function Bucket({ title, color, items, onDone, onMove, onNote }: { title: string; color: 'emerald'|'amber'|'slate'; items: any[]; onDone: (id: string) => void; onMove: (id: string, cat: Category) => void; onNote: (id: string, note: string) => void; }) {
  return <section className={`rounded-3xl border ${bucketStyles[color]}`}><h2 className="text-lg font-medium">{title}</h2><div className="mt-3 space-y-2 max-h-[32rem] overflow-auto pr-1">{items.map((t:any)=><div key={t.id} className="rounded-2xl border border-slate-800 bg-slate-950 p-3 text-sm"><div className="flex items-start justify-between gap-3"><div className="min-w-0 flex-1"><p className="text-slate-100">{t.text}</p><p className="mt-1 text-xs text-slate-500">{label(t.category)} · {new Date(t.createdAt).toLocaleDateString('ru-RU')}</p>{t.note ? <p className="mt-2 rounded-xl border border-slate-800 bg-slate-900/70 p-2 text-xs text-slate-300">{t.note}</p> : null}<input className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs" placeholder="Заметка" defaultValue={t.note || ''} onBlur={e => onNote(t.id, e.target.value)} /></div><div className="flex gap-2"><button className="text-xs text-emerald-300" onClick={()=>onDone(t.id)}>{t.done ? '↩︎' : '✓'}</button><button className="text-xs text-slate-400" onClick={()=>onMove(t.id,'ARCHIVE')}>→</button></div></div></div>)}{!items.length && <p className="text-sm text-slate-500">Пусто</p>}</div></section>; }
