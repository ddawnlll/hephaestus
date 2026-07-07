import type { GateStats } from '../app/mission-control/gate-flow'
import type { TickerEvent } from '../app/mission-control/live-ticker'
import type { TickReport } from '../app/mission-control/tick-summary'
import type { WorkerInfo } from '../app/mission-control/worker-status'

export { type GateStats, type TickerEvent, type TickReport, type WorkerInfo }

export const SAMPLE_TICK: TickReport = {
  tick_number: 47,
  date: '2026-07-06T14:30:00Z',
  budget_spent: 14.2,
  workers_active: 3,
  hypotheses_created: 12,
  hypotheses_completed: 8,
  gates_passed: 3,
  summary_text:
    'Tick 47 completed 8 hypotheses across 3 workers. Gate T2 passed on hypothesis "momentum_regime_shift". Budget at 56.8%.',
}

export const SAMPLE_WORKERS: WorkerInfo[] = [
  { id: 'w1', name: 'alpha-scout', status: 'running', progress: 0.72, current_task: 'Feature engineering — lag transforms' },
  { id: 'w2', name: 'beta-miner', status: 'running', progress: 0.45, current_task: 'Backtest regime_filter_v3' },
  { id: 'w3', name: 'gamma-validator', status: 'idle', progress: 1, current_task: 'Awaiting next tick dispatch' },
  { id: 'w4', name: 'delta-optimizer', status: 'failed', progress: 0.33, current_task: 'Hyperopt failed — timeout' },
]

export const SAMPLE_GATES: GateStats = {
  T0: { pass_count: 47, fail_count: 12, last_transition: '2026-07-06T14:28:00Z' },
  T1: { pass_count: 31, fail_count: 18, last_transition: '2026-07-06T14:15:00Z' },
  T2: { pass_count: 19, fail_count: 24, last_transition: '2026-07-06T13:55:00Z' },
  T3: { pass_count: 7, fail_count: 9, last_transition: '2026-07-06T12:30:00Z' },
}

export const SAMPLE_EVENTS: TickerEvent[] = [
  { id: 'e1', timestamp: '2026-07-06T14:29:00Z', type: 'success', message: 'Hypothesis momentum_regime_shift passed T2' },
  { id: 'e2', timestamp: '2026-07-06T14:25:00Z', type: 'info', message: 'Worker alpha-scout started tick 47' },
  { id: 'e3', timestamp: '2026-07-06T14:20:00Z', type: 'warning', message: 'Worker delta-optimizer timed out (180s limit)' },
  { id: 'e4', timestamp: '2026-07-06T14:15:00Z', type: 'success', message: 'Gate T1: 31 passed / 18 failed this tick' },
  { id: 'e5', timestamp: '2026-07-06T14:10:00Z', type: 'info', message: 'Budget: $14.20 / $25.00 (56.8%)' },
  { id: 'e6', timestamp: '2026-07-06T14:05:00Z', type: 'error', message: 'Hypothesis arb_decay_model rejected at T1 — p-value 0.12 > 0.05' },
  { id: 'e7', timestamp: '2026-07-06T14:00:00Z', type: 'info', message: 'Tick 47 dispatched — 4 workers, $0.50 budget' },
]
