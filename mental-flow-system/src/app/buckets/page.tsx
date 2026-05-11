'use client';

import { BottomNav } from '@/components/BottomNav';
import { BucketView } from '@/components/BucketView';
import { useAppState } from '@/lib/use-app-state';

export default function BucketsPage() {
  const { state } = useAppState();
  return (
    <main className="min-h-screen bg-slate-950 px-4 pb-24 pt-6 text-slate-100">
      <div className="mx-auto max-w-6xl space-y-6">
        <h1 className="text-3xl font-semibold">Корзины</h1>
        <BucketView state={state} />
      </div>
      <BottomNav />
    </main>
  );
}
