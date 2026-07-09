import { getTranslations } from "next-intl/server";
import { Link } from "@/src/i18n/routing";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/empty-state";
import { FinancialPageHeader } from "@/components/financial-page-header";
import { GenerateDailyReportButton } from "@/components/generate-daily-report-button";
import { getDashboardDateRanges } from "@/lib/dates";
import { ExternalLink } from "lucide-react";
import { backendFetch } from "@/lib/backend-api";

type ReportItem = {
  id: string;
  symbol: string;
  report_type: string;
  as_of: string;
  content_markdown: string;
  task_run_id?: string | null;
  source_summary?: ReportSourceSummary | null;
};

type ReportSourceSummary = {
  source?: string | null;
  price_source?: string | null;
  provider?: string | null;
  requested_provider?: string | null;
  effective_provider?: string | null;
  task_run_id?: string | null;
};

type ReportsPayload = {
  total: number;
  limit: number;
  offset: number;
  items: ReportItem[];
};

const defaultLimit = 10;

async function fetchReports(params: URLSearchParams): Promise<ReportsPayload> {
  const response = await backendFetch(`/reports?${params.toString()}`, { cache: "no-store" });
  if (!response.ok) {
    return { total: 0, limit: 50, offset: 0, items: [] };
  }
  return response.json() as Promise<ReportsPayload>;
}

