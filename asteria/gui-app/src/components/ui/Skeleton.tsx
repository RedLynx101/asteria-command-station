export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-lg bg-surface-raised ${className}`}
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="bg-surface border border-border rounded-xl p-4 space-y-3">
      <Skeleton className="h-3 w-20" />
      <Skeleton className="h-5 w-40" />
      <Skeleton className="h-16 w-full" />
    </div>
  );
}
