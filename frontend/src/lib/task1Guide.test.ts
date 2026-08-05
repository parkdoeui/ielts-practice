import { describe, expect, it } from "vitest";
import guideMarkdown from "../content/task-1-planning-guide.md?raw";
import { extractTask1Guide, parseGuideBlocks } from "./task1Guide";
import { TASK1_TYPE_META, TASK1_TYPE_ORDER } from "./task1QuestionTypes";

describe("Task 1 contextual guide", () => {
  it("extracts only the matching type plus its fast grouping rule", () => {
    for (const type of TASK1_TYPE_ORDER) {
      const section = extractTask1Guide(guideMarkdown, type);
      expect(section).toContain(`## ${TASK1_TYPE_META[type].guideHeading}`);
      expect(section).toContain("### Fast grouping rule");
      for (const otherType of TASK1_TYPE_ORDER.filter((candidate) => candidate !== type)) {
        expect(section).not.toContain(`## ${TASK1_TYPE_META[otherType].guideHeading}`);
      }
    }
  });

  it("parses headings, lists, paragraphs, and template quotes without HTML", () => {
    const blocks = parseGuideBlocks(extractTask1Guide(guideMarkdown, "line-graph"));
    expect(blocks.some((block) => block.kind === "heading" && block.text === "Line Graphs")).toBe(true);
    expect(blocks.some((block) => block.kind === "list" && block.items.includes("Crossovers"))).toBe(true);
    expect(blocks.some((block) => block.kind === "quote" && block.text.startsWith("The line graph compares"))).toBe(true);
    expect(blocks.some((block) => block.kind === "paragraph")).toBe(true);
  });
});
