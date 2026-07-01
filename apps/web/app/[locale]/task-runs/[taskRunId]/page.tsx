import { getTranslations } from "next-intl/server";
import { Link } from "@/src/i18n/routing";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TaskRunRetryButton } from "@/components/task-run-actions";
import { backendFetch } from "@/lib/backend-api";

type TaskRunDetail = {
  id: string;
  task_name: string;
  status: string;
  started_at: string;
  duration_ms: number | null;
  celery_task_id: string | null;
  input_json: Record<string, unknown>;
  result_json: Record<string, unknown> | null;
  error_message: string | null;
};

async function fetchTaskRun(taskRunId: string): Promise<TaskRunDetail | null> {
  const response = await backendFetch(`/task-runs/${taskRunId}`, { cache: "no-store" });
  if (!response.ok) {
    return null;
  }
  return response.json() as Promise<TaskRunDetail>;
}

export default async function TaskRunDetailPage({
  params,
}: {
  params: Promise<{ taskRunId: string; locale: string }>;
}) {
  const { taskRunId } = await params;
  const taskRun = await fetchTaskRun(taskRunId);
  const t = await getTranslations("TaskRuns");

  if (taskRun === null) {
    return (
      <div className="space-y-6">
        <Button variant="outline" asChild>
          <Link href="/task-runs">{t("backToList")}</Link>
        </Button>
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">{t("notFound")}</CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t("detailTitle")}</h1>
          <p className="font-mono text-sm text-muted-foreground">{taskRun.id}</p>
        </div>
        <Button variant="outline" asChild>
          <Link href="/task-runs">{t("backToList")}</Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle>{taskRun.task_name}</CardTitle>
            <Badge
              variant={
                taskRun.status === "succeeded"
                  ? "default"
                  : taskRun.status === "failed"
                    ? "destructive"
                    : "secondary"
              }
            >
              {taskRun.status}
            </Badge>
          </div>
          <CardDescription>
            {t("startedAt")}: {new Date(taskRun.started_at).toLocaleString()}
            {taskRun.duration_ms != null ? ` · ${taskRun.duration_ms} ms` : ""}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {taskRun.celery_task_id ? (
            <div>
              <h3 className="mb-1 text-sm font-medium">{t("celeryTaskId")}</h3>
              <p className="font-mono text-sm text-muted-foreground">{taskRun.celery_task_id}</p>
            </div>
          ) : null}
          <div>
            <h3 className="mb-1 text-sm font-medium">{t("input")}</h3>
            <pre className="overflow-x-auto rounded-md border bg-muted/50 p-3 text-xs">
              {JSON.stringify(taskRun.input_json, null, 2)}
            </pre>
          </div>
          <div>
            <h3 className="mb-1 text-sm font-medium">{t("result")}</h3>
            <pre className="overflow-x-auto rounded-md border bg-muted/50 p-3 text-xs">
              {taskRun.result_json ? JSON.stringify(taskRun.result_json, null, 2) : "—"}
            </pre>
          </div>
          {taskRun.error_message ? (
            <div>
              <h3 className="mb-1 text-sm font-medium text-destructive">{t("error")}</h3>
              <pre className="overflow-x-auto rounded-md border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
                {taskRun.error_message}
              </pre>
            </div>
          ) : null}
          {taskRun.status === "failed" ? (
            <div className="pt-2">
              <TaskRunRetryButton taskRunId={taskRun.id} />
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
