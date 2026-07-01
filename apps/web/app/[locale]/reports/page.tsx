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
import { ExternalLink } from "lucide-react";

type ReportItem = {
  id: string;
  symbol: string;
  report_type: string;
  as_of: string;
  content_markdown: string;
  task_run_id?: string | null;
};

type ReportsPayload = {
  total: number;
  limit: number;
  offset: number;
  items: ReportItem[];
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const defaultLimit = 10;

async function fetchReports(params: URLSearchParams): Promise<ReportsPayload> {
  const response = await fetch(`${apiBaseUrl}/reports?${params.toString()}`, { cache: "no-store" });
  if (!response.ok) {
    return { total: 0, limit: 50, offset: 0, items: [] };
  }
  return response.json() as Promise<ReportsPayload>;
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
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
      </div>

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
                    <TableCell className="max-w-[300px] truncate text-muted-foreground">
                      {item.content_markdown.substring(0, 100)}...
                    </TableCell>
                    <TableCell>
                      {item.task_run_id ? (
                        <Link href="/task-runs" className="text-sm text-primary hover:underline">
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
