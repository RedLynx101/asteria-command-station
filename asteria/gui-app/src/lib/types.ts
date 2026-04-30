export interface Pose {
  x: number;
  y: number;
  heading: number;
}

export interface Telemetry {
  connected: boolean;
  host?: string;
  battery_pct?: number;
  pose?: Pose;
  running_fsm_name?: string;
  running_fsm_active?: boolean;
  last_error?: string;
}

export interface Lease {
  holder_id?: string;
  holder_label?: string;
  holder_kind?: string;
  expires_at_epoch?: number;
}

export interface ConnectionInfo {
  active_profile?: string;
  profiles?: string[];
  resolved_host?: string;
  profile_robot_id?: string;
  profile_robot_host?: string;
  target_source?: string;
  override_target_input?: string;
  fallback_hosts?: string[];
  connected_runtime_mode?: string;
  supports_fsm_runtime?: boolean;
  diagnostics?: { timestamp: string | null; items: unknown[] };
}

export interface LatestImage {
  url?: string;
  captured_at?: string;
}

export interface SafeLimits {
  max_move_mm?: number;
  max_turn_deg?: number;
}

export interface LastResult {
  ok?: boolean;
  error?: string;
  message?: string;
  warning?: string;
  timestamp?: string;
  generated_py?: string;
  generated_exists?: boolean;
  image_path?: string;
}

export interface FsmFile {
  name: string;
  content?: string;
  generated_py?: string;
  generated_exists?: boolean;
}

export interface Prompt {
  id: string;
  text?: string;
  response?: string;
  status?: string;
  forward_mode?: string;
  submitted_at?: string;
  submitted_label?: string;
  resolved_at?: string;
  resolved_label?: string;
  forward_status?: string;
  forward_error?: string;
  forwarded_at?: string;
  bridge_session_key?: string;
}

export interface Activity {
  title?: string;
  actor_label?: string;
  timestamp?: string;
  kind?: string;
  detail?: string;
  related_action?: string;
  status?: string;
}

export interface RecentCommand {
  action?: string;
  timestamp?: string;
  payload?: Record<string, unknown>;
}

export interface Paths {
  asteria_root?: string;
  repo_root?: string;
}

export interface CodexJob {
  prompt_id: string;
  pid: string;
  model?: string;
  started_at?: string;
  output_tail?: string[];
  alive?: boolean;
}

export interface AsteriaStatus {
  telemetry?: Telemetry;
  lease?: Lease;
  connection?: ConnectionInfo;
  latest_image?: LatestImage;
  safe_limits?: SafeLimits;
  last_result?: LastResult;
  fsm_files?: FsmFile[];
  prompts?: Prompt[];
  activities?: Activity[];
  recent_commands?: RecentCommand[];
  paths?: Paths;
  codex_jobs?: CodexJob[];
  codex_model?: string;
  codex_timeout_minutes?: number;
  ok?: boolean;
  error?: string;
  message?: string;
  warning?: string;
  name?: string;
}

export type View = "operations" | "desk" | "fsm" | "vision" | "debug";
