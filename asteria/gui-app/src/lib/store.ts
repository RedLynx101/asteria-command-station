import { create } from "zustand";
import type { AsteriaStatus, View } from "./types";
import {
  DEFAULT_VIEW,
  HOLDER,
  LEASE_EXPIRY_BUFFER_MS,
  LEASE_GATED_ACTIONS,
  LEASE_RENEW_INTERVAL_MS,
  POLL_INTERVAL_MS,
} from "./constants";
import {
  claimLease,
  fetchStatus,
  releaseLease as apiReleaseLease,
  sendCommand,
} from "./api";
import { playCue } from "./audio";
import { toast } from "sonner";

function leaseExpiresAtMs(lease: AsteriaStatus["lease"] = {}): number {
  const epoch = Number(lease?.expires_at_epoch ?? 0);
  return Number.isFinite(epoch) ? epoch * 1000 : 0;
}

function isLocalGuiLease(lease: AsteriaStatus["lease"] = {}): boolean {
  return (
    lease?.holder_id === HOLDER.holder_id &&
    lease?.holder_kind === HOLDER.holder_kind
  );
}

function hasUsableLocalLease(lease: AsteriaStatus["lease"] = {}): boolean {
  return (
    isLocalGuiLease(lease) &&
    leaseExpiresAtMs(lease) > Date.now() + LEASE_EXPIRY_BUFFER_MS
  );
}

interface AppState {
  // Core state
  status: AsteriaStatus;
  view: View;
  theme: "dark" | "light";
  sidebarCollapsed: boolean;
  commandPaletteOpen: boolean;
  shortcutsOpen: boolean;

  // FSM editor state
  selectedFsm: string | null;
  editorDirty: boolean;
  lastRenderedFsm: string | null;

  // Preferences
  stopAllUnloadsFsm: boolean;
  continuousDirectControl: boolean;

  // Internal -- _leaseOwnedByGui is true only when the user explicitly
  // claimed the lease from this GUI session (click Claim / command palette).
  // Passive polling never auto-claims or auto-renews without it.
  _pollTimer: ReturnType<typeof setInterval> | null;
  _leaseTimer: ReturnType<typeof setInterval> | null;
  _leaseRenewInFlight: Promise<AsteriaStatus> | null;
  _leaseOwnedByGui: boolean;

  // Actions
  setView: (view: View) => void;
  setTheme: (theme: "dark" | "light") => void;
  toggleSidebar: () => void;
  setCommandPaletteOpen: (open: boolean) => void;
  setShortcutsOpen: (open: boolean) => void;
  setSelectedFsm: (name: string | null) => void;
  setEditorDirty: (dirty: boolean) => void;
  setStopAllUnloadsFsm: (value: boolean) => void;
  setContinuousDirectControl: (value: boolean) => void;

  // Async
  pollStatus: () => Promise<void>;
  startPolling: () => void;
  stopPolling: () => void;
  sendAction: (
    action: string,
    payload?: Record<string, unknown>,
    opts?: { leaseRequired?: boolean; refreshAfter?: boolean },
  ) => Promise<AsteriaStatus | null>;
  claimControl: (opts?: {
    force?: boolean;
    refresh?: boolean;
  }) => Promise<AsteriaStatus>;
  renewLease: (opts?: {
    force?: boolean;
    refresh?: boolean;
  }) => Promise<AsteriaStatus>;
  releaseLease: () => Promise<void>;
}

function readBool(key: string, fallback: boolean): boolean {
  try {
    const raw = localStorage.getItem(key);
    return raw == null ? fallback : raw === "true";
  } catch {
    return fallback;
  }
}

function writeBool(key: string, value: boolean) {
  try {
    localStorage.setItem(key, String(value));
  } catch {
    /* noop */
  }
}

function getInitialTheme(): "dark" | "light" {
  try {
    const stored = localStorage.getItem("asteria.theme");
    if (stored === "dark" || stored === "light") return stored;
  } catch {
    /* noop */
  }
  return window.matchMedia?.("(prefers-color-scheme: light)").matches
    ? "light"
    : "dark";
}

