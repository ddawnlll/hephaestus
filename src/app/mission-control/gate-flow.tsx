import { Codicon } from '@/components/ui/codicon'
import { Skeleton } from '@/components/ui/skeleton'
import { relativeTime } from '@/lib/time'
import { cn } from '@/lib/utils'

// ── Types ──────────────────────────────────────────────────────────────────

export interface GateInfo {
  pass_count: number
  fail_count: number
  last_transition: string | null
}

export interface GateStats {
  T0: GateInfo
  T1: GateInfo
  T2: GateInfo
  T3: GateInfo
}

// ── Props ───────────────────────────────────────────────────────────────────

interface GateFlowProps {
  gates: GateStats
  loading: boolean
}

// ── Component ───────────────────────────────────────────────────────────────

const GATE_LABELS: Record<string, string> = {
  T0: 'T0 — Init',
  T1: 'T1 — Validate',
  T2: 'T2 — Deploy',
  T3: 'T3 — Production',
}

const GATE_ORDER = ['T0', 'T1', 'T2', 'T3'] as const

export function GateFlow({ gates, loading }: GateFlowProps) {
  return (
    <div className="rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-editor-surface-background) p-4">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        Gate Flow
      </h2>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div className="space-y-1" key={i}>
              <Skeleton className="h-3.5 w-24" />
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-3 w-28" />
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          {GATE_ORDER.map((key, idx) => {
            const gate = gates[key as keyof GateStats] as GateInfo | undefined

            if (!gate) {return null}

            const total = gate.pass_count + gate.fail_count
            const passRate = total > 0 ? (gate.pass_count / total) * 100 : 0

            const lastLabel = gate.last_transition
              ? relativeTime(new Date(gate.last_transition).getTime())
              : '—'

            return (
              <div key={key}>
                {/* Gate card */}
                <div className="rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-editor-surface-background)/60 px-3 py-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-foreground">
                      {GATE_LABELS[key]}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      {lastLabel}
                    </span>
                  </div>

                  <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Codicon className="size-3 text-green-400" name="pass" />
                      {gate.pass_count}
                    </span>
                    <span className="flex items-center gap-1">
                      <Codicon className="size-3 text-red-400" name="error" />
                      {gate.fail_count}
                    </span>
                    <span
                      className={cn(
                        'ml-auto font-medium tabular-nums',
                        passRate >= 80
                          ? 'text-green-400'
                          : passRate >= 50
                            ? 'text-yellow-400'
                            : 'text-red-400',
                      )}
                    >
                      {passRate.toFixed(0)}%
                    </span>
                  </div>
                </div>

                {/* Arrow connector to next gate */}
                {idx < GATE_ORDER.length - 1 && (
                  <div className="flex justify-center py-0.5">
                    <Codicon className="size-3.5 text-muted-foreground/50" name="arrow-down" />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
