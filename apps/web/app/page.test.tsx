import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import HomePage from "./page";

it("renders stock analysis dashboard title", () => {
  render(<HomePage />);
  expect(screen.getByText("股票分析平台")).toBeInTheDocument();
});
