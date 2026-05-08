import { useState, useEffect } from "react";
import { getAuthSession, login } from "../services/api";

interface Props {
  children: React.ReactNode;
}

export function AccessGate({ children }: Props) {
  const [authenticated, setAuthenticated] = useState(false);
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const [checking, setChecking] = useState(true);
  const [backendUnavailable, setBackendUnavailable] = useState(false);

  useEffect(() => {
    setChecking(true);
    getAuthSession()
      .then((session) => setAuthenticated(session.authenticated))
      .catch(() => {
        setAuthenticated(false);
        setBackendUnavailable(true);
      })
      .finally(() => setChecking(false));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await login(input);
      setAuthenticated(true);
      setBackendUnavailable(false);
    } catch (e) {
      if (e instanceof TypeError) {
        setBackendUnavailable(true);
        return;
      }
      setError("Incorrect passcode. Try again.");
    }
  }

  if (authenticated) return <>{children}</>;

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-200 w-full max-w-sm">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">IELTS Practice</h1>
          <p className="text-gray-500 text-sm">Checking access…</p>
        </div>
      </div>
    );
  }

  if (backendUnavailable) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="bg-white p-8 rounded-xl shadow-sm border border-red-200 w-full max-w-md">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">IELTS Practice</h1>
          <p className="text-sm text-red-600">
            Backend authentication is unavailable. Start the backend API and refresh.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-200 w-full max-w-sm">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">IELTS Practice</h1>
        <p className="text-gray-500 text-sm mb-6">Enter passcode to continue</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="password"
            value={input}
            onChange={(e) => { setInput(e.target.value); setError(""); }}
            placeholder="Passcode"
            className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            autoFocus
          />
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Enter
          </button>
        </form>
      </div>
    </div>
  );
}
