import { PAGE_INSET_X, PAGE_MAX_W } from '@/app/layout-constants'
import { cn } from '@/lib/utils'

export function ReportsView() {
  return (
    <div className={cn('flex h-full flex-col overflow-y-auto', PAGE_INSET_X)}>
      <div className={cn('mx-auto flex w-full flex-col gap-6 py-6', PAGE_MAX_W)}>
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Reports</h1>
          <p className="mt-1 text-sm text-muted-foreground">AlphaForge tick reports & evidence</p>
        </div>
        <div className="flex items-center justify-center rounded-lg border border-dashed border-(--ui-stroke-tertiary) p-12 text-sm text-muted-foreground">
          Reports viewer — coming in v2
        </div>
      </div>
    </div>
  )
}
