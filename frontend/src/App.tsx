import { Link, Outlet, useLocation } from "react-router";
import { AccessGate } from "./components/AccessGate";

function NavBar() {
  const { pathname } = useLocation();
  const isTestRoute = pathname.startsWith("/test/");

  if (isTestRoute) return null; // test view manages its own header

  return (
    <nav className="border-b border-gray-200 bg-white px-4 md:px-6 py-3 flex items-center gap-6 shrink-0">
      <span className="font-bold text-gray-900 text-sm md:text-base">IELTS Practice</span>
      <Link
        to="/"
        className={`text-sm font-medium ${
          pathname === "/" ? "text-blue-600" : "text-gray-500 hover:text-gray-900"
        }`}
      >
        Tests
      </Link>
      <Link
        to="/progress"
        className={`text-sm font-medium ${
          pathname === "/progress" ? "text-blue-600" : "text-gray-500 hover:text-gray-900"
        }`}
      >
        Progress
      </Link>
    </nav>
  );
}

export function App() {
  return (
    <AccessGate>
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <NavBar />
        <main className="flex-1 flex flex-col min-h-0">
          <Outlet />
        </main>
      </div>
    </AccessGate>
  );
}

export default App;
