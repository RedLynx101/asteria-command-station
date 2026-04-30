import { Camera } from "lucide-react";
import { useStore } from "../../lib/store";
import { Card, CardHeader, CardTitle, Eyebrow } from "../ui/Card";
import { Button } from "../ui/Button";

export function MiniImagePreview() {
  const status = useStore((s) => s.status);
  const setView = useStore((s) => s.setView);
  const image = status.latest_image ?? {};

  return (
    <Card>
      <CardHeader>
        <div>
          <Eyebrow>Latest capture</Eyebrow>
          <CardTitle>Vision preview</CardTitle>
        </div>
        <Button size="sm" variant="ghost" onClick={() => setView("vision")}>
          Open Vision
        </Button>
      </CardHeader>
      <div className="relative min-h-[200px] bg-bg-inset border border-border rounded-lg overflow-hidden flex items-center justify-center">
        {image.url ? (
          <img
            src={image.url}
            alt="Latest robot capture"
            className="w-full h-full object-cover cursor-pointer"
            onClick={() => setView("vision")}
          />
        ) : (
          <div className="flex flex-col items-center gap-2 text-tertiary">
            <Camera size={28} strokeWidth={1.5} />
            <span className="text-xs font-medium">No image yet</span>
          </div>
        )}
      </div>
    </Card>
  );
}
