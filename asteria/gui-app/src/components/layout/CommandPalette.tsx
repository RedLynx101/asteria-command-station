import { Command } from "cmdk";
import { useStore } from "../../lib/store";
import type { View } from "../../lib/types";
import {
  Satellite,
  MessageSquareText,
  Code2,
  Camera,
  Bug,
  Wifi,
  WifiOff,
  OctagonX,
  Shield,
  ShieldOff,
  RefreshCw,
  Image,
  Play,
  Square,
  Keyboard,
} from "lucide-react";

export function CommandPalette() {
  const open = useStore((s) => s.commandPaletteOpen);
  const setOpen = useStore((s) => s.setCommandPaletteOpen);
  const setView = useStore((s) => s.setView);
  const setShortcutsOpen = useStore((s) => s.setShortcutsOpen);
  const sendAction = useStore((s) => s.sendAction);
  const claimControl = useStore((s) => s.claimControl);
  const releaseLease = useStore((s) => s.releaseLease);
  const pollStatus = useStore((s) => s.pollStatus);

  if (!open) return null;

  function run(fn: () => void) {
    fn();
    setOpen(false);
  }

  const viewIcons: Record<View, typeof Satellite> = {
    operations: Satellite,
    desk: MessageSquareText,
    fsm: Code2,
    vision: Camera,
    debug: Bug,
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => setOpen(false)}
      />
      <Command
        className="relative w-full max-w-lg bg-surface border border-border rounded-xl shadow-2xl overflow-hidden"
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
        }}
      >
        <Command.Input
          placeholder="Type a command or search..."
          className="w-full h-12 px-4 text-sm text-primary bg-transparent border-b border-border placeholder:text-tertiary outline-none"
          autoFocus
        />
        <Command.List className="max-h-72 overflow-auto p-2">
          <Command.Empty className="p-4 text-sm text-tertiary text-center">
            No results found.
          </Command.Empty>

          <Command.Group heading="Navigation" className="mb-2 [&>[cmdk-group-heading]]:text-[10px] [&>[cmdk-group-heading]]:uppercase [&>[cmdk-group-heading]]:tracking-wider [&>[cmdk-group-heading]]:text-tertiary [&>[cmdk-group-heading]]:px-2 [&>[cmdk-group-heading]]:py-1.5 [&>[cmdk-group-heading]]:font-bold">
            {(
              Object.entries(viewIcons) as [View, typeof Satellite][]
            ).map(([id, Icon]) => (
              <Command.Item
                key={id}
                value={`go to ${id}`}
                onSelect={() => run(() => setView(id))}
                className="flex items-center gap-3 px-3 py-2 text-sm rounded-lg text-secondary cursor-pointer data-[selected=true]:bg-accent-soft data-[selected=true]:text-accent"
              >
                <Icon size={16} />
                <span className="capitalize">{id}</span>
                <kbd className="ml-auto text-[10px] font-mono text-tertiary">
                  {["operations", "desk", "fsm", "vision", "debug"].indexOf(id) + 1}
                </kbd>
              </Command.Item>
            ))}
          </Command.Group>

          <Command.Group heading="Actions" className="mb-2 [&>[cmdk-group-heading]]:text-[10px] [&>[cmdk-group-heading]]:uppercase [&>[cmdk-group-heading]]:tracking-wider [&>[cmdk-group-heading]]:text-tertiary [&>[cmdk-group-heading]]:px-2 [&>[cmdk-group-heading]]:py-1.5 [&>[cmdk-group-heading]]:font-bold">
            <Command.Item
              value="connect robot"
              onSelect={() => run(() => sendAction("connect", {}, { leaseRequired: false }))}
              className="flex items-center gap-3 px-3 py-2 text-sm rounded-lg text-secondary cursor-pointer data-[selected=true]:bg-accent-soft data-[selected=true]:text-accent"
            >
              <Wifi size={16} /> Connect
            </Command.Item>
            <Command.Item
              value="disconnect robot"
              onSelect={() => run(() => sendAction("disconnect", {}, { leaseRequired: false }))}
              className="flex items-center gap-3 px-3 py-2 text-sm rounded-lg text-secondary cursor-pointer data-[selected=true]:bg-accent-soft data-[selected=true]:text-accent"
            >
              <WifiOff size={16} /> Disconnect
            </Command.Item>
            <Command.Item
              value="stop all emergency"
              onSelect={() => run(async () => { await claimControl({ force: true, refresh: false }); sendAction("stop_all", { stop_fsm: true }); })}
              className="flex items-center gap-3 px-3 py-2 text-sm rounded-lg text-danger cursor-pointer data-[selected=true]:bg-danger-soft data-[selected=true]:text-danger"
            >
              <OctagonX size={16} /> Stop All
            </Command.Item>
            <Command.Item
              value="claim lease control"
              onSelect={() => run(() => claimControl({ force: true, refresh: true }))}
              className="flex items-center gap-3 px-3 py-2 text-sm rounded-lg text-secondary cursor-pointer data-[selected=true]:bg-accent-soft data-[selected=true]:text-accent"
            >
              <Shield size={16} /> Claim Control
            </Command.Item>
            <Command.Item
              value="release lease control"
              onSelect={() => run(() => releaseLease())}
              className="flex items-center gap-3 px-3 py-2 text-sm rounded-lg text-secondary cursor-pointer data-[selected=true]:bg-accent-soft data-[selected=true]:text-accent"
            >
              <ShieldOff size={16} /> Release Lease
            </Command.Item>
            <Command.Item
              value="refresh status"
              onSelect={() => run(() => pollStatus())}
              className="flex items-center gap-3 px-3 py-2 text-sm rounded-lg text-secondary cursor-pointer data-[selected=true]:bg-accent-soft data-[selected=true]:text-accent"
            >
              <RefreshCw size={16} /> Refresh Status
            </Command.Item>
            <Command.Item
              value="capture image"
              onSelect={() => run(() => sendAction("capture_image", {}, { refreshAfter: true }))}
              className="flex items-center gap-3 px-3 py-2 text-sm rounded-lg text-secondary cursor-pointer data-[selected=true]:bg-accent-soft data-[selected=true]:text-accent"
            >
              <Image size={16} /> Capture Image
            </Command.Item>
            <Command.Item
              value="run fsm"
              onSelect={() => {
                run(() => setView("fsm"));
              }}
              className="flex items-center gap-3 px-3 py-2 text-sm rounded-lg text-secondary cursor-pointer data-[selected=true]:bg-accent-soft data-[selected=true]:text-accent"
            >
              <Play size={16} /> Open FSM Editor
            </Command.Item>
            <Command.Item
              value="unload fsm stop"
              onSelect={() => run(() => sendAction("unload_fsm"))}
              className="flex items-center gap-3 px-3 py-2 text-sm rounded-lg text-secondary cursor-pointer data-[selected=true]:bg-accent-soft data-[selected=true]:text-accent"
            >
              <Square size={16} /> Unload FSM
            </Command.Item>
          </Command.Group>

          <Command.Group heading="Help" className="[&>[cmdk-group-heading]]:text-[10px] [&>[cmdk-group-heading]]:uppercase [&>[cmdk-group-heading]]:tracking-wider [&>[cmdk-group-heading]]:text-tertiary [&>[cmdk-group-heading]]:px-2 [&>[cmdk-group-heading]]:py-1.5 [&>[cmdk-group-heading]]:font-bold">
            <Command.Item
              value="keyboard shortcuts help"
              onSelect={() => run(() => setShortcutsOpen(true))}
              className="flex items-center gap-3 px-3 py-2 text-sm rounded-lg text-secondary cursor-pointer data-[selected=true]:bg-accent-soft data-[selected=true]:text-accent"
            >
              <Keyboard size={16} /> Keyboard Shortcuts
            </Command.Item>
          </Command.Group>
        </Command.List>
      </Command>
    </div>
  );
}
