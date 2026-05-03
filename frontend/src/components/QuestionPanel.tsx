import type { QuestionGroup, SimpleQuestion } from "../types";

interface Props {
  groups: QuestionGroup[];
  answers: Record<number, string>;
  onAnswer: (questionId: number, answer: string) => void;
}

export function QuestionPanel({ groups, answers, onAnswer }: Props) {
  return (
    <div className="h-full overflow-y-auto px-6 py-4 space-y-8">
      {groups.map((group) => (
        <GroupRenderer
          key={group.id}
          group={group}
          answers={answers}
          onAnswer={onAnswer}
        />
      ))}
    </div>
  );
}

function getVisibleSharedText(sharedText?: string) {
  const normalized = sharedText?.trim();
  if (!normalized) {
    return null;
  }

  if (normalized.toLowerCase().startsWith("show answers")) {
    return null;
  }

  return normalized;
}

function GroupRenderer({
  group,
  answers,
  onAnswer,
}: {
  group: QuestionGroup;
  answers: Record<number, string>;
  onAnswer: (questionId: number, answer: string) => void;
}) {
  const visibleSharedText = getVisibleSharedText(group.shared_text);

  return (
    <div className="space-y-4">
      {/* Instruction — shown once per group */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <p className="text-xs text-gray-600 whitespace-pre-line leading-5">{group.instruction}</p>
      </div>

      {/* Shared passage (summary / note completion) */}
      {visibleSharedText && (
        <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded-lg border border-gray-200 leading-7 whitespace-pre-line">
          {visibleSharedText}
        </p>
      )}

      {/* Diagram image */}
      {group.image_url && (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <img
            src={group.image_url}
            alt="Diagram"
            className="max-w-full h-auto"
          />
        </div>
      )}

      {/* Word list for summary completion */}
      {group.word_list && group.word_list.length > 0 && (
        <div className="text-xs text-gray-600 bg-gray-50 p-3 rounded border border-gray-200">
          <span className="font-medium">Word bank: </span>
          {group.word_list.map((w, i) => (
            <span key={w}>
              <span className="font-medium">{String.fromCharCode(65 + i)}.</span> {w}
              {i < group.word_list!.length - 1 ? " · " : ""}
            </span>
          ))}
        </div>
      )}

      {/* Individual questions */}
      <div className="space-y-5">
        {group.questions.map((q) => (
          <div key={q.id} className="flex items-start gap-3">
            <span className="shrink-0 w-8 h-8 flex items-center justify-center rounded-full bg-blue-600 text-white text-sm font-bold">
              {q.id}
            </span>
            <div className="flex-1 pt-0.5">
              <QuestionInput
                group={group}
                question={q}
                value={answers[q.id] ?? ""}
                onChange={(v) => onAnswer(q.id, v)}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function QuestionInput({
  group,
  question,
  value,
  onChange,
}: {
  group: QuestionGroup;
  question: SimpleQuestion;
  value: string;
  onChange: (v: string) => void;
}) {
  const selectClass =
    "border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white";
  const inputClass =
    "border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";

  switch (group.type) {
    case "true-false-ng": {
      const isYesNo = question.answer === "YES" || question.answer === "NO";
      const opts = isYesNo ? ["YES", "NO", "NOT GIVEN"] : ["TRUE", "FALSE", "NOT GIVEN"];
      return (
        <div className="space-y-2">
          {question.statement && (
            <p className="text-sm font-medium text-gray-900">{question.statement}</p>
          )}
          <div className="space-y-1.5">
            {opts.map((opt) => (
              <label key={opt} className="flex items-center gap-3 cursor-pointer group">
                <input
                  type="radio"
                  name={`q-${question.id}`}
                  value={opt}
                  checked={value === opt}
                  onChange={() => onChange(opt)}
                  className="h-4 w-4 text-blue-600"
                />
                <span className="text-sm text-gray-700 group-hover:text-gray-900">{opt}</span>
              </label>
            ))}
          </div>
        </div>
      );
    }

    case "multiple-choice": {
      const opts = group.options ?? {};
      return (
        <div className="space-y-2">
          {question.statement && (
            <p className="text-sm font-medium text-gray-900">{question.statement}</p>
          )}
          <div className="space-y-1.5">
            {Object.entries(opts).map(([key, text]) => (
              <label key={key} className="flex items-start gap-3 cursor-pointer group">
                <input
                  type="radio"
                  name={`q-${question.id}`}
                  value={key}
                  checked={value === key}
                  onChange={() => onChange(key)}
                  className="h-4 w-4 text-blue-600 mt-0.5"
                />
                <span className="text-sm text-gray-700 group-hover:text-gray-900">
                  <span className="font-medium">{key}.</span> {text}
                </span>
              </label>
            ))}
          </div>
        </div>
      );
    }

    case "matching-information": {
      const opts = group.options ?? {};
      return (
        <div className="space-y-2">
          {question.statement && (
            <p className="text-sm font-medium text-gray-900">{question.statement}</p>
          )}
          <select
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className={selectClass}
          >
            <option value="">Select paragraph...</option>
            {Object.keys(opts).map((para) => (
              <option key={para} value={para}>
                Paragraph {para}
              </option>
            ))}
          </select>
        </div>
      );
    }

    case "matching-headings": {
      const opts = group.options ?? {};
      return (
        <div className="space-y-2">
          {question.statement && (
            <p className="text-sm font-medium text-gray-900">{question.statement}</p>
          )}
          <select
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className={`w-full ${selectClass}`}
          >
            <option value="">Select heading...</option>
            {Object.entries(opts).map(([key, text]) => (
              <option key={key} value={key}>
                {key !== text ? `${key}. ${text}` : key}
              </option>
            ))}
          </select>
        </div>
      );
    }

    case "summary-completion": {
      return (
        <div className="space-y-2">
          {group.word_list ? (
            <select
              value={value}
              onChange={(e) => onChange(e.target.value)}
              className={selectClass}
            >
              <option value="">Select word...</option>
              {group.word_list.map((w, i) => {
                const letter = String.fromCharCode(65 + i);
                return (
                  <option key={letter} value={letter}>
                    {letter}. {w}
                  </option>
                );
              })}
            </select>
          ) : (
            <input
              type="text"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              placeholder="Answer..."
              className={`${inputClass} w-64`}
            />
          )}
        </div>
      );
    }

    case "sentence-completion": {
      const raw = question.statement || "";
      const parts = raw.split("___");
      if (parts.length < 2) {
        return (
          <div className="space-y-2">
            {raw && <p className="text-sm text-gray-900">{raw}</p>}
            <input
              type="text"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              placeholder="Answer..."
              className={`${inputClass} w-64`}
            />
          </div>
        );
      }
      return (
        <div className="text-sm text-gray-900 leading-7 flex flex-wrap items-baseline gap-0.5">
          {parts.map((part, i) => (
            <span key={i}>
              {part}
              {i < parts.length - 1 && (
                <input
                  type="text"
                  value={value}
                  onChange={(e) => onChange(e.target.value)}
                  placeholder="..."
                  className="inline-block mx-1 border-b-2 border-blue-500 focus:outline-none text-blue-800 w-32 text-sm bg-transparent"
                />
              )}
            </span>
          ))}
        </div>
      );
    }

    case "diagram-labeling": {
      return (
        <div className="space-y-2">
          {question.statement && (
            <p className="text-sm text-gray-600">{question.statement}</p>
          )}
          <input
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Max 2 words from passage"
            className={`${inputClass} w-64`}
          />
        </div>
      );
    }

    default:
      return (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Answer..."
          className={`${inputClass} w-64`}
        />
      );
  }
}
