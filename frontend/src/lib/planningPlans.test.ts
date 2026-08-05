import { describe, expect, it } from "vitest";
import { simplifyTask1Plan } from "./planningPlans";

describe("Task 1 plan simplification", () => {
  it("converts legacy nested outlines into four notes", () => {
    const result = simplifyTask1Plan({
      kind: "task_1",
      introduction: { visual_subject: "Two maps of a hospital." },
      overview: { big_picture_1: "Access changed.", big_picture_2: "The hospital stayed." },
      detail_paragraphs: [
        {
          grouping_focus: "Transport",
          key_feature_1: "Roundabouts added",
          supporting_data_1: "Both ends of Hospital Road",
          key_feature_2: "Bus station added",
          supporting_data_2: "West side",
          comparison_or_relationship: "Replaced bus stops",
        },
      ],
    });

    expect(result).toEqual({
      kind: "task_1",
      introduction: "Two maps of a hospital.",
      overview: "Access changed. · The hospital stayed.",
      detail_1: "Transport · Roundabouts added · Both ends of Hospital Road · Bus station added · West side · Replaced bus stops",
      detail_2: "",
    });
  });

  it("preserves an existing four-note plan", () => {
    const plan = { kind: "task_1" as const, introduction: "Intro", overview: "Overview", detail_1: "One", detail_2: "Two" };
    expect(simplifyTask1Plan(plan)).toEqual(plan);
  });
});
