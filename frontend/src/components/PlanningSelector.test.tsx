import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { PlanningSelector } from "./PlanningSelector";

describe("PlanningSelector", () => {
  it("opens on Task 1 and exposes a guide action for every Task 1 prompt", () => {
    const markup = renderToStaticMarkup(
      <MemoryRouter>
        <PlanningSelector />
      </MemoryRouter>,
    );

    expect(markup).toContain("Use four notes: introduction, overview, detail paragraph 1, and detail paragraph 2.");
    expect(markup.match(/>Guide<\/button>/g)).toHaveLength(60);
    expect(markup).toContain("Open Map or plan guide for Writing Test 1");
    expect(markup).not.toContain("Plan the introduction, two developed arguments, and a consistent conclusion.");
  });
});
