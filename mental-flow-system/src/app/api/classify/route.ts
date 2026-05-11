import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  const body = await req.json();
  return NextResponse.json({ ok: true, received: body.thoughts?.length ?? 0, note: 'Claude integration placeholder — wire API key and Anthropic call here.' });
}
