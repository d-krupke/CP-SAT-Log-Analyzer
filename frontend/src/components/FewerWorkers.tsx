/**
 * The "Running on fewer cores" part of the Portfolio ranking card.
 *
 * Added 2026-09-28 when the card was restyled. For each smaller worker count at which CP-SAT
 * has to leave full-problem strategies out, it compares CP-SAT's own pick with the ranked
 * one as two rows of chips (added strategies green, dropped ones struck through) and offers
 * the Python lines that apply the ranked pick. Texts: `[texts]` in knowledge/importance.toml.
 */
import { useState } from 'react'
import { CopySnippet } from './CopySnippet'
import { Md } from './Md'
import type { WorkerChoice } from '../types'

/** The lines that make CP-SAT run exactly the ranked strategies with `c.workers` threads. */
function snippet(c: WorkerChoice): string {
  return [
    `solver.parameters.num_workers = ${c.workers}`,
    `solver.parameters.subsolvers.extend([${c.ranked.map((n) => `"${n}"`).join(', ')}])`,
  ].join('\n')
}

const differs = (c: WorkerChoice) => c.ranked.join() !== c.default.join()

export function FewerWorkers({ choices, texts }: { choices: WorkerChoice[]; texts: Record<string, string> }) {
  const [workers, setWorkers] = useState(() => (choices.find(differs) ?? choices[choices.length - 1]).workers)
  const choice = choices.find((c) => c.workers === workers) ?? choices[0]
  const code = snippet(choice)
  const kept = new Set(choice.default)
  const suggested = new Set(choice.ranked)
  return (
    <div className="pr-fewer">
      <div className="pr-label">Running on fewer cores</div>
      {texts.fewer_workers && <Md className="small" text={texts.fewer_workers} />}
      <div className="seg-buttons" role="group" aria-label="Number of workers">
        {choices.map((c) => (
          <button key={c.workers} className={`${c.workers === workers ? 'on' : ''}${differs(c) ? ' diff' : ''}`} onClick={() => setWorkers(c.workers)} title={differs(c) ? 'The suggestion differs here' : 'Same as CP-SAT'}>
            {c.workers}
          </button>
        ))}
        <span className="small">
          workers → {choice.full} full {choice.full === 1 ? 'strategy' : 'strategies'}
        </span>
      </div>
      <div className="pr-compare">
        <span className="who">CP-SAT keeps</span>
        <span className="chips">
          {choice.default.map((n) => (
            <span key={n} className={`chip${suggested.has(n) ? '' : ' dropped'}`}>
              {n}
            </span>
          ))}
        </span>
        <span className="who">This run suggests</span>
        <span className="chips">
          {differs(choice) ? (
            choice.ranked.map((n) => (
              <span key={n} className={`chip${kept.has(n) ? '' : ' added'}`}>
                {n}
              </span>
            ))
          ) : (
            <span className="small">the same, nothing to change</span>
          )}
        </span>
      </div>
      {differs(choice) && (
        <div className="pr-snippet">
          <CopySnippet code={code} />
          {texts.snippet_hint && <Md className="small" text={texts.snippet_hint} />}
        </div>
      )}
    </div>
  )
}
