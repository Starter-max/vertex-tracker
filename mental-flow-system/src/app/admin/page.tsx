'use client';
import { useState } from 'react';
import { BottomNav } from '@/components/BottomNav';
import { useAppState } from '@/lib/use-app-state';
import type { UserRole } from '@/lib/types';

export default function AdminPage() {
  const { state, setState } = useAppState();
  const [name, setName] = useState('');
  const [role, setRole] = useState<UserRole>('user');
  const [editId, setEditId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editRole, setEditRole] = useState<UserRole>('user');
  const save = () => { if (!name.trim()) return; setState({ ...state, users: [...state.users, { id: crypto.randomUUID(), name: name.trim(), role }] }); setName(''); };
  const beginEdit = (u:any) => { setEditId(u.id); setEditName(u.name); setEditRole(u.role); };
  const commitEdit = () => { if (!editId) return; setState({ ...state, users: state.users.map(u => u.id===editId ? { ...u, name: editName.trim(), role: editRole } : u) }); setEditId(null); };
  return <main className="min-h-screen bg-slate-950 px-4 pb-24 pt-6 text-slate-100"><div className="mx-auto max-w-3xl space-y-4"><h1 className="text-3xl font-semibold">Админка пользователей</h1><div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4 space-y-3"><input className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" placeholder="Имя" value={name} onChange={e => setName(e.target.value)} /><select className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" value={role} onChange={e => setRole(e.target.value as UserRole)}><option value="user">user</option><option value="admin">admin</option></select><button className="rounded-2xl bg-emerald-600 px-4 py-3 font-medium" onClick={save}>Добавить пользователя</button></div><div className="space-y-2">{state.users.map(u => <div key={u.id} className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 flex items-center justify-between gap-3"><span>{u.name} · {u.role}</span><div className="flex gap-2"><button className="text-slate-300" onClick={() => beginEdit(u)}>Редактировать</button><button className="text-rose-400" onClick={() => setState({ ...state, users: state.users.filter(x => x.id !== u.id) })}>Удалить</button></div></div>)}{editId && <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4 space-y-3"><input className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" value={editName} onChange={e => setEditName(e.target.value)} /><select className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" value={editRole} onChange={e => setEditRole(e.target.value as UserRole)}><option value="user">user</option><option value="admin">admin</option></select><button className="rounded-2xl bg-emerald-600 px-4 py-3 font-medium" onClick={commitEdit}>Сохранить</button></div>}</div></div><BottomNav /></main>
}
