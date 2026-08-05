import type { LegacyTask1Plan, Task1Plan, Task2Plan, WritingPlan } from "../types";

export const EMPTY_TASK1_PLAN: Task1Plan = {
  kind: "task_1",
  introduction: "",
  overview: "",
  detail_1: "",
  detail_2: "",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object";
}

export function isLegacyTask1Plan(plan: unknown): plan is LegacyTask1Plan {
  if (!isRecord(plan) || plan.kind !== "task_1") return false;
  return isRecord(plan.introduction)
    && isRecord(plan.overview)
    && Array.isArray(plan.detail_paragraphs);
}

export function isSimpleTask1Plan(plan: unknown): plan is Task1Plan {
  if (!isRecord(plan) || plan.kind !== "task_1") return false;
  return [plan.introduction, plan.overview, plan.detail_1, plan.detail_2]
    .every((value) => typeof value === "string");
}

function joinNotes(values: unknown[]): string {
  return values
    .filter((value): value is string => typeof value === "string" && Boolean(value.trim()))
    .map((value) => value.trim())
    .join(" · ");
}

function legacyDetail(plan: LegacyTask1Plan, index: number): string {
  const detail = plan.detail_paragraphs[index];
  if (!detail) return "";
  return joinNotes([
    detail.grouping_focus,
    detail.key_feature_1,
    detail.supporting_data_1,
    detail.key_feature_2,
    detail.supporting_data_2,
    detail.comparison_or_relationship,
  ]);
}

export function simplifyTask1Plan(plan: unknown): Task1Plan {
  if (isSimpleTask1Plan(plan)) return { ...plan };
  if (!isLegacyTask1Plan(plan)) return { ...EMPTY_TASK1_PLAN };
  return {
    kind: "task_1",
    introduction: plan.introduction.visual_subject.trim(),
    overview: joinNotes([plan.overview.big_picture_1, plan.overview.big_picture_2]),
    detail_1: legacyDetail(plan, 0),
    detail_2: legacyDetail(plan, 1),
  };
}

export function normalizePlanningPlanForEdit(plan: WritingPlan, taskNumber: 1 | 2): Task1Plan | Task2Plan {
  if (taskNumber === 1) return simplifyTask1Plan(plan);
  return plan as Task2Plan;
}
