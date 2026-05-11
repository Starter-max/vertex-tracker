'use client';
import Link from 'next/link';
const items = [{href:'/',label:'Захват'},{href:'/review',label:'Разбор'},{href:'/buckets',label:'Корзины'}];
export function BottomNav(){return <nav className="fixed bottom-0 left-0 right-0 border-t border-slate-800 bg-slate-950/95 backdrop-blur"><div className="mx-auto grid max-w-4xl grid-cols-3 text-center text-sm">{items.map(i=><Link key={i.href} href={i.href} className="py-4 text-slate-300 hover:bg-slate-900">{i.label}</Link>)}</div></nav>}
