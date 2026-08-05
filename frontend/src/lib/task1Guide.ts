import type { Task1QuestionType } from "../types";
import { TASK1_TYPE_META } from "./task1QuestionTypes";

export type GuideBlock =
  | { kind: "heading"; level: 2 | 3; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "quote"; text: string }
  | { kind: "list"; items: string[] };

const FAST_GROUPING_HEADING: Record<Task1QuestionType, string> = {
  "line-graph": "Time-based charts",
  "bar-chart": "Static charts",
  table: "Static charts",
  "pie-chart": "Static charts",
  "map-plan": "Maps",
  "process-manufacturing": "Processes",
  "natural-lifecycle": "Processes",
  "mixed-visuals": "Mixed visuals",
};

function extractHeadingSection(markdown: string, heading: string, level: 2 | 3): string {
  const lines = markdown.split(/\r?\n/);
  const prefix = "#".repeat(level);
  const marker = `${prefix} ${heading}`;
  const start = lines.findIndex((line) => line.trim() === marker);
  if (start < 0) throw new Error(`Missing Task 1 guide heading: ${heading}`);
  const nextHeading = new RegExp(`^#{${level}}\\s+`);
  const endOffset = lines.slice(start + 1).findIndex((line) => nextHeading.test(line));
  const end = endOffset < 0 ? lines.length : start + 1 + endOffset;
  return lines.slice(start, end).join("\n").trim();
}

export function extractTask1Guide(markdown: string, type: Task1QuestionType): string {
  const mainSection = extractHeadingSection(markdown, TASK1_TYPE_META[type].guideHeading, 2);
  const fastGroupingSection = extractHeadingSection(markdown, "Fast Grouping Rules", 2);
  const matchingRule = extractHeadingSection(
    fastGroupingSection,
    FAST_GROUPING_HEADING[type],
    3,
  ).replace(/^###\s+.+\n?/, "").trim();
  return `${mainSection}\n\n### Fast grouping rule\n\n${matchingRule}`;
}

export function parseGuideBlocks(markdown: string): GuideBlock[] {
  const lines = markdown.split(/\r?\n/);
  const blocks: GuideBlock[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index].trim();
    if (!line) {
      index += 1;
      continue;
    }
    if (line.startsWith("### ")) {
      blocks.push({ kind: "heading", level: 3, text: line.slice(4).trim() });
      index += 1;
      continue;
    }
    if (line.startsWith("## ")) {
      blocks.push({ kind: "heading", level: 2, text: line.slice(3).trim() });
      index += 1;
      continue;
    }
    if (line.startsWith("> ")) {
      blocks.push({ kind: "quote", text: line.slice(2).trim() });
      index += 1;
      continue;
    }
    if (line.startsWith("- ")) {
      const items: string[] = [];
      while (index < lines.length && lines[index].trim().startsWith("- ")) {
        items.push(lines[index].trim().slice(2).trim());
        index += 1;
      }
      blocks.push({ kind: "list", items });
      continue;
    }

    const paragraph: string[] = [line];
    index += 1;
    while (index < lines.length) {
      const next = lines[index].trim();
      if (!next || /^(## |### |> |- )/.test(next)) break;
      paragraph.push(next);
      index += 1;
    }
    blocks.push({ kind: "paragraph", text: paragraph.join(" ") });
  }

  return blocks;
}
