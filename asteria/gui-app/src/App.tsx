import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Toaster } from "sonner";
import { useStore } from "./lib/store";
import { useKeyboardShortcuts } from "./lib/use-keyboard";
import { initAudio } from "./lib/audio";
import { AppShell } from "./components/layout/AppShell";
import { OperationsView } from "./components/views/OperationsView";
import { DeskView } from "./components/views/DeskView";
import { FsmView } from "./components/views/FsmView";
import { VisionView } from "./components/views/VisionView";
import { DebugView } from "./components/views/DebugView";

const viewComponents = {
  operations: OperationsView,
  desk: DeskView,
  fsm: FsmView,
  vision: VisionView,
  debug: DebugView,
};

const pageVariants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
};

export default function App() {
  const view = useStore((s) => s.view);
  const theme = useStore((s) => s.theme);
  const startPolling = useStore((s) => s.startPolling);
  const stopPolling = useStore((s) => s.stopPolling);
  const setView = useStore((s) => s.setView);

  useKeyboardShortcuts();

  useEffect(() => {
    initAudio();
    startPolling();

    // Sync initial theme class
    document.documentElement.classList.remove("dark", "light");
    document.documentElement.classList.add(theme);

    // Sync hash to view
    const hash = window.location.hash.replace("#", "");
    if (hash && hash in viewComponents) {
      setView(hash as keyof typeof viewComponents);
    }

    return () => stopPolling();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const ViewComponent = viewComponents[view];

  return (
    <>
      <AppShell>
        <AnimatePresence mode="wait">
          <motion.div
            key={view}
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.15, ease: "easeOut" }}
          >
            <ViewComponent />
          </motion.div>
        </AnimatePresence>
      </AppShell>
      <Toaster
        theme={theme}
        position="bottom-right"
        richColors
        closeButton
        toastOptions={{
          className: "text-sm",
        }}
      />
    </>
  );
}
