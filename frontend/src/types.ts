export type QuestionType =
  | "true-false-ng"
  | "multiple-choice"
  | "matching-headings"
  | "matching-information"
  | "sentence-completion"
  | "summary-completion"
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
}

export interface TestSession {
  id: string;
  test_id: string;
  started_at: string;
  completed_at: string;
  total_time_ms: number;
  answers: UserAnswer[];
  score: { correct: number; total: number; band_estimate: number };
  passcode: string;
}
