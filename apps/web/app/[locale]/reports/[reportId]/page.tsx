import { getTranslations } from "next-intl/server";
import { Link } from "@/src/i18n/routing";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type ReportDetail = {
  id: string;
  symbol: string;
  report_type: string;
  as_of: string;
  content_markdown: string;
  citations: string[];
  created_at: string;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchReport(reportId: string): Promise<ReportDetail | null> {
  const response = await fetch(`${apiBaseUrl}/reports/items/${reportId}`, { cache: "no-store" });
  if (!response.ok) {
    return null;
  }
  return response.json() as Promise<ReportDetail>;
}

function citationUrl(citation: string): string | null {
  return citation.match(/https?:\/\/\S+/)?.[0] ?? null;
}

export default async function ReportDetailPage({
  params,
}: {
  params: Promise<{ reportId: string; locale: string }>;
}) {
  const { reportId } = await params;
  const report = await fetchReport(reportId);
  const t = await getTranslations("ReportsCenter");

  if (report === null) {
    return (
      <div className="space-y-6">
        <Button variant="outline" asChild>
          <Link href="/reports">{t("backToReports")}</Link>
        </Button>
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            {t("noData")}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Button variant="outline" asChild>
        <Link href="/reports">{t("backToReports")}</Link>
      </Button>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle className="text-2xl">{report.symbol}</CardTitle>
            <Badge variant="secondary" className="capitalize">
              {report.report_type.replace("_", " ")}
            </Badge>
          </div>
          <CardDescription>
            {t("asOf")}: {new Date(report.as_of).toLocaleDateString()}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <pre className="whitespace-pre-wrap font-sans text-sm leading-7">
            {report.content_markdown}
          </pre>
        </CardContent>
      </Card>

      {report.citations.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>{t("citations")}</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">
              {report.citations.map((citation) => {
                const url = citationUrl(citation);
                return (
                  <li key={citation}>
                    {url ? (
                      <a href={url} target="_blank" rel="noreferrer" className="text-primary hover:underline">
                        {citation}
                      </a>
                    ) : (
                      citation
                    )}
                  </li>
                );
              })}
            </ul>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
