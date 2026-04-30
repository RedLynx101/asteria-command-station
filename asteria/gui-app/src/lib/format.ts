import type { Lease, Pose } from "./types";
import { HOLDER, LEASE_EXPIRY_BUFFER_MS } from "./constants";

export function formatBattery(value?: number): string {
  if (value == null || Number.isNaN(Number(value))) return "n/a";
  return `${Math.round(Number(value))}%`;
}

export function formatPose(pose?: Pose): string {
  if (!pose || pose.x == null || pose.y == null || pose.heading == null)
    return "n/a";
  return `${Number(pose.x).toFixed(1)} / ${Number(pose.y).toFixed(1)} / ${Number(pose.heading).toFixed(1)}°`;
}

export function formatTimestamp(value?: string): string {
  if (!value) return "n/a";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString([], {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    month: "short",
    day: "numeric",
  });
}

export function leaseExpiresAtMs(lease: Lease = {}): number {
  const epoch = Number(lease.expires_at_epoch ?? 0);
  return Number.isFinite(epoch) ? epoch * 1000 : 0;
}

export function formatLease(lease: Lease = {}): string {
  if (!lease.holder_id) return "Unclaimed";
  const expiresMs = leaseExpiresAtMs(lease);
  const ttl =
    expiresMs > 0
      ? Math.max(0, Math.ceil((expiresMs - Date.now()) / 1000))
      : 0;
  const ttlText = ttl > 0 ? ` (${ttl}s)` : "";
  return `${lease.holder_label || lease.holder_id}${ttlText}`;
}

export function isLocalGuiLease(lease: Lease = {}): boolean {
  return (
    lease.holder_id === HOLDER.holder_id &&
    lease.holder_kind === HOLDER.holder_kind
  );
}

export function hasUsableLocalLease(lease: Lease = {}): boolean {
  return (
    isLocalGuiLease(lease) &&
    leaseExpiresAtMs(lease) > Date.now() + LEASE_EXPIRY_BUFFER_MS
  );
}
