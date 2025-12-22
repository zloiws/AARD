import React from "react";
import { render, screen } from "@testing-library/react";
import TimelineView from "../TimelineView";

describe("TimelineView", () => {
  it("renders no events message", () => {
    render(<TimelineView />);
    expect(screen.getByText(/No events/i)).toBeInTheDocument();
  });
});


