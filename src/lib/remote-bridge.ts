import { readDesktopFileText } from '@/lib/desktop-fs'

// ── RemoteBridge ─────────────────────────────────────────────────────────────
//
// Provides access to AlphaForge ledger files. When SSH_HOST env vars are
// configured, the bridge can tunnel to a remote server (SSH integration TBD).
// By default, reads from the local filesystem via the desktop bridge.
//
// Future: replace the local fallback with actual SSH (ssh2 or exec ssh command)
// when REMOTE_SSH_HOST and REMOTE_LEDGER_PATH are set.

const DEFAULT_LOCAL_PATH = '~/.hermes/alphaforge'

export class RemoteBridge {
  private _connected = false
  private _sshHost: string | null = null
  private _remoteLedgerPath: string | null = null
  private _localLedgerPath: string

  constructor(localLedgerPath?: string) {
    this._localLedgerPath = localLedgerPath || DEFAULT_LOCAL_PATH
  }

  /**
   * Connect to a remote SSH host. When SSH_HOST env is unset, this sets up
   * local-only mode (no-op connect).
   *
   * @param sshHost  SSH host string (user@hostname or hostname)
   * @param ledgerPath  Remote ledger path
   */
  async connect(
    sshHost: string,
    ledgerPath: string,
  ): Promise<void> {
    this._sshHost = sshHost
    this._remoteLedgerPath = ledgerPath
    this._connected = true
    console.info(
      `[remote-bridge] Connected to ${sshHost}:${ledgerPath}`,
    )
  }

  /**
   * Disconnect the SSH tunnel (or reset local mode).
   */
  disconnect(): void {
    this._sshHost = null
    this._remoteLedgerPath = null
    this._connected = false
  }

  /**
   * Whether the bridge is in connected state.
   */
  isConnected(): boolean {
    return this._connected
  }

  /**
   * Read a file relative to the ledger path.
   * In local-only mode, reads via the desktop bridge.
   * In SSH mode (future), reads via a remote SSH command.
   *
   * @param relativePath  Path relative to ledger base (e.g. "control.yaml")
   * @returns File contents as string, or null on error / ENOENT
   */
  async readFile(relativePath: string): Promise<string | null> {
    // ── Check env for SSH configuration ──────────────────────────────
    const envSshHost =
      process.env.REMOTE_SSH_HOST || this._sshHost

    const envRemotePath =
      process.env.REMOTE_LEDGER_PATH || this._remoteLedgerPath

    if (envSshHost && envRemotePath) {
      // ── SSH mode (stub for future) ─────────────────────────────────
      try {
        return await this.readRemoteViaSsh(
          envSshHost,
          envRemotePath,
          relativePath,
        )
      } catch (err) {
        console.warn(
          '[remote-bridge] SSH read failed, falling back to local:',
          err,
        )

        return this.readLocal(relativePath)
      }
    }

    // ── Local mode (default) ─────────────────────────────────────────
    return this.readLocal(relativePath)
  }

  /**
   * Resolve the local ledger path with ~/ expansion.
   */
  private localPath(relativePath: string): string {
    const home =
      process.env.HOME || process.env.USERPROFILE || '~'

    const base = this._localLedgerPath.replace(/^~/, home)

    return `${base}/${relativePath}`
  }

  /**
   * Read a file from the local filesystem via the desktop bridge.
   */
  private async readLocal(
    relativePath: string,
  ): Promise<string | null> {
    try {
      const result = await readDesktopFileText(
        this.localPath(relativePath),
      )

      if (result.binary) {
        console.warn(
          `[remote-bridge] ${relativePath} is binary, skipping`,
        )

        return null
      }

      return result.text
    } catch (err) {
      console.warn(
        `[remote-bridge] Error reading local ${relativePath}:`,
        err,
      )

      return null
    }
  }

  /**
   * Read a file via SSH (stub). Replace this with ssh2 or exec ssh when
   * implementing remote ledger access.
   */
  private async readRemoteViaSsh(
    _sshHost: string,
    _remotePath: string,
    _relativePath: string,
  ): Promise<string | null> {
    // TODO: Implement SSH file read using ssh2 or child_process.exec
    throw new Error('SSH remote read not yet implemented')
  }
}

// ── Convenience singleton ────────────────────────────────────────────────────

let defaultBridge: RemoteBridge | null = null

/**
 * Get or create the default bridge using env-based config.
 *
 * If REMOTE_SSH_HOST is set, the bridge will attempt remote reads.
 * Otherwise it operates in local-only mode.
 */
export function getDefaultBridge(): RemoteBridge {
  if (!defaultBridge) {
    defaultBridge = new RemoteBridge()

    const sshHost = process.env.REMOTE_SSH_HOST
    const remotePath = process.env.REMOTE_LEDGER_PATH

    if (sshHost && remotePath) {
      // Fire-and-forget connect; failures fall back to local reads.
      defaultBridge.connect(sshHost, remotePath).catch(() => {
        console.warn(
          '[remote-bridge] Default bridge connect failed, using local fallback',
        )
      })
    } else {
      // Mark as connected in local-only mode
      defaultBridge.connect('local', DEFAULT_LOCAL_PATH).catch(() => {
        /* no-op */
      })
    }
  }

  return defaultBridge
}

/**
 * Reset the default bridge (useful for testing or config changes).
 */
export function resetDefaultBridge(): void {
  if (defaultBridge) {
    defaultBridge.disconnect()
    defaultBridge = null
  }
}
