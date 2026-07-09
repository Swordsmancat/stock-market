import { getTranslations } from "next-intl/server";

import { FinancialPageHeader } from "@/components/financial-page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { backendFetch } from "@/lib/backend-api";
import { Link } from "@/src/i18n/routing";

type ReportDetail = {
  id: string;
  symbol: string;
  report_type: string;
  as_of: string;
  content_markdown: string;
  citations: string[];
  created_at: string;
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

async function fetchReport(reportId: string): Promise<ReportDetail | null> {
  const response = await backendFetch(`/reports/items/${reportId}`, { cache: "no-store" });
  if (!response.ok) {
    return null;
  }
  return response.json() as Promise<ReportDetail>;
}

function citationUrl(citation: string): string | null {
  return citation.match(/https?:\/\/\S+/)?.[0] ?? null;
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
        <FinancialPageHeader
          title={t("title")}
          description={t("noData")}
          badges={[{ label: t("reportType") }]}
          metrics={[
            { label: t("symbol"), value: reportId, description: t("emptyHint") },
            { label: t("asOf"), value: t("noData"), description: t("description") },
          ]}
          actions={
            <Button size="sm" variant="outline" asChild>
              <Link href="/reports">{t("backToReports")}</Link>
            </Button>
          }
        />
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">{t("noData")}</CardContent>
        </Card>
      </div>
    );
  }

  const sourceBadges = buildReportSourceDetails(report.source_summary).map((detail) => ({ label: detail }));

  return (
    <div className="space-y-6">
      <FinancialPageHeader
        title={report.symbol}
        description={
          <>
            {t("asOf")}: {new Date(report.as_of).toLocaleDateString()}
            {report.task_run_id ? (
              <>
                {" / "}
                <Link href={`/task-runs/${report.task_run_id}` as any} className="text-primary hover:underline">
                  {t("taskRun")}: {report.task_run_id.slice(0, 8)}
                </Link>
              </>
            ) : null}
          </>
        }
        badges={[
          { label: report.report_type.replace("_", " "), variant: "secondary" as const },
          ...sourceBadges,
        ]}
        metrics={[
          { label: t("reportType"), value: report.report_type.replace("_", " "), description: t("description") },
          { label: t("asOf"), value: new Date(report.as_of).toLocaleDateString(), description: report.created_at },
          { label: t("citations"), value: report.citations.length, description: t("taskRun") },
        ]}
        actions={
          <>
            <Button size="sm" variant="outline" asChild>
              <Link href="/reports">{t("backToReports")}</Link>
            </Button>
            <Button size="sm" variant="outline" asChild>
              <Link href={`/instruments/${report.symbol}` as any}>{t("viewInstrument")}</Link>
            </Button>
          </>
        }
      />

      <Card>
        <CardContent>
          <pre className="whitespace-pre-wrap font-sans text-sm leading-7">{report.content_markdown}</pre>
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
