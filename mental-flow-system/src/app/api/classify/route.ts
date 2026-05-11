import { NextResponse } from 'next/server';
import { CLASSIFY_SYSTEM_PROMPT, classifyThought } from '@/lib/classifier';

export async function POST(req: Request) {
  const body = await req.json();
  const thoughts = Array.isArray(body.thoughts) ? body.thoughts : [];
  const apiKey = String(body.apiKey || '').trim();
  const items = thoughts.map((t: any) => ({ id: t.id, category: classifyThought(t.text), confidence: 0.74 }));
  if (!apiKey) return NextResponse.json({ ok: true, items, mode: 'heuristic', systemPrompt: CLASSIFY_SYSTEM_PROMPT });
  try {
    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 1024,
        system: CLASSIFY_SYSTEM_PROMPT,
        messages: [{ role: 'user', content: JSON.stringify(thoughts.map((t:any)=>({id:t.id,text:t.text}))) }],
      }),
    });
    if (!res.ok) return NextResponse.json({ ok: true, items, mode: 'heuristic_fallback', status: res.status });
    const data = await res.json();
    const text = Array.isArray(data.content) ? data.content.map((x:any)=>x.text || '').join('') : '';
    let parsed:any[] = [];
    try { parsed = JSON.parse(text); } catch {}
    const merged = thoughts.map((t:any) => ({ id: t.id, category: parsed.find((x:any)=>x.id===t.id)?.category || classifyThought(t.text), confidence: parsed.find((x:any)=>x.id===t.id)?.confidence || 0.74 }));
    return NextResponse.json({ ok: true, items: merged, mode: 'anthropic' });
  } catch {
    return NextResponse.json({ ok: true, items, mode: 'heuristic_error' });
  }
}
