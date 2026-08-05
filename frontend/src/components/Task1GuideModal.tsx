import { useEffect, useMemo, useRef } from "react";
import { createPortal } from "react-dom";
import guideMarkdown from "../content/task-1-planning-guide.md?raw";
import { extractTask1Guide, parseGuideBlocks, type GuideBlock } from "../lib/task1Guide";
import { TASK1_TYPE_META } from "../lib/task1QuestionTypes";
import type { Task1QuestionType } from "../types";

function InlineMarkdown({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) =>
    part.startsWith("**") && part.endsWith("**")
      ? <strong key={index}>{part.slice(2, -2)}</strong>
      : <span key={index}>{part}</span>,
  );
}

function GuideBlockView({ block }: { block: GuideBlock }) {
  if (block.kind === "heading") {
    return block.level === 2
      ? <h2 className="text-xl font-bold text-gray-950"><InlineMarkdown text={block.text} /></h2>
      : <h3 className="pt-3 text-sm font-bold uppercase tracking-[0.12em] text-violet-800"><InlineMarkdown text={block.text} /></h3>;
  }
  if (block.kind === "list") {
    return (
      <ul className="list-disc space-y-1 pl-5 text-sm leading-6 text-gray-700">
        {block.items.map((item) => <li key={item}><InlineMarkdown text={item} /></li>)}
      </ul>
    );
  }
  if (block.kind === "quote") {
    return <blockquote className="rounded-lg border-l-4 border-violet-300 bg-violet-50 px-4 py-3 text-sm leading-6 text-violet-950"><InlineMarkdown text={block.text} /></blockquote>;
  }
  return <p className="text-sm leading-6 text-gray-700"><InlineMarkdown text={block.text} /></p>;
}

export function Task1GuideModal({
  type,
  open,
  onClose,
}: {
  type: Task1QuestionType;
  open: boolean;
  onClose: () => void;
}) {
  const dialogRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const blocks = useMemo(
    () => parseGuideBlocks(extractTask1Guide(guideMarkdown, type)),
    [type],
  );

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCloseRef.current();
      if (event.key === "Tab") {
        const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
        );
        if (!focusable?.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (focusable.length === 1 || (event.shiftKey && document.activeElement === first)) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
      previousFocusRef.current?.focus();
    };
  }, [open]);

  if (!open) return null;
  const visibleBlocks = blocks[0]?.kind === "heading" && blocks[0].level === 2
    ? blocks.slice(1)
    : blocks;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-gray-950/50 p-0 sm:items-center sm:p-6"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="task1-guide-title"
        className="flex max-h-[92vh] w-full max-w-2xl flex-col rounded-t-2xl bg-white shadow-2xl sm:rounded-2xl"
      >
        <header className="flex items-start justify-between gap-4 border-b border-gray-200 px-5 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-violet-700">Task 1 guide</p>
            <h2 id="task1-guide-title" className="mt-1 text-xl font-bold text-gray-950">{TASK1_TYPE_META[type].guideHeading}</h2>
          </div>
          <button ref={closeButtonRef} type="button" onClick={onClose} className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-semibold text-gray-700 hover:bg-gray-50" aria-label="Close Task 1 guide">Close</button>
        </header>
        <div className="overflow-y-auto px-5 py-5">
          <div className="mb-5 rounded-lg bg-blue-50 px-4 py-3 text-sm leading-6 text-blue-950">
            Introduction → Overview → Detail paragraph 1 → Detail paragraph 2. No separate conclusion.
          </div>
          <div className="space-y-3">
            {visibleBlocks.map((block, index) => <GuideBlockView key={`${block.kind}-${index}`} block={block} />)}
          </div>
        </div>
      </section>
    </div>,
    document.body,
  );
}