export const useStore = create<AppState>((set, get) => ({
  status: {},
  view: DEFAULT_VIEW,
  theme: getInitialTheme(),
  sidebarCollapsed: false,
  commandPaletteOpen: false,
  shortcutsOpen: false,
  selectedFsm: null,
  editorDirty: false,
  lastRenderedFsm: null,
  stopAllUnloadsFsm: readBool("asteria.stopAllUnloadsFsm", true),
  continuousDirectControl: readBool("asteria.continuousDirectControl", false),
  _pollTimer: null,
  _leaseTimer: null,
  _leaseRenewInFlight: null,
  _leaseOwnedByGui: false,

  setView: (view) => {
    set({ view });
    history.replaceState(null, "", `#${view}`);
    playCue("click");
  },

  setTheme: (theme) => {
    set({ theme });
    localStorage.setItem("asteria.theme", theme);
    const root = document.documentElement;
    root.classList.add("theme-transition");
    root.classList.remove("dark", "light");
    root.classList.add(theme);
    setTimeout(() => root.classList.remove("theme-transition"), 350);
  },

  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
  setShortcutsOpen: (open) => set({ shortcutsOpen: open }),

  setSelectedFsm: (name) =>
    set({ selectedFsm: name, editorDirty: false, lastRenderedFsm: null }),
  setEditorDirty: (dirty) => set({ editorDirty: dirty }),

  setStopAllUnloadsFsm: (value) => {
    set({ stopAllUnloadsFsm: value });
    writeBool("asteria.stopAllUnloadsFsm", value);
  },

  setContinuousDirectControl: (value) => {
    set({ continuousDirectControl: value });
    writeBool("asteria.continuousDirectControl", value);
  },

  pollStatus: async () => {
    try {
      const status = await fetchStatus();
      set({ status });

      // Only auto-renew the lease if the user explicitly claimed it from
      // this GUI session.  Passive observation never grabs or holds the
      // lease so the agent (or another holder) keeps control.
      const lease = status.lease;
      const state = get();
      if (
        state._leaseOwnedByGui &&
        isLocalGuiLease(lease) &&
        leaseExpiresAtMs(lease) > Date.now()
      ) {
        if (!state._leaseTimer) {
          const timer = setInterval(async () => {
            try {
              await get().renewLease({ force: false, refresh: false });
            } catch {
              clearInterval(get()._leaseTimer!);
              set({ _leaseTimer: null, _leaseOwnedByGui: false });
            }
          }, LEASE_RENEW_INTERVAL_MS);
          set({ _leaseTimer: timer });
        }
      } else if (!state._leaseOwnedByGui && state._leaseTimer) {
        // Lease was released or taken by someone else; stop renewing.
        clearInterval(state._leaseTimer);
        set({ _leaseTimer: null });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      set((s) => ({
        status: {
          ...s.status,
          last_result: {
            ok: false,
            error: msg,
            message: msg,
            timestamp: new Date().toISOString(),
          },
        },
      }));
    }
  },

  startPolling: () => {
    const state = get();
    if (state._pollTimer) clearInterval(state._pollTimer);
    get().pollStatus();
    const timer = setInterval(() => get().pollStatus(), POLL_INTERVAL_MS);
    set({ _pollTimer: timer });
  },

  stopPolling: () => {
    const state = get();
    if (state._pollTimer) clearInterval(state._pollTimer);
    if (state._leaseTimer) clearInterval(state._leaseTimer);
    set({ _pollTimer: null, _leaseTimer: null });
  },

  sendAction: async (action, payload = {}, opts = {}) => {
    const leaseRequired =
      opts.leaseRequired ?? LEASE_GATED_ACTIONS.has(action);

    if (leaseRequired && !hasUsableLocalLease(get().status.lease)) {
      const state = get();
      if (state._leaseOwnedByGui) {
        // We previously claimed -- try a silent re-acquire.
        try {
          await get().renewLease({ force: false, refresh: true });
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          toast.error("Lease unavailable", { description: msg });
          playCue("warning");
          return null;
        }
      } else {
        // Never claimed -- don't steal, just tell the user.
        toast.error("Claim control first", {
          description:
            "Press Claim in the status bar or use ⌘K → Claim Control before sending lease-gated actions.",
        });
        playCue("warning");
        return null;
      }
    }

    try {
      const response = await sendCommand(action, payload);
      set({ status: response });

      if (response.ok === false || response.error) {
        toast.error(response.error || "Action failed", {
          description: response.warning,
        });
        playCue("warning");
      } else if (response.warning) {
        toast.warning(response.message || "Warning", {
          description: response.warning,
        });
        playCue("warning");
      } else {
        const msg = response.last_result?.message || response.message;
        if (msg) {
          toast.success(msg);
        }
        playCue(action === "stop_all" ? "alert" : "success");
      }

      if (opts.refreshAfter) {
        await get().pollStatus();
      }

      return response;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error("Command failed", { description: msg });
      playCue("warning");
      return null;
    }
  },

  claimControl: async (opts = {}) => {
    // Explicit user action -- sets the ownership flag so auto-renew kicks in.
    const response = await claimLease(opts.force ?? true);
    set((s) => ({
      _leaseOwnedByGui: true,
      status: { ...s.status, lease: response.lease ?? s.status.lease },
    }));
    if (opts.refresh) await get().pollStatus();
    return response;
  },

  renewLease: async (opts = {}) => {
    let inflight = get()._leaseRenewInFlight;
    if (inflight) return inflight;

    inflight = (async () => {
      const response = await claimLease(opts.force ?? false);
      set((s) => ({
        status: { ...s.status, lease: response.lease ?? s.status.lease },
      }));
      if (opts.refresh) await get().pollStatus();
      return response;
    })();

    set({ _leaseRenewInFlight: inflight });
    try {
      return await inflight;
    } finally {
      set({ _leaseRenewInFlight: null });
    }
  },

  releaseLease: async () => {
    try {
      const response = await apiReleaseLease();
      const state = get();
      if (state._leaseTimer) {
        clearInterval(state._leaseTimer);
      }
      set({
        _leaseTimer: null,
        _leaseOwnedByGui: false,
        status: { ...get().status, lease: response.lease ?? {} },
      });
      await get().pollStatus();
      toast.success("Lease released");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error("Failed to release lease", { description: msg });
    }
  },
}));
