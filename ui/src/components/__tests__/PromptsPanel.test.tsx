import React from "react";
import { render, screen } from "@testing-library/react";
import PromptsPanel from "../PromptsPanel";
import { ModelProvider } from "../../contexts/ModelContext";

describe("PromptsPanel", () => {
  it("renders prompts header", () => {
    render(
      <ModelProvider>
        <PromptsPanel />
      </ModelProvider>
    );
    expect(screen.getByText(/Prompts/i)).toBeInTheDocument();
  });
});


