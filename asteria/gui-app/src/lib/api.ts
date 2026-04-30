import type { AsteriaStatus } from "./types";
import { HOLDER } from "./constants";

export async function fetchJson<T = AsteriaStatus>(
  url: string,
  options: RequestInit & { body?: string } = {},
): Promise<T> {
  const response = await fetch(url, {
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
    ...options,
  });

  const raw = await response.text();
  let payload: T = {} as T;
  if (raw) {
    try {
      payload = JSON.parse(raw) as T;
    } catch {
      throw new Error(raw);
    }
  }

  if (!response.ok) {
    throw new Error(
      (payload as Record<string, string>).error ||
        `${response.status} ${response.statusText}`,
    );
  }

  return payload;
}

export async function sendCommand(
  action: string,
  payload: Record<string, unknown> = {},
): Promise<AsteriaStatus> {
  return fetchJson<AsteriaStatus>("/api/command", {
    method: "POST",
    body: JSON.stringify({ action, ...HOLDER, ...payload }),
  });
}

export async function claimLease(
  force = false,
): Promise<AsteriaStatus & { lease?: AsteriaStatus["lease"] }> {
  return fetchJson("/api/lease/claim", {
    method: "POST",
    body: JSON.stringify({ ...HOLDER, force }),
  });
}

export async function releaseLease(): Promise<AsteriaStatus> {
  return fetchJson("/api/lease/release", {
    method: "POST",
    body: JSON.stringify({ ...HOLDER }),
  });
}

export async function fetchStatus(): Promise<AsteriaStatus> {
  return fetchJson<AsteriaStatus>("/api/status");
}
