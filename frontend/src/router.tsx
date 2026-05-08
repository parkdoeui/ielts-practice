import { createBrowserRouter } from "react-router";
import { App } from "./App";
import { TestSelector } from "./components/TestSelector";
import { ReadingTest } from "./components/ReadingTest";
import { ResultsView } from "./components/ResultsView";
import { ProgressDashboard } from "./components/ProgressDashboard";
import { WritingTestSelector } from "./components/WritingTestSelector";
import { WritingTest } from "./components/WritingTest";
import { WritingResultsView } from "./components/WritingResultsView";

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
    ],
  },
], {
  basename: import.meta.env.BASE_URL,
});
