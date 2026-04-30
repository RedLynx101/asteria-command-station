import type { ReactNode } from "react";
import { useState } from "react";
import { Menu, X } from "lucide-react";
import { StatusBar } from "./StatusBar";
import { Sidebar } from "./Sidebar";
import { CommandPalette } from "./CommandPalette";
import { ShortcutsOverlay } from "./ShortcutsOverlay";

export function AppShell({ children }: { children: ReactNode }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Desktop sidebar */}
      <div className="hidden md:flex">
        <Sidebar />
      </div>

      {/* Mobile nav overlay */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setMobileNavOpen(false)}
          />
          <div className="relative w-60 h-full">
            <Sidebar />
          </div>
        </div>
      )}

      <div className="flex flex-col flex-1 min-w-0">
        <StatusBar />

        {/* Mobile menu button */}
        <div className="flex md:hidden items-center px-3 py-2 border-b border-border bg-surface">
          <button
            onClick={() => setMobileNavOpen(!mobileNavOpen)}
            className="flex items-center gap-2 text-sm text-secondary hover:text-primary transition-colors cursor-pointer"
          >
            {mobileNavOpen ? <X size={18} /> : <Menu size={18} />}
            <span className="font-medium">Menu</span>
          </button>
        </div>

        <main className="flex-1 overflow-y-auto p-4 md:p-5">
          {children}
        </main>
      </div>
      <CommandPalette />
      <ShortcutsOverlay />
    </div>
  );
}
