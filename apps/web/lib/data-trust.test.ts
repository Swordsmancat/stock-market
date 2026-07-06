import { describe, expect, it } from "vitest";
import { createDataTrustSignal } from "./data-trust";

describe("createDataTrustSignal", () => {
  it("normalizes fresh market data", () => {
    expect(createDataTrustSignal({ status: "ok", freshness: "fresh", provider: "yfinance" })).toMatchObject({
      severity: "fresh",
      label: "新鲜",
      provider: "yfinance",
    });
  });

  it("normalizes stale data", () => {
    expect(createDataTrustSignal({ status: "ok", freshness: "stale" }).severity).toBe("stale");
  });

  it("normalizes delayed data from availability metadata", () => {
    const signal = createDataTrustSignal({ availability: { status: "ok", is_delayed: true, delay_minutes: 15 } });

    expect(signal).toMatchObject({ severity: "delayed", delayMinutes: 15, isDelayed: true });
  });

  it("normalizes mock and fixture sources conservatively", () => {
    expect(createDataTrustSignal({ data_mode: "mock" }).severity).toBe("mock");
    expect(createDataTrustSignal({ source: "static_sector_fixture" }).severity).toBe("mock");
  });

  it("normalizes degraded, no-data, and unavailable states", () => {
    expect(createDataTrustSignal({ status: "degraded" }).severity).toBe("degraded");
    expect(createDataTrustSignal({ status: "no_data" }).severity).toBe("no_data");
    expect(createDataTrustSignal({ status: "unavailable" }).severity).toBe("unavailable");
  });

  it("does not fabricate freshness when metadata is missing", () => {
    expect(createDataTrustSignal({}).severity).toBe("unknown");
  });
});
