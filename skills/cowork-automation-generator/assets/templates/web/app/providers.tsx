"use client";
// Purpose: wire up the Convex React client and an anonymous per-browser sessionId.

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ConvexProvider, ConvexReactClient } from "convex/react";

const CONVEX_URL = process.env.NEXT_PUBLIC_CONVEX_URL;
const SESSION_STORAGE_KEY = "automation-session-id";

const SessionContext = createContext<string>("");

/** The anonymous session id for this browser. Empty string until hydrated. */
export function useSessionId(): string {
  return useContext(SessionContext);
}

export function Providers({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string>("");

  // Generate (once) and persist an anonymous session id in localStorage. The
  // BYOK key and runs are keyed by this id.
  useEffect(() => {
    let sid = window.localStorage.getItem(SESSION_STORAGE_KEY);
    if (!sid) {
      sid =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : Math.random().toString(36).slice(2) + Date.now().toString(36);
      window.localStorage.setItem(SESSION_STORAGE_KEY, sid);
    }
    setSessionId(sid);
  }, []);

  const client = useMemo(
    () => (CONVEX_URL ? new ConvexReactClient(CONVEX_URL) : null),
    [],
  );

  // Friendly setup screen instead of a hard crash when the URL isn't set yet.
  if (!client) {
    return (
      <main className="setup-note">
        <h1>Almost there</h1>
        <p>
          Set <code>NEXT_PUBLIC_CONVEX_URL</code> in <code>.env.local</code>.
        </p>
        <p>
          Run <code>npx convex dev</code> once — it provisions a deployment and
          writes the URL for you — then restart <code>npm run dev</code>.
        </p>
      </main>
    );
  }

  return (
    <ConvexProvider client={client}>
      <SessionContext.Provider value={sessionId}>
        {children}
      </SessionContext.Provider>
    </ConvexProvider>
  );
}
