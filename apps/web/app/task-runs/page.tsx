type TaskRun = {
  task_name: string;
  status: string;
  started_at?: string | null;
  finished_at?: string | null;
  duration_ms?: number | null;
  result_json?: {
    item_count?: number;
  } | null;
  error_message?: string | null;
};

type RecentTaskRunsPayload = {
  source: string;
  items: TaskRun[];
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const dailyWatchlistTaskName = "reports.refresh_daily_watchlist_analysis";

async function fetchOptionalJson<T>(path: string, fallback: T): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { cache: "no-store" });
  if (!response.ok) {
    return fallback;
  }
  return response.json() as Promise<T>;
}

function taskSummary(taskRun: TaskRun) {
  const processedCount = taskRun.result_json?.item_count ?? 0;
  const duration = taskRun.duration_ms ?? 0;
  return `${taskRun.status}，处理股票数：${processedCount}，耗时：${duration}ms`;
}

export default async function TaskRunsPage() {
  const [latestWatchlistRun, recentRuns] = await Promise.all([
    fetchOptionalJson<TaskRun>(
      `/task-runs/latest?task_name=${dailyWatchlistTaskName}`,
      {
        task_name: dailyWatchlistTaskName,
        status: "not_found",
      },
    ),
    fetchOptionalJson<RecentTaskRunsPayload>("/task-runs/recent?limit=10", {
      source: "unavailable",
      items: [],
    }),
  ]);

  return (
    <main>
      <h1>任务监控</h1>
      <section>
        <h2>每日关注列表报告</h2>
        <p>{taskSummary(latestWatchlistRun)}</p>
        {latestWatchlistRun.error_message ? (
          <p>失败原因：{latestWatchlistRun.error_message}</p>
        ) : null}
      </section>
      <section>
        <h2>最近任务</h2>
        {recentRuns.items.length > 0 ? (
          <ul>
            {recentRuns.items.map((taskRun) => (
              <li key={`${taskRun.task_name}-${taskRun.started_at ?? taskRun.status}`}>
                {taskRun.task_name}：{taskSummary(taskRun)}
                {taskRun.error_message ? `，失败原因：${taskRun.error_message}` : ""}
              </li>
            ))}
          </ul>
        ) : (
          <p>暂无任务运行记录，来源：{recentRuns.source}</p>
        )}
      </section>
    </main>
  );
}
