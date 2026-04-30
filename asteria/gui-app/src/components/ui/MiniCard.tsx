import type { ReactNode } from "react";

type Kind = "default" | "success" | "ok" | "warning" | "warn" | "pending" | "info" | "empty" | "error";

const kindStyles: Record<Kind, string> = {
  default: "border-border bg-surface-raised",
  info: "border-border bg-surface-raised",
  empty: "border-border bg-surface-raised",
  success: "border-success/20 bg-success-soft",
  ok: "border-success/20 bg-success-soft",
  warning: "border-warning/20 bg-warning-soft",
  warn: "border-warning/20 bg-warning-soft",
  pending: "border-accent/20 bg-accent-soft",
  error: "border-danger/20 bg-danger-soft",
};

export function MiniCard({
  title,
  meta,
  body,
  note,
  kind = "default",
  statusSlot,
  actions,
}: {
  title: string;
  meta?: string;
  body?: string;
  note?: string;
  kind?: Kind;
  statusSlot?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className={`border rounded-lg p-3 ${kindStyles[kind] || kindStyles.default}`}>
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-semibold text-primary">{title}</span>
        {meta && (
          <span className="text-[11px] text-tertiary whitespace-nowrap shrink-0">
            {meta}
          </span>
        )}
      </div>
      {body && (
        <p className="mt-1.5 text-xs text-secondary whitespace-pre-wrap break-words leading-relaxed">
          {body}
        </p>
      )}
      {statusSlot && <div className="mt-2">{statusSlot}</div>}
      {note && (
        <p className="mt-1.5 text-[11px] text-tertiary leading-relaxed">
          {note}
        </p>
      )}
      {actions && <div className="mt-2 flex justify-end">{actions}</div>}
    </div>
  );
}
