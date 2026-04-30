import { useEffect, useRef } from "react";
import { EditorView, basicSetup } from "codemirror";
import { python } from "@codemirror/lang-python";
import { oneDark } from "@codemirror/theme-one-dark";
import { EditorState } from "@codemirror/state";
import { useStore } from "../../lib/store";

const lightTheme = EditorView.theme({
  "&": { backgroundColor: "#f7fbfb", color: "#153331" },
  ".cm-gutters": { backgroundColor: "#f0f6f5", borderRight: "1px solid #d5e7e5" },
  ".cm-activeLineGutter": { backgroundColor: "#e8f0ef" },
  ".cm-activeLine": { backgroundColor: "#e8f0ef40" },
});

interface FsmEditorProps {
  value: string;
  onChange: (value: string) => void;
}

export function FsmCodeEditor({ value, onChange }: FsmEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const theme = useStore((s) => s.theme);

  useEffect(() => {
    if (!containerRef.current) return;

    const state = EditorState.create({
      doc: value,
      extensions: [
        basicSetup,
        python(),
        theme === "dark" ? oneDark : lightTheme,
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            onChange(update.state.doc.toString());
          }
        }),
        EditorView.theme({
          "&": { height: "100%", fontSize: "13px" },
          ".cm-scroller": { overflow: "auto" },
        }),
      ],
    });

    const view = new EditorView({ state, parent: containerRef.current });
    viewRef.current = view;

    return () => {
      view.destroy();
      viewRef.current = null;
    };
    // Intentionally only re-create on theme change, not value
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme]);

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const currentDoc = view.state.doc.toString();
    if (currentDoc !== value) {
      view.dispatch({
        changes: { from: 0, to: currentDoc.length, insert: value },
      });
    }
  }, [value]);

  return (
    <div
      ref={containerRef}
      className="h-[460px] border border-border rounded-lg overflow-hidden"
    />
  );
}
