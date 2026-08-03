import type {
  ListeningLayoutBlock,
  ListeningListItem,
  ListeningSegment,
  QuestionGroup,
  SimpleQuestion,
} from "../types";
import { getListeningSelectionUpdate } from "../lib/listeningSelections";
import { QuestionPanel } from "./QuestionPanel";

interface Props {
  groups: QuestionGroup[];
  answers: Record<number, string>;
  onAnswer: (questionId: number, answer: string) => void;
  readOnly?: boolean;
}

interface GroupProps {
  group: QuestionGroup;
  answers: Record<number, string>;
  onAnswer: (questionId: number, answer: string) => void;
  readOnly: boolean;
}

const inputClass =
  "mx-1 inline-block w-32 rounded-md border border-gray-300 bg-white px-2 py-1 text-sm text-blue-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200 disabled:bg-gray-100";

export function ListeningQuestionPanel({ groups, answers, onAnswer, readOnly = false }: Props) {
  return (
    <div className="space-y-8 px-4 py-5 md:px-6">
      {groups.map((group) => (
        <ListeningGroup
          key={group.id}
          group={group}
          answers={answers}
          onAnswer={onAnswer}
          readOnly={readOnly}
        />
      ))}
    </div>
  );
}

function ListeningGroup(props: GroupProps) {
  const { group } = props;
  if (group.type === "note-completion" && group.layout?.length) {
    return <CompletionGroup {...props} />;
  }
  if (group.type === "multiple-choice") {
    return <MultipleChoiceGroup {...props} />;
  }
  if (group.type === "matching") {
    return <MatchingGroup {...props} />;
  }
  return (
    <QuestionPanel
      groups={[group]}
      answers={props.answers}
      onAnswer={props.onAnswer}
      readOnly={props.readOnly}
    />
  );
}

function Instruction({ text }: { text: string }) {
  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
      <p className="text-sm leading-6 text-gray-700">{text}</p>
    </div>
  );
}

function QuestionBadge({ questionId }: { questionId: number }) {
  return (
    <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-blue-600 px-1.5 text-xs font-bold text-white">
      {questionId}
    </span>
  );
}

function SegmentLine({
  segments,
  answers,
  onAnswer,
  readOnly,
}: {
  segments: ListeningSegment[];
  answers: Record<number, string>;
  onAnswer: Props["onAnswer"];
  readOnly: boolean;
}) {
  return (
    <span className="text-sm leading-9 text-gray-900">
      {segments.map((segment, index) => {
        if (segment.type === "text") {
          return <span key={`text-${index}`}>{segment.text}</span>;
        }
        const questionId = segment.question_id;
        return (
          <label
            key={`blank-${questionId}-${index}`}
            id={`question-${questionId}`}
            className="inline-flex scroll-mt-28 items-center whitespace-nowrap align-baseline"
          >
            <QuestionBadge questionId={questionId} />
            <input
              type="text"
              value={answers[questionId] ?? ""}
              onChange={(event) => onAnswer(questionId, event.target.value)}
              disabled={readOnly}
              placeholder="Answer"
              aria-label={`Question ${questionId}`}
              className={inputClass}
            />
          </label>
        );
      })}
    </span>
  );
}

function CompletionGroup({ group, answers, onAnswer, readOnly }: GroupProps) {
  return (
    <section className="space-y-4">
      <Instruction text={group.instruction} />
      <div className="space-y-3 rounded-lg border border-gray-200 bg-white p-4 md:p-5">
        {group.layout!.map((block, index) => (
          <LayoutBlock
            key={`${block.type}-${index}`}
            block={block}
            answers={answers}
            onAnswer={onAnswer}
            readOnly={readOnly}
          />
        ))}
      </div>
    </section>
  );
}