function cleanReportPreviewLine(line: string): string {
  return line
    .replace(/^#{1,6}\s*/, "")
    .replace(/^[-*]\s+/, "")
    .replace(/\[([^\]]+)]\([^)]*\)/g, "$1")
    .replace(/[*_`]/g, "")
    .trim();
}

function extractReportPreview(contentMarkdown: string, fallback: string): string {
  const lines = contentMarkdown.split(/\r?\n/).map((line) => line.trim());
  const headingLine = lines.find((line) => line.startsWith("#"));
  const meaningfulLine = headingLine ?? lines.find((line) => line.length > 0);

  if (meaningfulLine === undefined) {
    return fallback;
  }

  const cleanedLine = cleanReportPreviewLine(meaningfulLine);
  return cleanedLine || fallback;
}

function buildReportSourceDetails(sourceSummary: ReportSourceSummary | null | undefined): string[] {
  if (!sourceSummary) {
    return [];
  }

  const details: string[] = [];
  if (sourceSummary.source) {
    details.push(`source: ${sourceSummary.source}`);
  }
  if (sourceSummary.price_source) {
    details.push(`price_source: ${sourceSummary.price_source}`);
  }
  if (sourceSummary.effective_provider || sourceSummary.provider) {
    details.push(`provider: ${sourceSummary.effective_provider ?? sourceSummary.provider}`);
  }
  if (sourceSummary.requested_provider) {
    details.push(`requested_provider: ${sourceSummary.requested_provider}`);
  }
  if (sourceSummary.task_run_id) {
    details.push(`task_run_id: ${sourceSummary.task_run_id}`);
  }
  return details;
}

export default async function ReportsCenterPage({
  searchParams = Promise.resolve({}),
}: {
  searchParams?: Promise<{
    symbol?: string;
    report_type?: string;
    q?: string;
    as_of_start?: string;
    as_of_end?: string;
    limit?: string;
    offset?: string;
  }>;
} = {}) {
  const params = await searchParams;
  const apiParams = new URLSearchParams();
  if (params.symbol) apiParams.set("symbol", params.symbol);
  if (params.report_type) apiParams.set("report_type", params.report_type);
  if (params.q) apiParams.set("q", params.q);
  if (params.as_of_start) apiParams.set("as_of_start", params.as_of_start);
  if (params.as_of_end) apiParams.set("as_of_end", params.as_of_end);
  apiParams.set("limit", params.limit ?? String(defaultLimit));
  apiParams.set("offset", params.offset ?? "0");

  const payload = await fetchReports(apiParams);
  const { getTranslations } = await import("next-intl/server");
  const t = await getTranslations("ReportsCenter");
  const { analysis } = getDashboardDateRanges();
  const generateSymbol = params.symbol?.trim().toUpperCase() || "AAPL";
  const currentOffset = payload.offset;
  const currentLimit = payload.limit;
  const visibleStart = payload.total === 0 ? 0 : currentOffset + 1;
  const visibleEnd = Math.min(currentOffset + payload.items.length, payload.total);
  const hasPreviousPage = currentOffset > 0;
  const hasNextPage = currentOffset + currentLimit < payload.total;
  const pageHref = (offset: number) => {
    const nextParams = new URLSearchParams(apiParams);
    nextParams.set("offset", String(Math.max(0, offset)));
    return `/reports?${nextParams.toString()}` as any;
  };

  return (
    <div className="space-y-6">
      <FinancialPageHeader
        title={t("title")}
        description={t("description")}
        badges={[]}
        metrics={[
          { label: t("symbol"), value: generateSymbol },
          { label: t("asOf"), value: params.as_of_start || params.as_of_end ? `${params.as_of_start ?? "--"} / ${params.as_of_end ?? "--"}` : "--" },
          { label: t("reportType"), value: params.report_type || t("allTypes") },
        ]}
        actions={
          <GenerateDailyReportButton
            symbol={generateSymbol}
            start={analysis.start}
            end={analysis.end}
            provider={params.symbol ? undefined : null}
            variant="default"
            size="default"
          />
        }
      />

      <Card>
        <CardContent className="pt-6">
          <form className="grid gap-3 md:grid-cols-[minmax(0,10rem)_minmax(0,12rem)_minmax(0,1fr)_minmax(0,10rem)_minmax(0,10rem)_auto_auto]">
            <Input
              name="symbol"
              defaultValue={params.symbol ?? ""}
              placeholder={t("symbolPlaceholder")}
            />
            <select
              name="report_type"
              defaultValue={params.report_type ?? ""}
              className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
            >
              <option value="">{t("allTypes")}</option>
              <option value="stock_daily">stock daily</option>
            </select>
            <Input
              name="q"
              defaultValue={params.q ?? ""}
              placeholder={t("searchPlaceholder")}
            />
            <Input
              name="as_of_start"
              type="date"
              defaultValue={params.as_of_start ?? ""}
              aria-label={t("fromDate")}
            />
            <Input
              name="as_of_end"
              type="date"
              defaultValue={params.as_of_end ?? ""}
              aria-label={t("toDate")}
            />
            <Button type="submit">{t("search")}</Button>
            <Button variant="outline" asChild>
              <Link href="/reports">{t("reset")}</Link>
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
          <CardDescription>
            {t("total", { count: payload.total })}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[100px]">{t("symbol")}</TableHead>
                <TableHead className="w-[150px]">{t("reportType")}</TableHead>
                <TableHead className="w-[150px]">{t("asOf")}</TableHead>
                <TableHead>{t("preview")}</TableHead>
                <TableHead className="w-[120px]">{t("taskRun")}</TableHead>
                <TableHead className="text-right w-[100px]">{t("actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {payload.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                    <EmptyState title={t("noData")} description={t("emptyHint")} />
                  </TableCell>
                </TableRow>
              ) : (
                payload.items.map((item, index) => (
                  <TableRow key={`${item.symbol}-${item.as_of}-${index}`}>
                    <TableCell className="font-medium">
                      <Link href={`/instruments/${item.symbol}` as any} className="hover:underline">
                        {item.symbol}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="capitalize">
                        {item.report_type.replace("_", " ")}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {item.as_of ? new Date(item.as_of).toLocaleDateString() : "--"}
                    </TableCell>
                    <TableCell className="max-w-[300px] text-muted-foreground">
                      <div className="truncate">
                        {extractReportPreview(item.content_markdown, t("emptyPreview"))}
                      </div>
                      {buildReportSourceDetails(item.source_summary).length > 0 ? (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {buildReportSourceDetails(item.source_summary).map((detail) => (
                            <Badge key={detail} variant="outline" className="text-[10px] font-normal">
                              {detail}
                            </Badge>
                          ))}
                        </div>
                      ) : null}
                    </TableCell>
                    <TableCell>
                      {item.task_run_id ? (
                        <Link
                          href={`/task-runs/${item.task_run_id}` as any}
                          className="text-sm text-primary hover:underline"
                        >
                          {item.task_run_id.slice(0, 8)}
                        </Link>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" asChild>
                        <Link href={`/reports/${item.id}` as any} title={t("viewFullReport")}>
                          <ExternalLink className="h-4 w-4" />
                          <span className="sr-only">{t("viewFullReport")}</span>
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
          <div className="mt-4 flex flex-col gap-3 text-sm text-muted-foreground md:flex-row md:items-center md:justify-between">
            <span>
              {t("pageStatus", {
                start: visibleStart,
                end: visibleEnd,
                total: payload.total,
              })}
            </span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={!hasPreviousPage} asChild={hasPreviousPage}>
                {hasPreviousPage ? (
                  <Link href={pageHref(currentOffset - currentLimit)}>{t("previous")}</Link>
                ) : (
                  <span>{t("previous")}</span>
                )}
              </Button>
              <Button variant="outline" size="sm" disabled={!hasNextPage} asChild={hasNextPage}>
                {hasNextPage ? (
                  <Link href={pageHref(currentOffset + currentLimit)}>{t("next")}</Link>
                ) : (
                  <span>{t("next")}</span>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
