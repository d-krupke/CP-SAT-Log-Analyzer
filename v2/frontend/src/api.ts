/** Thin fetch wrappers for the backend API (see v2/backend/app/main.py). */
import type { ExampleInfo, Explanations, ParseResult } from './types'

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? ''

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = ((await res.json()) as { detail?: string }).detail ?? detail
    } catch {
      /* keep statusText */
    }
    throw new Error(`${res.status}: ${detail}`)
  }
  return (await res.json()) as T
}

export function parseLog(text: string): Promise<ParseResult> {
  return fetch(`${BASE}/api/parse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  }).then((r) => json<ParseResult>(r))
}

export function listExamples(): Promise<ExampleInfo[]> {
  return fetch(`${BASE}/api/examples`).then((r) => json<ExampleInfo[]>(r))
}

export function readExample(name: string): Promise<string> {
  return fetch(`${BASE}/api/examples/${encodeURIComponent(name)}`)
    .then((r) => json<{ text: string }>(r))
    .then((d) => d.text)
}

export function loadExplanations(): Promise<Explanations> {
  return fetch(`${BASE}/api/explanations`).then((r) => json<Explanations>(r))
}
