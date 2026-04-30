import type { ReactNode } from "react";

type Variant = "default" | "accent" | "success" | "warning" | "danger";

const variants: Record<Variant, string> = {
  default: "bg-surface-raised border-border text-secondary",
  accent: "bg-accent-soft border-accent/20 text-accent",
  success: "bg-success-soft border-success/20 text-success",
  warning: "bg-warning-soft border-warning/20 text-warning",
  danger: "bg-danger-soft border-danger/20 text-danger",
};

export function Badge({
  children,
  variant = "default",
  className = "",
}: {
  children: ReactNode;
  variant?: Variant;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center h-6 px-2.5 text-[11px] font-bold rounded-full border whitespace-nowrap ${variants[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
