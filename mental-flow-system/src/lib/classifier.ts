import { Category, Thought } from './types';

export const CLASSIFY_SYSTEM_PROMPT = `Ты — система классификации входящих мыслей и идей.
Эпицентр пользователя: исследование сложного → синтез → передача людям.
Три активных проекта: здоровье (телесное и психологическое), семья (создание безопасной среды), бизнес (инструмент, не цель).
Для каждой мысли определи категорию: ACTIVE_HEALTH, ACTIVE_FAMILY, ACTIVE_BUSINESS, PARKING, ARCHIVE.
Ответь только JSON массивом без пояснений: [{"id":"...","category":"ACTIVE_HEALTH","confidence":0.9}]`;

export function classifyThought(text: string): Category {
  const t = text.toLowerCase();
  if (/(сроч|тревог|страх|а вдруг|боюсь|паник|надо срочно|ипохондр)/.test(t)) return 'PARKING';
  if (/(инстаграм|ютуб|tik|хайп|пример|чуж|шопинг|дофамин|развлеч|scroll|смотреть)/.test(t)) return 'ARCHIVE';
  if (/(семья|ребен|жена|муж|дом|отношен|близк)/.test(t)) return 'ACTIVE_FAMILY';
  if (/(бизнес|клиент|проект|деньги|продаж|партнер|задач|встреч|сделк)/.test(t)) return 'ACTIVE_BUSINESS';
  return 'ACTIVE_HEALTH';
}

export async function classifyWithAI(thoughts: Thought[], apiKey: string) {
  const res = await fetch('/api/classify', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thoughts, apiKey })
  });
  return res.json();
}
