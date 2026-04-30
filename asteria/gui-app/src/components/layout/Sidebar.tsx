import {
  Satellite,
  MessageSquareText,
  Code2,
  Camera,
  Bug,
} from "lucide-react";
import { useStore } from "../../lib/store";
import type { View } from "../../lib/types";

interface NavItem {
  id: View;
  label: string;
  shortcut: string;
  icon: typeof Satellite;
}

const NAV_ITEMS: NavItem[] = [
  { id: "operations", label: "Operations", shortcut: "1", icon: Satellite },
  { id: "desk", label: "Desk", shortcut: "2", icon: MessageSquareText },
  { id: "fsm", label: "FSM", shortcut: "3", icon: Code2 },
  { id: "vision", label: "Vision", shortcut: "4", icon: Camera },
  { id: "debug", label: "Debug", shortcut: "5", icon: Bug },
];

export function Sidebar() {
  const view = useStore((s) => s.view);
  const setView = useStore((s) => s.setView);
  const collapsed = useStore((s) => s.sidebarCollapsed);

  return (
    <aside
      className={`flex flex-col bg-sidebar-bg border-r border-border shrink-0 transition-all duration-200 ${
        collapsed ? "w-14" : "w-52"
      }`}
    >
      {/* Brand */}
      <div className={`flex items-center gap-3 px-3 h-14 border-b border-border ${collapsed ? "justify-center" : ""}`}>
        <img
          src="/assets/icons/asteria-icon.svg"
          alt="Asteria"
          className="w-8 h-8 rounded-lg shrink-0"
        />
        {!collapsed && (
          <div className="min-w-0">
            <div className="text-sm font-bold text-primary truncate tracking-tight">
              Asteria
            </div>
            <div className="text-[10px] text-tertiary font-medium">
              Command Station
            </div>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-2 px-2 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const active = view === item.id;
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => setView(item.id)}
              className={`flex items-center gap-2.5 w-full h-9 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
                collapsed ? "justify-center px-0" : "px-2.5"
              } ${
                active
                  ? "bg-sidebar-active text-accent"
                  : "text-secondary hover:text-primary hover:bg-sidebar-hover"
              }`}
              title={collapsed ? item.label : undefined}
            >
              <Icon size={18} className="shrink-0" />
              {!collapsed && (
                <>
                  <span className="truncate">{item.label}</span>
                  <kbd className="ml-auto text-[10px] text-tertiary font-mono">
                    {item.shortcut}
                  </kbd>
                </>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer hint */}
      {!collapsed && (
        <div className="px-3 py-3 border-t border-border">
          <div className="text-[10px] text-tertiary leading-relaxed">
            Press <kbd className="font-mono bg-surface-raised px-1 py-0.5 rounded text-secondary">⌘K</kbd> for
            command palette
          </div>
        </div>
      )}
    </aside>
  );
}
