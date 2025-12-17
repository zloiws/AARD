import React from "react";
import { render } from "@testing-library/react";
import GraphCanvas from "../GraphCanvas";

describe("GraphCanvas", () => {
  it("renders svg canvas", () => {
    const { container } = render(<GraphCanvas width={400} height={300} />);
    expect(container.querySelector("svg")).toBeTruthy();
  });
});


