// Standalone AlphaForge Mission Control — runs in browser without Electron IPC.
// Spawn with: npm run dev:standalone
// then open http://127.0.0.1:5174/standalone.html

// ── Mock Electron IPC bridge (as any to skip strict type checking) ──────
function noop() {}

function sub() { return noop }

window.hermesDesktop = {
  isFullscreen: false,
  getPlatform: () => 'win32',
  getNativeOverlayWidth: () => 0,
  setBadgeCount: noop,
  setProgressBar: noop,
  setPreviewShortcutActive: noop,
  signalDeepLinkReady: () => Promise.resolve({ ok: true }),
  onBootProgress: sub,
  onBootstrapEvent: sub,
  onPreviewFileChanged: sub,
  onBackendExit: sub,
  onOpenSettingsRequested: sub,
  onFocusSession: sub,
  onNotificationAction: sub,
  onDeepLink: sub,
  onClosePreviewRequested: sub,
  onOpenUpdatesRequested: sub,
  onWindowStateChanged: sub,
  onPowerResume: sub,
  getBootstrapState: () => Promise.resolve({ step: 'done' }),
  getBootProgress: () => Promise.resolve({ progress: 1, step: 'done', title: 'Ready', message: '' }),
  resetBootstrap: () => Promise.resolve({ ok: true }),
  repairBootstrap: () => Promise.resolve({ ok: true }),
  cancelBootstrap: () => Promise.resolve({ ok: true, cancelled: true }),
  getVersion: () => Promise.resolve({ appVersion: '0.17.0', electronVersion: '40.10.2', nodeVersion: '22', platform: 'win32' }),
  updates: { check: () => Promise.resolve({ status: 'current' }), apply: () => Promise.resolve({ ok: true }), getBranch: () => Promise.resolve({ branch: 'main' }), setBranch: () => Promise.resolve({ branch: 'main' }), onProgress: sub },
  uninstall: { summary: () => Promise.resolve({ ok: true, hermes_home: '', agent_installed: true, gui_installed: true, source_built_artifacts: false, app_data: '', platform: 'win32', desktop_bundle: '', desktop_data: '' }), run: () => Promise.resolve({ ok: true }) },
  themes: { fetchMarketplace: () => Promise.resolve({ extensionId: '', displayName: '', themes: [] }), searchMarketplace: () => Promise.resolve([]) },
  git: { worktreeList: () => Promise.resolve([]), worktreeAdd: () => Promise.resolve({ worktree: { name: '', path: '' } }), worktreeRemove: () => Promise.resolve({ ok: true }), status: () => Promise.resolve({}), diff: () => Promise.resolve(''), commit: () => Promise.resolve({ ok: true }), commitContext: () => Promise.resolve({ diff: '', recent: '' }), push: () => Promise.resolve({ ok: true }), shipInfo: () => Promise.resolve({ url: '' }), createPr: () => Promise.resolve({ url: '' }), scanRepos: () => Promise.resolve([]) },
  terminal: { dispose: () => Promise.resolve(true), onData: sub, onExit: sub, resize: () => Promise.resolve(true), start: () => Promise.resolve({ cwd: '/', id: 'mock', shell: 'bash' }), write: () => Promise.resolve(true) },
} as any

import './../styles.css'

import { StrictMode, useState } from 'react'
// ── React app ───────────────────────────────────────────────────────────
import { createRoot } from 'react-dom/client'

import { ControlPlaneView } from '../app/control-plane'
import { type MissionControlData, MissionControlView } from '../app/mission-control'
import { ThemeProvider } from '../themes/context'

import { SAMPLE_EVENTS, SAMPLE_GATES, SAMPLE_TICK, SAMPLE_WORKERS } from './sample-data'

type View = 'mc' | 'cp'

const NAV_ITEMS: { id: View; label: string }[] = [
  { id: 'mc', label: 'Mission Control' },
  { id: 'cp', label: 'Control Plane' },
]

function StandaloneApp() {
  const [view, setView] = useState<View>('mc')

  const mcData: MissionControlData = {
    tick: SAMPLE_TICK,
    workers: SAMPLE_WORKERS,
    gates: SAMPLE_GATES,
    events: SAMPLE_EVENTS,
    budgetSpent: 14.2,
    budgetTotal: 25,
    loading: false,
  }

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: '#111' }}>
      {/* Sidebar */}
      <nav
        style={{
          width: 48,
          background: '#1a1a1a',
          borderRight: '1px solid #2a2a2a',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          paddingTop: 8,
          gap: 4,
        }}
      >
        {NAV_ITEMS.map(item => (
          <button
            key={item.id}
            onClick={() => setView(item.id)}
            style={{
              width: 36,
              height: 36,
              background: view === item.id ? '#2a2a2a' : 'transparent',
              border: 'none',
              borderRadius: 6,
              color: view === item.id ? '#ffd700' : '#666',
              cursor: 'pointer',
              fontSize: 16,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            title={item.label}
          >
            {item.id === 'mc' ? '◉' : '⚙'}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main style={{ flex: 1, minWidth: 0 }}>
        {view === 'mc' ? <MissionControlView {...mcData} /> : <ControlPlaneView />}
      </main>
    </div>
  )
}

const root = document.getElementById('root')

if (root) {
  createRoot(root).render(
    <StrictMode>
      <ThemeProvider>
        <StandaloneApp />
      </ThemeProvider>
    </StrictMode>,
  )
}
