import { useStore } from "../../lib/store";
import { Card, CardHeader, CardTitle, Eyebrow } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { MiniCard } from "../ui/MiniCard";
import { formatTimestamp } from "../../lib/format";

export function ActivityTimeline() {
  const status = useStore((s) => s.status);
  const activities = [...(status.activities ?? [])].reverse();

  return (
    <Card>
      <CardHeader>
        <div>
          <Eyebrow>Activity</Eyebrow>
          <CardTitle>Recent feed</CardTitle>
        </div>
        <Badge>{activities.length} events</Badge>
      </CardHeader>
      <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
        {activities.length === 0 ? (
          <MiniCard
            title="No activity yet"
            body="Commands, prompts, and lease changes will show up here."
          />
        ) : (
          activities.map((item, i) => (
            <MiniCard
              key={i}
              title={item.title ?? "Activity"}
              meta={`${item.actor_label ?? "Unknown"} | ${formatTimestamp(item.timestamp)} | ${item.kind ?? "event"}`}
              body={item.detail ?? `${item.related_action ?? "event"} recorded`}
              kind={
                (item.status as "success" | "warning" | "pending" | "info") ??
                "info"
              }
            />
          ))
        )}
      </div>
    </Card>
  );
}
