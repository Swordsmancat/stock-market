export const BUILT_IN_MACRO_LABEL_KEYS = {
  buffett_indicator_us: "terminalMacroLabelBuffettUs",
  buffett_indicator_cn: "terminalMacroLabelBuffettCn",
  buffett_indicator_hk: "terminalMacroLabelBuffettHk",
  us_10y_yield: "terminalMacroLabelUs10yYield",
  us_2y_yield: "terminalMacroLabelUs2yYield",
  us_10y_2y_spread: "terminalMacroLabelUs10y2ySpread",
  us_cpi_yoy: "terminalMacroLabelUsCpiYoy",
  us_m2_yoy: "terminalMacroLabelUsM2Yoy",
  cn_m2_yoy: "terminalMacroLabelCnM2Yoy",
} as const;

export type BuiltInMacroLabelKey =
  (typeof BUILT_IN_MACRO_LABEL_KEYS)[keyof typeof BUILT_IN_MACRO_LABEL_KEYS];

export function getBuiltInMacroLabelKey(
  code: string,
): BuiltInMacroLabelKey | null {
  return Object.hasOwn(BUILT_IN_MACRO_LABEL_KEYS, code)
    ? BUILT_IN_MACRO_LABEL_KEYS[
        code as keyof typeof BUILT_IN_MACRO_LABEL_KEYS
      ]
    : null;
}
