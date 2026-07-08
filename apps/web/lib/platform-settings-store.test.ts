import { expect, it } from "vitest";

import {
  DEFAULT_FAVORITE_HOME_INDEX_CODES,
  DEFAULT_HOME_INDEX_DISPLAY_FIELDS,
  DEFAULT_NEWS_SEARCH_PROVIDER_ORDER,
  normalizeFavoriteHomeIndexCodes,
  normalizeHomeIndexDisplayFields,
  normalizeNewsSearchEnabledProviders,
  normalizeNewsSearchProviderOrder,
} from "./platform-settings-store";

it("normalizes homepage index codes from strings while preserving order", () => {
  expect(normalizeFavoriteHomeIndexCodes("us_sp_500\ncn_csi_300, us_sp_500\n\ncn_chinext")).toEqual([
    "us_sp_500",
    "cn_csi_300",
    "cn_chinext",
  ]);
});

it("falls back to default homepage index codes when the input is empty", () => {
  expect(normalizeFavoriteHomeIndexCodes(" \n , ")).toEqual([...DEFAULT_FAVORITE_HOME_INDEX_CODES]);
  expect(normalizeFavoriteHomeIndexCodes(null)).toEqual([...DEFAULT_FAVORITE_HOME_INDEX_CODES]);
});

it("normalizes homepage index display fields and removes unknown values", () => {
  expect(
    normalizeHomeIndexDisplayFields([
      "latest_close",
      "provider",
      "unknown_field",
      "latest_close",
      "as_of",
    ]),
  ).toEqual(["latest_close", "provider", "as_of"]);
});

it("falls back to default homepage index display fields when no valid fields remain", () => {
  expect(normalizeHomeIndexDisplayFields("unknown_field, another_unknown")).toEqual([
    ...DEFAULT_HOME_INDEX_DISPLAY_FIELDS,
  ]);
});

it("normalizes news search provider order and appends registry providers", () => {
  expect(normalizeNewsSearchProviderOrder("serpapi_baidu\nanspire\nunknown\nanspire").slice(0, 3)).toEqual([
    "serpapi_baidu",
    "anspire",
    "tavily",
  ]);
  expect(normalizeNewsSearchProviderOrder(null)).toEqual([...DEFAULT_NEWS_SEARCH_PROVIDER_ORDER]);
});

it("normalizes enabled news search providers without forcing defaults for empty input", () => {
  expect(normalizeNewsSearchEnabledProviders(["anspire", "mock", "unknown", "anspire"])).toEqual([
    "anspire",
    "mock",
  ]);
  expect(normalizeNewsSearchEnabledProviders("")).toEqual([]);
});
