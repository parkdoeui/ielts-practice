export type QuestionType =
  | "true-false-ng"
  | "multiple-choice"
  | "matching-headings"
  | "matching-information"
  | "matching-features"
  | "matching-sentence-endings"
  | "classification"
  | "sentence-completion"
  | "summary-completion"
  | "table-completion"
  | "diagram-labeling"
  | "note-completion"
  | "matching";

export interface Passage {
  id: string;
  title: string;
  text: string;
  paragraphs: string[];
}

export interface SimpleQuestion {
  id: number;
  statement: string;
  answer: string;
  accepted_answers?: string[];
  options?: Record<string, string>;  // per-question MC choices when not shared by the group
}

export interface ListeningTextSegment {
  type: "text";
  text: string;
}

export interface ListeningBlankSegment {
  type: "blank";
  question_id: number;
}

export type ListeningSegment = ListeningTextSegment | ListeningBlankSegment;

export interface ListeningListItem {
  segments: ListeningSegment[];
  children: ListeningListItem[];
}

export interface ListeningTableCell {
  segments: ListeningSegment[];
}

export interface ListeningTableRow {
  cells: ListeningTableCell[];
}

export interface ListeningLayoutBlock {
  type: "heading" | "paragraph" | "list" | "table";
  segments: ListeningSegment[];
  items: ListeningListItem[];
  rows: ListeningTableRow[];
}

export interface QuestionGroup {
  id: string;
  type: QuestionType;
  passage_id: string;
  instruction: string;
  questions: SimpleQuestion[];
  shared_text?: string;       // summary/note passage shown once for the group
  word_list?: string[];       // word bank for summary completion
  image_url?: string;         // diagram image URL
  options?: Record<string, string>;  // shared options (MC choices, paragraph letters, headings)
  layout?: ListeningLayoutBlock[];   // Listening-only ordered source presentation
  selection_limit?: number;          // Shared option count, e.g. Choose TWO
}

export interface ReadingTest {
  id: string;
  title: string;
  test_type: "academic" | "general";
  passages: Passage[];
  question_groups: QuestionGroup[];
  time_limit_minutes: number;
  source_url: string;
}

export interface ListeningPart {
  id: string;
  number: number;
  title?: string | null;
}

export interface ListeningTest {
  id: string;
  title: string;
  audio_url: string;
  parts: ListeningPart[];
  question_groups: QuestionGroup[];
  time_limit_minutes: number;
  source_url: string;
}

export interface UserAnswer {
  question_id: number;
  user_answer: string;
  is_correct: boolean;
  time_spent_ms: number;
  question_type?: QuestionType;
  self_corrected?: boolean;
}

export interface TestSession {
  id: string;
  test_id: string;
  started_at: string;
  completed_at: string;
  total_time_ms: number;
  answers: UserAnswer[];
  score: { correct: number; total: number; band_estimate: number };
  sync_status?: "synced" | "local-only";
  sync_error?: string;
}

export interface WritingTask {
  task_number: 1 | 2;
  task_type: "academic-task-1" | "essay";
  prompt: string;
  instructions: string[];
  min_words: number;
  image_url?: string;
  table?: string[][];
}

export interface WritingTest {
  id: string;
  title: string;
  test_type: "academic" | "general";
  tasks: WritingTask[];
  time_limit_minutes: number;
  source_url: string;
}

export interface WritingCriteria {
  task_response: number;
  coherence_cohesion: number;
  lexical_resource: number;
  grammar_accuracy: number;
}

export interface WritingCriterionEvidence {
  task_response: string;
  coherence_cohesion: string;
  lexical_resource: string;
  grammar_accuracy: string;
}

export interface WritingDetailedImprovementPoints {
  task_response: string[];
  coherence_cohesion: string[];
  lexical_resource: string[];
  grammar_accuracy: string[];
}

export interface WritingTaskFeedback {
  band: number;
  criteria: WritingCriteria;
  criterion_evidence: WritingCriterionEvidence;
  detailed_improvement_points: WritingDetailedImprovementPoints;
  current_state: string;
  primary_goal: string;
  sample_answer: string;
}

export interface WritingGradingResult {
  overall_band: number;
  task_1: WritingTaskFeedback;
  task_2: WritingTaskFeedback;
  action_points: string[];
}

export interface WritingSubmittedTask {
  prompt: string;
  answer: string;
}

export interface WritingAnswersJson {
  task1: WritingSubmittedTask;
  task2: WritingSubmittedTask;
}

export interface WritingSession {
  id: string;
  test_id: string;
  started_at: string;
  completed_at: string;
  total_time_ms: number;
  answers: Record<string, string>;
  answers_json?: WritingAnswersJson;
  grading: WritingGradingResult;
  sync_status?: "synced" | "local-only";
  sync_error?: string;
}

// ---- Full Test (Mock Exam) simulation ----

export type MockMode = "relaxed" | "strict";
export type SkillName = "listening" | "reading" | "writing" | "speaking";

export interface MockSection {
  skill: SkillName;
  test_id: string | null;    // null ⇒ not-yet-available (speaking this iteration)
  session_id: string | null; // set on completion; also the "done" signal
  band: number | null;       // child session's band, captured at completion
}

export interface MockSession {
  id: string;
  full_test_id?: string;
  mode: MockMode;
  started_at: string;
  completed_at?: string | null;
  overall_band?: number | null;
  sections: MockSection[];   // ordered: listening, reading, writing, speaking
}

export interface FullTestSet {
  id: string;
  title: string;
  listening_test_id: string;
  reading_test_id: string;
  writing_test_id: string;
  speaking_test_id: string | null;
}

// Skills that have a real, playable section today.
export const IMPLEMENTED_SKILLS = new Set<SkillName>(["listening", "reading", "writing"]);

export function isMockSectionDone(section: MockSection): boolean {
  return section.session_id !== null;
}

export function isMockSectionComingSoon(section: MockSection): boolean {
  return !IMPLEMENTED_SKILLS.has(section.skill);
}
