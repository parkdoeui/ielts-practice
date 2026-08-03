export interface NavigatorPart {
  label: string;         // e.g. "Part 1"
  questionIds: number[];
}

interface Props {
  parts: NavigatorPart[];
  answered: Set<number>;
  flagged: Set<number>;
  current: number | null;
  onJump: (questionId: number) => void;
  onToggleFlag: (questionId: number) => void;
  onPrev: () => void;
  onNext: () => void;
}

/**
 * Bottom chrome for the mock (CBT) experience — the signature computer-delivered IELTS
 * navigator: part tabs + a row of numbered boxes for the active part, each showing
 * answered / current / flagged state, a review-flag toggle for the current question, and
 * prev/next arrows. Reading/Listening only (writing has no discrete questions).
 */
export function QuestionNavigator({
  parts,
  answered,
  flagged,
  current,
  onJump,
  onToggleFlag,
  onPrev,
  onNext,
}: Props) {
  const activePartIndex = Math.max(
    0,
    parts.findIndex((part) => current != null && part.questionIds.includes(current)),
  );
  const activePart = parts[activePartIndex] ?? parts[0];

  return (
    <div className="flex items-center gap-3 border-t border-gray-200 bg-white px-3 md:px-4 py-2 shrink-0 overflow-x-auto">
      <button
        type="button"
        onClick={onPrev}
        className="h-8 shrink-0 rounded-lg border border-gray-300 px-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        aria-label="Previous question"
      >
        ◀
      </button>

      <div className="flex shrink-0 gap-1">
        {parts.map((part, index) => (
          <button
            key={part.label}
            type="button"
            onClick={() => onJump(part.questionIds[0])}
            className={`h-8 rounded-lg px-2.5 text-xs font-semibold transition-colors ${
              index === activePartIndex
                ? "bg-gray-900 text-white"
                : "border border-gray-300 text-gray-600 hover:bg-gray-50"
            }`}
          >
            {part.label}
          </button>
        ))}
      </div>

      <div className="flex flex-1 items-center gap-1">
        {activePart?.questionIds.map((qid) => {
          const isCurrent = qid === current;
          const isAnswered = answered.has(qid);
          const isFlagged = flagged.has(qid);
          return (
            <button
              key={qid}
              type="button"
              onClick={() => onJump(qid)}
              className={`relative h-8 w-8 shrink-0 border text-xs font-semibold tabular-nums transition-all ${
                isFlagged ? "rounded-full" : "rounded-md"
              } ${
                isCurrent
                  ? "border-blue-600 ring-2 ring-blue-500 text-blue-700"
                  : isAnswered
                    ? "border-blue-600 bg-blue-600 text-white"
                    : "border-gray-300 text-gray-600 hover:bg-gray-50"
              }`}
              aria-label={`Question ${qid}${isAnswered ? ", answered" : ""}${isFlagged ? ", flagged for review" : ""}`}
            >
              {qid}
            </button>
          );
        })}
      </div>

      {current != null && (
        <button
          type="button"
          onClick={() => onToggleFlag(current)}
          className={`h-8 shrink-0 rounded-lg px-2.5 text-xs font-medium transition-colors ${
            flagged.has(current)
              ? "bg-amber-100 text-amber-800 border border-amber-300"
              : "border border-gray-300 text-gray-700 hover:bg-gray-50"
          }`}
          aria-pressed={flagged.has(current)}
        >
          ⚑ Review
        </button>
      )}

      <button
        type="button"
        onClick={onNext}
        className="h-8 shrink-0 rounded-lg border border-gray-300 px-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        aria-label="Next question"
      >
        ▶
      </button>
    </div>
  );
}
