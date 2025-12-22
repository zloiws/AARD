import React, { createContext, useContext, useEffect, useState } from "react";

type SessionContextType = {
  sessionId: string | null;
  setSessionId: (id: string | null) => void;
};

const SessionContext = createContext<SessionContextType | undefined>(undefined);

const STORAGE_KEY = "aard_session_id";

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionIdState] = useState<string | null>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  });

  useEffect(() => {
    try {
      if (sessionId) localStorage.setItem(STORAGE_KEY, sessionId);
      else localStorage.removeItem(STORAGE_KEY);
    } catch {}
  }, [sessionId]);

  const setSessionId = (id: string | null) => {
    setSessionIdState(id);
  };

  return <SessionContext.Provider value={{ sessionId, setSessionId }}>{children}</SessionContext.Provider>;
}

export function useSessionContext() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSessionContext must be used within SessionProvider");
  return ctx;
}


