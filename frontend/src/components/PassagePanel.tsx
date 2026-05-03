import type { Passage } from "../types";

interface Props {
  passages: Passage[];
  currentPassageIndex: number;
  onPassageChange: (index: number) => void;
}

export function PassagePanel({ passages, currentPassageIndex, onPassageChange }: Props) {
  const passage = passages[currentPassageIndex];

  return (
    <div className="flex flex-col h-full">
      {/* Passage tabs */}
      {passages.length > 1 && (
        <div className="flex gap-1 px-4 pt-3 pb-2 border-b border-gray-200 bg-gray-50">
          {passages.map((p, i) => (
            <button
              key={p.id}
              onClick={() => onPassageChange(i)}
              className={`px-3 py-1 text-sm rounded-md font-medium transition-colors ${
                i === currentPassageIndex
                  ? "bg-white border border-gray-300 text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              P{i + 1}
            </button>
          ))}
        </div>
      )}

      {/* Passage title */}
      <div className="px-6 py-4 border-b border-gray-100">
        <h2 className="text-lg font-bold text-gray-900">{passage.title}</h2>
      </div>

      {/* Passage text */}
      <div className="flex-1 overflow-y-auto px-6 py-4 text-sm leading-7 text-gray-800 space-y-4">
        {passage.paragraphs.length > 0 ? (
          passage.paragraphs.map((para, i) => (
            <p key={i} className="whitespace-pre-wrap">
              {para}
            </p>
          ))
        ) : (
          <p className="whitespace-pre-wrap">{passage.text}</p>
        )}
      </div>
    </div>
  );
}
