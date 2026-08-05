import { createBrowserRouter } from "react-router";
import { App } from "./App";
import { TestSelector } from "./components/TestSelector";
import { ReadingTest } from "./components/ReadingTest";
import { ResultsView } from "./components/ResultsView";
import { ProgressDashboard } from "./components/ProgressDashboard";
import { WritingTestSelector } from "./components/WritingTestSelector";
import { WritingTest } from "./components/WritingTest";
import { WritingResultsView } from "./components/WritingResultsView";
import { MockExamSetup } from "./components/MockExamSetup";
import { MockRunner } from "./components/MockRunner";
import { MockResultsView } from "./components/MockResultsView";
import { PlanningSelector } from "./components/PlanningSelector";
import { PlanningPractice } from "./components/PlanningPractice";
import { PlanningResultsView } from "./components/PlanningResultsView";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <TestSelector /> },
      { path: "test/:id", element: <ReadingTest /> },
      { path: "results/:id", element: <ResultsView /> },
      { path: "progress", element: <ProgressDashboard /> },
      { path: "writing", element: <WritingTestSelector /> },
      { path: "writing/:id", element: <WritingTest /> },
      { path: "writing-results/:id", element: <WritingResultsView /> },
      { path: "planning", element: <PlanningSelector /> },
      { path: "planning/:testId/:taskNumber", element: <PlanningPractice /> },
      { path: "planning-results/:id", element: <PlanningResultsView /> },
      { path: "mock", element: <MockExamSetup /> },
      { path: "mock/:id", element: <MockRunner /> },
      { path: "mock-results/:id", element: <MockResultsView /> },
    ],
  },
], {
  basename: import.meta.env.BASE_URL,
});