function LayoutBlock({
  block,
  answers,
  onAnswer,
  readOnly,
}: {
  block: ListeningLayoutBlock;
  answers: Record<number, string>;
  onAnswer: Props["onAnswer"];
  readOnly: boolean;
}) {
  const segmentProps = { answers, onAnswer, readOnly };
  if (block.type === "heading") {
    return (
      <h3 className="pt-2 text-base font-semibold text-gray-950 first:pt-0">
        <SegmentLine segments={block.segments} {...segmentProps} />
      </h3>
    );
  }
  if (block.type === "list") {
    return <ListeningList items={block.items} {...segmentProps} />;
  }
  if (block.type === "table") {
    return (
      <div className="overflow-x-auto rounded-lg border border-gray-300">
        <table className="min-w-full border-collapse text-left">
          <tbody>
            {block.rows.map((row, rowIndex) => (
              <tr key={rowIndex} className={rowIndex === 0 ? "bg-gray-50" : "bg-white"}>
                {row.cells.map((cell, cellIndex) => (
                  <td key={cellIndex} className="min-w-40 border-b border-r border-gray-300 p-3 align-top last:border-r-0">
                    <SegmentLine segments={cell.segments} {...segmentProps} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  return (
    <p>
      <SegmentLine segments={block.segments} {...segmentProps} />
    </p>
  );
}

function ListeningList({
  items,
  answers,
  onAnswer,
  readOnly,
  nested = false,
}: {
  items: ListeningListItem[];
  answers: Record<number, string>;
  onAnswer: Props["onAnswer"];
  readOnly: boolean;
  nested?: boolean;
}) {
  return (
    <ul className={`${nested ? "mt-1 list-[circle] pl-6" : "list-disc pl-6"} space-y-1.5`}>
      {items.map((item, index) => (
        <li key={index} className="pl-1 marker:text-gray-600">
          <SegmentLine segments={item.segments} answers={answers} onAnswer={onAnswer} readOnly={readOnly} />
          {item.children.length > 0 && (
            <ListeningList
              items={item.children}
              answers={answers}
              onAnswer={onAnswer}
              readOnly={readOnly}
              nested
            />
          )}
        </li>
      ))}
    </ul>
  );
}

function MultipleChoiceGroup(props: GroupProps) {
  const { group } = props;
  if (group.selection_limit && group.options) {
    return <SharedMultipleChoiceGroup {...props} />;
  }
  return (
    <section className="space-y-4">
      <Instruction text={group.instruction} />
      {group.shared_text && <p className="text-sm leading-7 text-gray-800">{group.shared_text}</p>}
      <div className="space-y-6">
        {group.questions.map((question) => (
          <SingleMultipleChoice key={question.id} question={question} {...props} />
        ))}
      </div>
    </section>
  );
}

function SharedMultipleChoiceGroup({ group, answers, onAnswer, readOnly }: GroupProps) {
  const limit = group.selection_limit!;
  const questionIds = group.questions.map((question) => question.id);
  const selected = questionIds
    .map((questionId) => answers[questionId])
    .filter((answer): answer is string => Boolean(answer));
  const selectedSet = new Set(selected);
  const stem = group.shared_text || group.questions[0]?.statement;

  const toggle = (option: string) => {
    const update = getListeningSelectionUpdate(questionIds, answers, option, limit);
    if (update) onAnswer(update.questionId, update.answer);
  };

  return (
    <section className="space-y-4">
      <Instruction text={group.instruction} />
      <div className="rounded-lg border border-gray-200 p-4">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          {questionIds.map((questionId) => (
            <span key={questionId} id={`question-${questionId}`} className="scroll-mt-28">
              <QuestionBadge questionId={questionId} />
            </span>
          ))}
          <span className="text-xs font-medium text-gray-500">Select {limit} options ({selected.length}/{limit})</span>
        </div>
        {stem && <p className="mb-3 text-sm font-medium leading-6 text-gray-900">{stem}</p>}
        <div className="space-y-2">
          {Object.entries(group.options!).map(([key, text]) => {
            const checked = selectedSet.has(key);
            const disabled = readOnly || (!checked && selected.length >= limit);
            return (
              <label key={key} className="flex cursor-pointer items-start gap-3 rounded-md px-2 py-1.5 hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggle(key)}
                  disabled={disabled}
                  className="mt-0.5 h-4 w-4 rounded text-blue-600"
                />
                <span className="text-sm text-gray-800"><strong>{key}.</strong> {text}</span>
              </label>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function SingleMultipleChoice({ question, group, answers, onAnswer, readOnly }: GroupProps & { question: SimpleQuestion }) {
  const options = question.options ?? group.options ?? {};
  return (
    <div id={`question-${question.id}`} className="scroll-mt-28 rounded-lg border border-gray-200 p-4">
      <div className="mb-3 flex items-start gap-3">
        <QuestionBadge questionId={question.id} />
        <p className="text-sm font-medium leading-6 text-gray-900">{question.statement}</p>
      </div>
      <div className="space-y-2 pl-0 md:pl-9">
        {Object.entries(options).map(([key, text]) => (
          <label key={key} className="flex cursor-pointer items-start gap-3">
            <input
              type="radio"
              name={`question-${question.id}`}
              checked={answers[question.id] === key}
              onChange={() => onAnswer(question.id, key)}
              disabled={readOnly}
              className="mt-0.5 h-4 w-4 text-blue-600"
            />
            <span className="text-sm text-gray-800"><strong>{key}.</strong> {text}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

function MatchingGroup({ group, answers, onAnswer, readOnly }: GroupProps) {
  const options = group.options ?? {};
  return (
    <section className="space-y-4">
      <Instruction text={group.instruction} />
      <div className="rounded-lg border border-gray-300 bg-gray-50 p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Options</p>
        <div className="grid gap-x-6 gap-y-1.5 md:grid-cols-2">
          {Object.entries(options).map(([key, text]) => (
            <p key={key} className="text-sm leading-6 text-gray-800"><strong>{key}.</strong> {text}</p>
          ))}
        </div>
      </div>
      <div className="divide-y divide-gray-200 rounded-lg border border-gray-200">
        {group.questions.map((question) => (
          <div key={question.id} id={`question-${question.id}`} className="flex scroll-mt-28 flex-col gap-3 p-3 sm:flex-row sm:items-center">
            <div className="flex min-w-0 flex-1 items-start gap-3">
              <QuestionBadge questionId={question.id} />
              <p className="text-sm leading-6 text-gray-900">{question.statement}</p>
            </div>
            <select
              value={answers[question.id] ?? ""}
              onChange={(event) => onAnswer(question.id, event.target.value)}
              disabled={readOnly}
              aria-label={`Question ${question.id}`}
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select letter</option>
              {Object.keys(options).map((key) => <option key={key} value={key}>{key}</option>)}
            </select>
          </div>
        ))}
      </div>
    </section>
  );
}
