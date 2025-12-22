import React from "react";
import { render, screen } from "@testing-library/react";
import RegistryView from "../RegistryView";

describe("RegistryView", () => {
  it("renders tabs and shows read-only notice", () => {
    render(<RegistryView />);
    expect(screen.getByRole("heading", { name: /Registry/i })).toBeInTheDocument();
    expect(screen.getByText(/Read-only view/i)).toBeInTheDocument();
  });
});


