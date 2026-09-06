/**
 * TypeScript mirror of the cpsatlog pydantic schema (v2/cpsatlog/src/cpsatlog/schema)
 * and of the backend analysis models (v2/backend/app/analysis.py).
 *
 * Keep in sync when the Python models change. Every parsed value carries the
 * log line it was read from so the UI can link data and log text both ways.
 */

export interface LineSpan {
  start: number
  end: number
}
export interface Loc<T> {
  value: T
  line: number
}
export interface Block {
  kind: string
  span: LineSpan
}
export interface LinesBlock extends Block {
  lines: Loc<string>[]
  message_kind?: string
}

export type Cell = number | string | null
export interface TableRow {
  name: string
  line: number
  cells: string[]
  values: Record<string, Cell>
}
export interface Table extends Block {
  kind: 'table'
  table_id: string
  title: string
  header_line: number
  columns: string[]
  rows: TableRow[]
  count: number | null
}
export interface TimingStats {
  n: number
  min: number
  max: number
  avg: number
  dev: number
  total: number
}
export interface TaskTimingRow {
  name: string
  line: number
  wall: TimingStats
  deterministic: TimingStats | null
}
export interface TaskTimingTable extends Block {
  kind: 'task_timing'
  table_id: string
  title: string
  header_line: number
  rows: TaskTimingRow[]
}
export interface FinalStats {
  task_timing: TaskTimingTable | null
  search_stats: Table | null
  sat_formula: Table | null
  sat_stats: Table | null
  vivification: Table | null
  clause_deletion: Table | null
  lp_stats: Table | null
  lp_dimension: Table | null
  lp_debug: Table | null
  lp_pool: Table | null
  lp_cut: Table | null
  lns_stats: Table | null
  ls_stats: Table | null
  solutions: Table | null
  objective_bounds: Table | null
  solution_repositories: Table | null
  improving_bounds_shared: Table | null
  clauses_shared: Table | null
  linear2_shared: Table | null
  other: Table[]
}

export interface SolverInfo extends Block {
  version: Loc<string> | null
  version_tuple: [number, number, number] | null
  parameters: Loc<Record<string, unknown>> | null
  parameters_raw: string | null
  num_workers: Loc<number> | null
  other_lines: Loc<string>[]
}

export interface DomainLine {
  line: number
  count: number
  description: string
  kind: 'bool' | 'int' | 'constant' | 'summary' | 'other'
  lo: number | null
  hi: number | null
  size: number | null
  intervals: number | null
  truncated: boolean
}
export interface ConstraintLine {
  line: number
  name: string
  count: number
  details: Record<string, number>
}
export interface ModelDescription extends Block {
  stage: 'initial' | 'presolved'
  problem_type: string | null
  name: string | null
  fingerprint: string | null
  num_variables: Loc<number> | null
  num_bools_in_objective: Loc<number> | null
  num_ints_in_objective: Loc<number> | null
  num_primary_variables: Loc<number> | null
  domains: DomainLine[]
  constraints: ConstraintLine[]
  search_strategies: Loc<string>[]
  other_lines: Loc<string>[]
}

export interface PresolveStep {
  line: number
  name: string
  time_s: number | null
  dtime_s: number | null
  details: string
  stats: Record<string, number | string>
}
export interface PresolveLog extends Block {
  spans: LineSpan[]
  start_time: Loc<number> | null
  steps: PresolveStep[]
  symmetry_lines: Loc<string>[]
  sat_presolve_lines: Loc<string>[]
  messages: Loc<string>[]
}
export interface PresolveRule {
  line: number
  rule: string
  count: number
}
export interface PresolveSummary extends Block {
  affine_relations: Loc<number> | null
  rules: PresolveRule[]
  closed_by_presolve: Loc<boolean> | null
  other_lines: Loc<string>[]
}

export interface SearchStart {
  line: number
  time: number
  num_workers: number | null
  deterministic: boolean
  batch_size: number | null
  sequential: boolean
}
export interface SubsolverGroup {
  line: number
  category: string
  label: string
  count: number | null
  subsolvers: { name: string; count: number }[]
}
export type EventKind = 'solution' | 'bound' | 'model' | 'done' | 'other'
export interface SearchEvent {
  line: number
  kind: EventKind
  label: string
  time: number
  solution_index: number | null
  objective: number | null
  objective_infinite: string | null
  next_lb: number | null
  next_ub: number | null
  subsolver: string | null
  message: string
  tags: string[]
  skipped_logs: number | null
  model_vars: number | null
  model_vars_total: number | null
  model_constraints: number | null
  model_constraints_total: number | null
}
export interface SearchProgress extends Block {
  spans: LineSpan[]
  start: SearchStart | null
  subsolvers: SubsolverGroup[]
  events: SearchEvent[]
  objective_sense: 'minimize' | 'maximize' | null
}

