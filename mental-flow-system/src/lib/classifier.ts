import { Category, Thought } from './types';

export function classifyThought(text: string): Category { const t = text.toLowerCase(); if (/(сроч|тревог|страх|а вдруг|боюсь|паник|надо срочно)/.test(t)) return 'PARKING'; if (/(инстаграм|ютуб|tik|хайп|пример|чуж|шопинг|допамин|дофамин)/.test(t)) return 'ARCHIVE'; if (/(семья|ребен|жена|муж|дом|отношен)/.test(t)) return 'ACTIVE_FAMILY'; if (/(бизнес|клиент|проект|деньги|продаж|партнер|задач)/.test(t)) return 'ACTIVE_BUSINESS'; return 'ACTIVE_HEALTH'; }
export async function classifyWithAI(thoughts: Thought[], apiKey: string) { const res = await fetch('/api/classify', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ thoughts, apiKey }) }); return res.json(); }
