import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Card } from "../ui/Card";

interface JsonViewerProps {
  title: string;
  data: unknown;
  testId?: string;
}

export function JsonViewer({ title, data, testId }: JsonViewerProps) {
  const [open, setOpen] = useState(false);

  return (
    <Card>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full text-left text-sm font-bold text-primary cursor-pointer"
        data-testid={testId}
      >
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        {title}
      </button>
      {open && (
        <pre className="mt-3 bg-bg-inset text-accent text-xs leading-relaxed p-4 rounded-lg overflow-auto max-h-[480px] font-mono">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </Card>
  );
}
