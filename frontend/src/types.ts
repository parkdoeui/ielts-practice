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
  | "diagram-labeling";

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

export interface WritingSession {
  id: string;
  test_id: string;
  started_at: string;
  completed_at: string;
  total_time_ms: number;
  answers: Record<string, string>;
  grading: WritingGradingResult;
  sync_status?: "synced" | "local-only";
  sync_error?: string;
}
