import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { PriceChangeBadge } from "./price-change-badge";

const { getMovementColorMock, getMovementBgMock } = vi.hoisted(() => ({
  getMovementColorMock: vi.fn((value: number) => value >= 0 ? "text-positive" : "text-negative"),
  getMovementBgMock: vi.fn((value: number) => value >= 0 ? "bg-positive" : "bg-negative"),
}));

vi.mock("@/context/market-colors-context", () => ({
  useMarketColorsContext: () => ({
    colorScheme: "china",
    setColorScheme: vi.fn(),
    getMovementColor: getMovementColorMock,
    getMovementBg: getMovementBgMock,
    colors: {
      up: "text-positive",
      down: "text-negative",
      upBg: "bg-positive",
      downBg: "bg-negative",
    },
  }),
}));

beforeEach(() => {
  getMovementColorMock.mockClear();
  getMovementBgMock.mockClear();
});

afterEach(() => {
  cleanup();
});

function getBadgeElement(formattedPercent: string): HTMLElement {
  const percentElement = screen.getByText(formattedPercent);
  const badgeElement = percentElement.parentElement;
  if (!badgeElement) {
    throw new Error("Expected percent element to be inside the badge root element.");
  }
  return badgeElement;
}

it("uses global market colors for positive changes", () => {
  render(<PriceChangeBadge percentChange={0.015} />);

  expect(getBadgeElement("+1.50%")).toHaveClass("text-positive", "bg-positive");
  expect(getMovementColorMock).toHaveBeenCalledWith(1);
  expect(getMovementBgMock).toHaveBeenCalledWith(1);
});

it("uses global market colors for negative changes", () => {
  render(<PriceChangeBadge percentChange={-0.025} />);

  expect(getBadgeElement("-2.50%")).toHaveClass("text-negative", "bg-negative");
  expect(getMovementColorMock).toHaveBeenCalledWith(-1);
  expect(getMovementBgMock).toHaveBeenCalledWith(-1);
});

it("keeps flat changes neutral", () => {
  render(<PriceChangeBadge percentChange={0} />);

  expect(getBadgeElement("0.00%")).toHaveClass("text-muted-foreground");
  expect(getMovementColorMock).not.toHaveBeenCalled();
  expect(getMovementBgMock).not.toHaveBeenCalled();
});
