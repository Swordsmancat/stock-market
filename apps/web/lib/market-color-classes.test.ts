import { expect, it } from "vitest";
import { getMarketMovementBgClass, getMarketMovementTextClass } from "./market-color-classes";

it("maps China market movement colors and keeps flat values neutral", () => {
  expect(getMarketMovementTextClass("china", 1)).toContain("text-green-600");
  expect(getMarketMovementTextClass("china", -1)).toContain("text-red-600");
  expect(getMarketMovementTextClass("china", 0)).toBe("text-muted-foreground");
  expect(getMarketMovementBgClass("china", 0)).toBe("bg-muted/40");
});

it("maps international market movement colors and keeps flat values neutral", () => {
  expect(getMarketMovementTextClass("international", 1)).toContain("text-red-600");
  expect(getMarketMovementTextClass("international", -1)).toContain("text-green-600");
  expect(getMarketMovementTextClass("international", 0)).toBe("text-muted-foreground");
  expect(getMarketMovementBgClass("international", 0)).toBe("bg-muted/40");
});
