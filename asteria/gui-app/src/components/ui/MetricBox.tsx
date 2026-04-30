type Severity = "" | "success" | "warning" | "danger";

const severityStyles: Record<string, string> = {
  "": "",
  success: "border-success/20",
  warning: "border-warning/20",
  danger: "border-danger/20",
};

const valueStyles: Record<string, string> = {
  "": "text-primary",
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
};

export function MetricBox({
  label,
  value,
  severity = "",
}: {
  label: string;
  value: string;
  severity?: Severity;
}) {
  return (
    <div
      className={`bg-surface-raised border border-border rounded-lg p-3 min-w-0 ${severityStyles[severity]}`}
    >
      <div className="text-[10px] font-bold uppercase tracking-wider text-tertiary mb-1">
        {label}
      </div>
      <div
        className={`text-sm font-semibold break-words ${valueStyles[severity]}`}
      >
        {value}
      </div>
    </div>
  );
}
