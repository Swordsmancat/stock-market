export type TopicResearchId = "agriculture" | "consumption" | "real_estate" | "nonferrous";
export type TopicResearchWindow = "30d" | "90d" | "180d";
export type TopicResearchSectionStatus = "ready" | "empty";

export type TopicResearchMatch = { field: string; keyword: string };

export type TopicResearchNewsItem = {
  id: string;
  symbol: string;
  title: string;
  url: string;
  source: string;
  publishedAt: string;
  summary: string | null;
  matchedOn: TopicResearchMatch;
};

export type TopicResearchRankingItem = {
  date: string;
  rank: number;
  code: string;
  name: string;
  changePercent: number;
  provider: string;
  sourceUrl: string;
  matchedOn: TopicResearchMatch;
};

export type TopicResearchCompanyItem = {
  symbol: string;
  name: string;
  industry: string | null;
  businessScope: string | null;
  profile: string | null;
  asOf: string;
  market: string | null;
  instrumentName: string | null;
  matchedOn: TopicResearchMatch;
};

type TopicResearchSection<T> = {
  status: TopicResearchSectionStatus;
  total: number;
  returned: number;
  latestDate: string | null;
  items: T[];
};

export type TopicResearchPayload = {
  status: "ready" | "empty";
  source: "database";
  taxonomyVersion: string;
  topic: TopicResearchId;
  topics: TopicResearchId[];
  window: TopicResearchWindow;
  period: { start: string; end: string };
  evidenceCount: number;
  latestEvidenceDate: string | null;
  sections: {
    news: TopicResearchSection<TopicResearchNewsItem>;
    industryRankings: TopicResearchSection<TopicResearchRankingItem>;
    companies: TopicResearchSection<TopicResearchCompanyItem>;
  };
};

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function count(value: unknown): number {
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? Math.floor(parsed) : 0;
}

function finite(value: unknown): number | null {
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function match(value: unknown): TopicResearchMatch | null {
  const item = record(value);
  const field = text(item?.field);
  const keyword = text(item?.keyword);
  return field && keyword ? { field, keyword } : null;
}

function topic(value: unknown): TopicResearchId | null {
  return value === "agriculture" || value === "consumption" || value === "real_estate" || value === "nonferrous"
    ? value
    : null;
}

function windowValue(value: unknown): TopicResearchWindow | null {
  return value === "30d" || value === "90d" || value === "180d" ? value : null;
}

function decodeNews(value: unknown): TopicResearchNewsItem | null {
  const item = record(value);
  const matchedOn = match(item?.matched_on);
  const id = text(item?.id);
  const symbol = text(item?.symbol);
  const title = text(item?.title);
  const url = text(item?.url);
  const source = text(item?.source);
  const publishedAt = text(item?.published_at);
  if (!item || !matchedOn || !id || !symbol || !title || !url || !source || !publishedAt) return null;
  return { id, symbol, title, url, source, publishedAt, summary: text(item.summary), matchedOn };
}

function decodeRanking(value: unknown): TopicResearchRankingItem | null {
  const item = record(value);
  const matchedOn = match(item?.matched_on);
  const date = text(item?.date);
  const code = text(item?.code);
  const name = text(item?.name);
  const provider = text(item?.provider);
  const sourceUrl = text(item?.source_url);
  const changePercent = finite(item?.change_percent);
  const rank = count(item?.rank);
  if (!item || !matchedOn || !date || !code || !name || !provider || !sourceUrl || changePercent === null || rank < 1) return null;
  return { date, rank, code, name, provider, sourceUrl, changePercent, matchedOn };
}

function decodeCompany(value: unknown): TopicResearchCompanyItem | null {
  const item = record(value);
  const matchedOn = match(item?.matched_on);
  const symbol = text(item?.symbol);
  const name = text(item?.name);
  const asOf = text(item?.as_of);
  if (!item || !matchedOn || !symbol || !name || !asOf) return null;
  return {
    symbol,
    name,
    industry: text(item.industry),
    businessScope: text(item.business_scope),
    profile: text(item.profile),
    asOf,
    market: text(item.market),
    instrumentName: text(item.instrument_name),
    matchedOn,
  };
}

function decodeSection<T>(value: unknown, decoder: (value: unknown) => T | null): TopicResearchSection<T> | null {
  const section = record(value);
  if (!section || (section.status !== "ready" && section.status !== "empty")) return null;
  const items = (Array.isArray(section.items) ? section.items : []).map(decoder).filter((item): item is T => item !== null);
  if (section.status === "ready" && items.length === 0) return null;
  return {
    status: section.status,
    total: count(section.total),
    returned: count(section.returned),
    latestDate: text(section.latest_date),
    items,
  };
}

export function decodeTopicResearchPayload(value: unknown): TopicResearchPayload | null {
  const payload = record(value);
  const selectedTopic = topic(payload?.topic);
  const selectedWindow = windowValue(payload?.window);
  const period = record(payload?.period);
  const start = text(period?.start);
  const end = text(period?.end);
  const sections = record(payload?.sections);
  const news = decodeSection(sections?.news, decodeNews);
  const industryRankings = decodeSection(sections?.industry_rankings, decodeRanking);
  const companies = decodeSection(sections?.companies, decodeCompany);
  if (
    !payload || payload.source !== "database" ||
    (payload.status !== "ready" && payload.status !== "empty") ||
    !text(payload.taxonomy_version) || !selectedTopic || !selectedWindow || !start || !end ||
    !news || !industryRankings || !companies
  ) return null;
  return {
    status: payload.status,
    source: "database",
    taxonomyVersion: text(payload.taxonomy_version) as string,
    topic: selectedTopic,
    topics: (Array.isArray(payload.topics) ? payload.topics : []).map(topic).filter((item): item is TopicResearchId => item !== null),
    window: selectedWindow,
    period: { start, end },
    evidenceCount: count(payload.evidence_count),
    latestEvidenceDate: text(payload.latest_evidence_date),
    sections: { news, industryRankings, companies },
  };
}
