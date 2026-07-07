import { PAGE_INSET_X, PAGE_MAX_W } from '@/app/layout-constants'
import { cn } from '@/lib/utils'

import { BudgetBar } from './budget-bar'
import { GateFlow, type GateStats } from './gate-flow'
import { LiveTicker, type TickerEvent } from './live-ticker'
import { type TickReport, TickSummary } from './tick-summary'
import { type WorkerInfo, WorkerStatus } from './worker-status'

export interface MissionControlData {
  tick?: TickReport | null
  workers?: WorkerInfo[]
  gates?: GateStats
  events?: TickerEvent[]
  budgetSpent?: number
  budgetTotal?: number
  loading?: boolean
}

const EMPTY_GATES: GateStats = {
  T0: { pass_count: 0, fail_count: 0, last_transition: null },
  T1: { pass_count: 0, fail_count: 0, last_transition: null },
  T2: { pass_count: 0, fail_count: 0, last_transition: null },
  T3: { pass_count: 0, fail_count: 0, last_transition: null },
}

export function MissionControlView({
  tick = null,
  workers = [],
  gates = EMPTY_GATES,
  events = [],
  budgetSpent = 0,
  budgetTotal = 25,
  loading = true,
}: MissionControlData = {}) {
  const connectionText = loading
    ? 'waiting for ledger…'
    : tick
      ? `tick ${tick.tick_number} · live`
      : 'no data'

  return (
    <div className={cn('flex h-full flex-col overflow-y-auto', PAGE_INSET_X)}>
      <div className={cn('mx-auto flex w-full flex-col gap-6 py-6', PAGE_MAX_W)}>
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Mission Control</h1>
            <p className="mt-1 text-sm text-muted-foreground">AlphaForge orchestrator dashboard</p>
          </div>
          <div
            className={cn(
              'flex items-center gap-2 text-xs',
              loading ? 'text-muted-foreground' : tick ? 'text-emerald-500' : 'text-yellow-500',
            )}
          >
            <span
              className={cn(
                'inline-block size-1.5 rounded-full',
                loading ? 'bg-yellow-500' : tick ? 'bg-emerald-500' : 'bg-yellow-500',
              )}
            />
            <span>{connectionText}</span>
          </div>
        </div>

        {/* Top row: tick summary + budget + workers */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <TickSummary loading={loading} tick={tick} />
          <BudgetBar loading={loading} spent={budgetSpent} total={budgetTotal} />
          <WorkerStatus loading={loading} workers={workers} />
        </div>

        {/* Middle: gate flow */}
        <GateFlow gates={gates} loading={loading} />

        {/* Bottom: live ticker */}
        <LiveTicker events={events} loading={loading} />
      </div>
    </div>
  )
}
