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
import { ExternalLink } from "lucide-react";

type ReportItem = {
  id: string;
  symbol: string;
  report_type: string;
  as_of: string;
  content_markdown: string;
};

type ReportsPayload = {
  total: number;
  limit: number;
  offset: number;
  items: ReportItem[];
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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
  searchParams?: Promise<{ symbol?: string; q?: string; limit?: string; offset?: string }>;
} = {}) {
  const params = await searchParams;
  const apiParams = new URLSearchParams();
  if (params.symbol) apiParams.set("symbol", params.symbol);
  if (params.q) apiParams.set("q", params.q);
  apiParams.set("limit", params.limit ?? "50");
  apiParams.set("offset", params.offset ?? "0");

  const payload = await fetchReports(apiParams);
  const { getTranslations } = await import("next-intl/server");
  const t = await getTranslations("ReportsCenter");

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
          <form className="flex flex-col gap-3 md:flex-row">
            <Input
              name="symbol"
              defaultValue={params.symbol ?? ""}
              placeholder={t("symbolPlaceholder")}
              className="md:w-40"
            />
            <Input
              name="q"
              defaultValue={params.q ?? ""}
              placeholder={t("searchPlaceholder")}
              className="md:max-w-sm"
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
                <TableHead className="text-right w-[100px]">{t("actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {payload.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                    {t("noData")}
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
        </CardContent>
      </Card>
    </div>
  );
}
