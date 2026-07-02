import { getTranslations } from "next-intl/server";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Link } from "@/src/i18n/routing";
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
import { TaskRunRetryButton } from "@/components/task-run-actions";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { backendFetch } from "@/lib/backend-api";

type TaskRun = {
  id: string;
  task_name: string;
  status: string;
  started_at: string;
  duration_ms: number | null;
  input_json: Record<string, unknown>;
  result_json: any | null;
  error_message: string | null;
};

type TaskRunsPayload = {
  items: TaskRun[];
};

type TaskRunsFetchResult = TaskRunsPayload & {
  hasError: boolean;
};

async function fetchTaskRuns(status?: string): Promise<TaskRunsFetchResult> {
  const params = new URLSearchParams({ limit: "20" });
  if (status) {
    params.set("status", status);
  }

  try {
    const response = await backendFetch(`/task-runs/recent?${params.toString()}`, { cache: "no-store" });
    if (!response.ok) {
      return { items: [], hasError: true };
    }

    const payload = (await response.json()) as TaskRunsPayload;
    return { items: payload.items, hasError: false };
  } catch {
    return { items: [], hasError: true };
  }
}

function formatTaskRunStatus(
  status: string,
  t: Awaited<ReturnType<typeof getTranslations>>,
): string {
  if (status === "running" || status === "succeeded" || status === "failed") {
    return t(status);
  }

  return status;
}

export default async function TaskRunsPage({
  searchParams = Promise.resolve({}),
}: {
  searchParams?: Promise<{ status?: string }>;
} = {}) {
  const params = await searchParams;
  const selectedStatus = ["running", "succeeded", "failed"].includes(params.status ?? "")
    ? params.status
    : undefined;
  const payload = await fetchTaskRuns(selectedStatus);
  const { getTranslations } = await import("next-intl/server");
  const t = await getTranslations("TaskRuns");

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button variant={!selectedStatus ? "default" : "outline"} size="sm" asChild>
          <Link href="/task-runs">{t("all")}</Link>
        </Button>
        {(["running", "succeeded", "failed"] as const).map((status) => (
          <Button key={status} variant={selectedStatus === status ? "default" : "outline"} size="sm" asChild>
            <Link href={`/task-runs?status=${status}` as any}>{t(status)}</Link>
          </Button>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
          {!payload.hasError ? (
            <CardDescription>{t("recentCount", { count: payload.items.length })}</CardDescription>
          ) : null}
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("taskName")}</TableHead>
                <TableHead>{t("status")}</TableHead>
                <TableHead>{t("startedAt")}</TableHead>
                <TableHead>{t("duration")}</TableHead>
                <TableHead>{t("input")}</TableHead>
                <TableHead>{t("result")}</TableHead>
                <TableHead>{t("error")}</TableHead>
                <TableHead className="text-right">{t("actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {payload.hasError ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                    <ErrorState title={t("loadFailed")} description={t("loadFailedHint")} />
                  </TableCell>
                </TableRow>
              ) : payload.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                    <EmptyState title={t("noData")} description={t("emptyHint")} />
                  </TableCell>
                </TableRow>
              ) : (
                payload.items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-medium">
                      <Link href={`/task-runs/${item.id}` as any} className="hover:underline">
                        {item.task_name}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          item.status === "succeeded"
                            ? "default"
                            : item.status === "failed"
                            ? "destructive"
                            : "secondary"
                        }
                      >
                        {formatTaskRunStatus(item.status, t)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {new Date(item.started_at).toLocaleString()}
                    </TableCell>
                    <TableCell>{item.duration_ms ?? "--"}</TableCell>
                    <TableCell className="max-w-[180px] truncate" title={JSON.stringify(item.input_json)}>
                      {item.input_json ? JSON.stringify(item.input_json) : "--"}
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate" title={JSON.stringify(item.result_json)}>
                      {item.result_json ? JSON.stringify(item.result_json) : "--"}
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate text-destructive" title={item.error_message ?? ""}>
                      {item.error_message ?? "--"}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button variant="ghost" size="sm" asChild>
                          <Link href={`/task-runs/${item.id}` as any}>{t("viewDetail")}</Link>
                        </Button>
                        {item.status === "failed" ? <TaskRunRetryButton taskRunId={item.id} /> : null}
                      </div>
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
