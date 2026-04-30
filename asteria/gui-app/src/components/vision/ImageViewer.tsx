import { useState } from "react";
import { Camera, X, ZoomIn, ZoomOut } from "lucide-react";
import { useStore } from "../../lib/store";
import { Card, CardHeader, CardTitle, Eyebrow } from "../ui/Card";
import { Button } from "../ui/Button";

export function ImageViewer() {
  const status = useStore((s) => s.status);
  const sendAction = useStore((s) => s.sendAction);
  const pollStatus = useStore((s) => s.pollStatus);
  const image = status.latest_image ?? {};
  const [lightbox, setLightbox] = useState(false);
  const [zoom, setZoom] = useState(1);

  return (
    <>
      <Card>
        <CardHeader>
          <div>
            <Eyebrow>Vision</Eyebrow>
            <CardTitle>Image viewer</CardTitle>
          </div>
          <div className="flex gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={() =>
                sendAction("capture_image", {}, { refreshAfter: true })
              }
            >
              <Camera size={13} /> Capture
            </Button>
            <Button size="sm" onClick={() => pollStatus()}>
              Refresh
            </Button>
          </div>
        </CardHeader>
        <div
          className="relative min-h-[480px] bg-bg-inset border border-border rounded-lg overflow-hidden flex items-center justify-center cursor-pointer"
          onClick={() => image.url && setLightbox(true)}
        >
          {image.url ? (
            <img
              src={image.url}
              alt="Robot camera frame"
              className="w-full h-full object-contain"
            />
          ) : (
            <div className="flex flex-col items-center gap-3 text-tertiary">
              <Camera size={40} strokeWidth={1.2} />
              <span className="text-sm font-medium">
                No captured image available
              </span>
              <span className="text-xs">
                Click Capture to take a photo from the robot camera.
              </span>
            </div>
          )}
        </div>
      </Card>

      {/* Lightbox */}
      {lightbox && image.url && (
        <div className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center">
          <div className="absolute top-4 right-4 flex gap-2 z-10">
            <button
              onClick={() => setZoom((z) => Math.min(z + 0.5, 4))}
              className="flex items-center justify-center w-10 h-10 rounded-xl bg-white/10 text-white hover:bg-white/20 transition-colors cursor-pointer"
            >
              <ZoomIn size={18} />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(z - 0.5, 0.5))}
              className="flex items-center justify-center w-10 h-10 rounded-xl bg-white/10 text-white hover:bg-white/20 transition-colors cursor-pointer"
            >
              <ZoomOut size={18} />
            </button>
            <button
              onClick={() => {
                setLightbox(false);
                setZoom(1);
              }}
              className="flex items-center justify-center w-10 h-10 rounded-xl bg-white/10 text-white hover:bg-white/20 transition-colors cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>
          <img
            src={image.url}
            alt="Robot camera frame (full)"
            className="max-w-[90vw] max-h-[90vh] object-contain transition-transform duration-200"
            style={{ transform: `scale(${zoom})` }}
            onClick={(e) => e.stopPropagation()}
          />
          <div
            className="absolute inset-0 -z-10"
            onClick={() => {
              setLightbox(false);
              setZoom(1);
            }}
          />
        </div>
      )}
    </>
  );
}
