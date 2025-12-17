import React from "react";
import { render, screen } from "@testing-library/react";
import PromptsPanel from "../PromptsPanel";

describe("PromptsPanel", () => {
  it("renders prompts header", () => {
    render(<PromptsPanel />);
    expect(screen.getByText(/Prompts/i)).toBeInTheDocument();
  });
});


