import { createBrowserRouter } from "react-router";
import { App } from "./App";
import { TestSelector } from "./components/TestSelector";
import { ReadingTest } from "./components/ReadingTest";
import { ResultsView } from "./components/ResultsView";
import { ProgressDashboard } from "./components/ProgressDashboard";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <TestSelector /> },
      { path: "test/:id", element: <ReadingTest /> },
      { path: "results/:id", element: <ResultsView /> },
      { path: "progress", element: <ProgressDashboard /> },
    ],
  },
], {
  basename: import.meta.env.BASE_URL,
});
