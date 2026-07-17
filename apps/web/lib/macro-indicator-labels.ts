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
  cn_lpr_1y: "terminalMacroLabelCnLpr1y",
  cn_lpr_5y: "terminalMacroLabelCnLpr5y",
  cn_shibor_overnight: "terminalMacroLabelCnShiborOvernight",
  cn_fr007: "terminalMacroLabelCnFr007",
  cn_fdr007: "terminalMacroLabelCnFdr007",
  cn_10y_yield: "terminalMacroLabelCn10yYield",
  cn_cpi_yoy: "terminalMacroLabelCnCpiYoy",
  cn_ppi_yoy: "terminalMacroLabelCnPpiYoy",
  cn_retail_sales_yoy: "terminalMacroLabelCnRetailSalesYoy",
  cn_manufacturing_pmi: "terminalMacroLabelCnManufacturingPmi",
  cn_gdp_yoy: "terminalMacroLabelCnGdpYoy",
  cn_exports_yoy: "terminalMacroLabelCnExportsYoy",
  cn_imports_yoy: "terminalMacroLabelCnImportsYoy",
  cn_m1_yoy: "terminalMacroLabelCnM1Yoy",
  cn_m0_yoy: "terminalMacroLabelCnM0Yoy",
  cn_tax_revenue_yoy: "terminalMacroLabelCnTaxRevenueYoy",
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
