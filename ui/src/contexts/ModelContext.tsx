import React, { createContext, useContext, useEffect, useState } from "react";

type ModelSelection = {
  serverId: string | null;
  modelName: string | null;
};

type ModelContextType = {
  selection: ModelSelection;
  setSelection: (s: ModelSelection) => void;
};

const STORAGE_KEY = "aard_model_selection";

const ModelContext = createContext<ModelContextType | undefined>(undefined);

export function ModelProvider({ children }: { children: React.ReactNode }) {
  const [selection, setSelectionState] = useState<ModelSelection>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return JSON.parse(raw);
    } catch {}
    return { serverId: null, modelName: null };
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(selection));
    } catch {}
  }, [selection]);

  const setSelection = (s: ModelSelection) => {
    setSelectionState(s);
  };

  return <ModelContext.Provider value={{ selection, setSelection }}>{children}</ModelContext.Provider>;
}

export function useModelContext() {
  const ctx = useContext(ModelContext);
  if (!ctx) throw new Error("useModelContext must be used within ModelProvider");
  return ctx;
}


