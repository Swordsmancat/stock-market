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

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchTaskRuns(status?: string): Promise<TaskRunsPayload> {
  const params = new URLSearchParams({ limit: "20" });
  if (status) {
    params.set("status", status);
  }
  const response = await fetch(`${apiBaseUrl}/task-runs/recent?${params.toString()}`, { cache: "no-store" });
  if (!response.ok) {
    return { items: [] };
  }
  return response.json() as Promise<TaskRunsPayload>;
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
          <CardDescription>
            {payload.items.length} recent task runs.
          </CardDescription>
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
              </TableRow>
            </TableHeader>
            <TableBody>
              {payload.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                    {t("noData")}
                  </TableCell>
                </TableRow>
              ) : (
                payload.items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-medium">{item.task_name}</TableCell>
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
                        {item.status}
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
