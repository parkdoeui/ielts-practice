import type { FullTestSet } from "../types";

const fullTestFiles = import.meta.glob<{ default: FullTestSet }>(
  "../data/full-tests/*.json",
  { eager: true },
);

export function isFullTestSet(value: unknown): value is FullTestSet {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<FullTestSet>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.title === "string" &&
    typeof candidate.listening_test_id === "string" &&
    typeof candidate.reading_test_id === "string" &&
    typeof candidate.writing_test_id === "string" &&
    (typeof candidate.speaking_test_id === "string" || candidate.speaking_test_id === null)
  );
}

export const FULL_TESTS = Object.values(fullTestFiles)
  .map((module) => module.default)
  .filter(isFullTestSet)
  .sort((a, b) => a.title.localeCompare(b.title));
