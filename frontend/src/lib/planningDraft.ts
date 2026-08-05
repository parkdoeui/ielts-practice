import type { WritingPlan } from "../types";

export interface PlanningDraft {
  testId: string;
  taskNumber: 1 | 2;
  parentSessionId?: string | null;
  startedAt: string;
  plan: WritingPlan;
}

function draftKey(testId: string, taskNumber: 1 | 2, parentSessionId?: string | null): string {
  return `ielts_planning_draft_${testId}_${taskNumber}_${parentSessionId ?? "new"}`;
}

export function savePlanningDraft(draft: PlanningDraft): void {
  localStorage.setItem(draftKey(draft.testId, draft.taskNumber, draft.parentSessionId), JSON.stringify(draft));
}

export function getPlanningDraft(
  testId: string,
  taskNumber: 1 | 2,
  parentSessionId?: string | null,
): PlanningDraft | null {
  const raw = localStorage.getItem(draftKey(testId, taskNumber, parentSessionId));
  if (!raw) return null;
  try {
    const value = JSON.parse(raw) as PlanningDraft;
    if (value.testId !== testId || value.taskNumber !== taskNumber || !value.plan || !value.startedAt) return null;
    return value;
  } catch {
    return null;
  }
}

export function clearPlanningDraft(
  testId: string,
  taskNumber: 1 | 2,
  parentSessionId?: string | null,
): void {
  localStorage.removeItem(draftKey(testId, taskNumber, parentSessionId));
}
