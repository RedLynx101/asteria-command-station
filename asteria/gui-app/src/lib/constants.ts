import type { View } from "./types";

export const VIEWS: View[] = ["operations", "desk", "fsm", "vision", "debug"];
export const DEFAULT_VIEW: View = "operations";
export const POLL_INTERVAL_MS = 5000;
export const LEASE_RENEW_INTERVAL_MS = 20000;
export const LEASE_EXPIRY_BUFFER_MS = 8000;

export const HOLDER = {
  holder_id: "local-gui",
  holder_label: "Local GUI",
  holder_kind: "human",
} as const;

export const LEASE_GATED_ACTIONS = new Set([
  "run_fsm",
  "unload_fsm",
  "send_text",
  "send_speech",
  "stop_all",
  "capture_image",
  "move",
  "sideways",
  "turn",
  "say",
  "kick",
]);

export const AUDIO_MANIFEST: Record<string, string> = {
  click: "/assets/audio/tab.wav",
  success: "/assets/audio/receive.wav",
  send: "/assets/audio/send.wav",
  warning: "/assets/audio/error.wav",
  alert: "/assets/audio/stop.wav",
};