export interface ResponseSummary extends Block {
  status: Loc<string> | null
  objective: Loc<number> | null
  best_bound: Loc<number> | null
  integers: Loc<number> | null
  booleans: Loc<number> | null
  conflicts: Loc<number> | null
  branches: Loc<number> | null
  propagations: Loc<number> | null
  integer_propagations: Loc<number> | null
  restarts: Loc<number> | null
  lp_iterations: Loc<number> | null
  walltime: Loc<number> | null
  usertime: Loc<number> | null
  deterministic_time: Loc<number> | null
  gap_integral: Loc<number> | null
  solution_fingerprint: Loc<string> | null
  lrat_status: Loc<string> | null
  extra: Record<string, Loc<string>>
}

export interface BlockRef {
  kind: string
  span: LineSpan
  path: string
  title: string
}

export interface CpSatLog {
  num_lines: number
  solver: SolverInfo | null
  initial_model: ModelDescription | null
  presolve: PresolveLog | null
  presolve_summary: PresolveSummary | null
  presolved_model: ModelDescription | null
  search: SearchProgress | null
  stats: FinalStats
  response: ResponseSummary | null
  messages: LinesBlock[]
  comments: LinesBlock[]
  unparsed: LinesBlock[]
  blocks: BlockRef[]
  warnings: string[]
}

// ---- analysis (backend/app/analysis.py) ----
export type Level = 'info' | 'good' | 'warn' | 'bad'
export interface Metric {
  key: string
  label: string
  value: string
  line: number | null
  hint: string | null
  level: Level
}
export interface SeriesPoint {
  time: number
  value: number
  line: number
  subsolver: string | null
}
export interface ProgressSeries {
  objective_sense: 'minimize' | 'maximize' | null
  solutions: SeriesPoint[]
  bounds: SeriesPoint[]
  done_time: number | null
  done_line: number | null
  end_time: number | null
}
export interface ParameterInfo {
  name: string
  value: unknown
  known: boolean
  type: string | null
  default: string | null
  section: string | null
  doc: string
  enum_values: Record<string, string>
  advice: string | null
  warning: string | null
}
export interface SubsolverContribution {
  name: string
  solutions: number
  bounds: number
  first_solution_time: number | null
  best_solution_line: number | null
  description: string | null
  role: string | null
}
export interface Insight {
  level: Level
  title: string
  text: string
  lines: number[]
}
export interface HintNote {
  line: number
  kind: string
  text: string
  numbers: Record<string, number>
}
/** What the log says about the solution hint (backend/app/hints.py). */
export interface HintReport {
  provided: boolean
  status: string
  notes: HintNote[]
  used_as_first_solution: boolean
  first_solution_line: number | null
  objective: number | null
  hinted: number | null
  active: number | null
  fixed_variables: number | null
  lines: number[]
}
export interface Analysis {
  metrics: Metric[]
  progress: ProgressSeries
  parameters: ParameterInfo[]
  subsolvers: SubsolverContribution[]
  insights: Insight[]
  hint: HintReport
}
export interface ParseResult {
  log: CpSatLog
  analysis: Analysis
}

export interface TableDoc {
  summary: string
  columns: Record<string, string>
}
export interface SubsolverDoc {
  summary: string
  details: string
  role: string
}
export interface SubsolverPattern extends SubsolverDoc {
  pattern: string
}
export interface ConstraintDoc {
  summary: string
  complexity: string
}
export interface LevelDoc {
  label: string
  color: 'good' | 'info' | 'warn' | 'bad'
  text: string
}
export interface DomainSizeLevel extends LevelDoc {
  id: string
  max_size: number | null
}
export interface DomainDocs {
  levels: DomainSizeLevel[]
  holes: string
  truncated: string
  summary: string
  constant: string
}
/** Mirror of app/explanations.py; every section is a TOML file in v2/knowledge/. */
export interface Explanations {
  blocks: Record<string, string>
  cards: Record<string, string>
  tables: Record<string, TableDoc>
  response_fields: Record<string, string>
  subsolvers: Record<string, SubsolverDoc>
  subsolver_patterns: SubsolverPattern[]
  subsolver_roles: Record<string, string>
  subsolver_categories: Record<string, string>
  constraints: Record<string, ConstraintDoc>
  constraint_complexity: Record<string, LevelDoc>
  domains: DomainDocs
  messages: Record<string, string>
}
export interface ExampleInfo {
  name: string
  version_hint: string
  description: string
  summary: string
}
