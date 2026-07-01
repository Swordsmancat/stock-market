export type TaskRunItem = {
  id: string;
  status: string;
  task_name: string;
  result_json?: Record<string, unknown> | null;
  error_message?: string | null;
};

type EnqueueResponse = {
  status: string;
  task_run?: TaskRunItem;
  error?: string;
};

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string; error?: string };
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (typeof body.error === "string") {
      return body.error;
    }
  } catch {
    // ignore parse errors
  }
  return "Request failed";
}

export async function pollTaskRun(
  taskRunId: string,
  options?: { intervalMs?: number; timeoutMs?: number },
): Promise<TaskRunItem> {
  const intervalMs = options?.intervalMs ?? 1000;
  const timeoutMs = options?.timeoutMs ?? 60000;
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const response = await fetch(`/api/task-runs/${taskRunId}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }
    const payload = (await response.json()) as { item: TaskRunItem };
    const item = payload.item;
    if (item.status === "succeeded") {
      return item;
    }
    if (item.status === "failed") {
      throw new Error(item.error_message ?? "Task failed");
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }

  throw new Error("Task timed out while waiting for worker");
}

export async function enqueueAndPoll(
  url: string,
  options?: { intervalMs?: number; timeoutMs?: number },
): Promise<TaskRunItem> {
  const response = await fetch(url, { method: "POST" });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  const payload = (await response.json()) as EnqueueResponse;
  if (payload.status !== "dispatched" || !payload.task_run?.id) {
    throw new Error(payload.error ?? "Failed to dispatch background task");
  }
  return pollTaskRun(payload.task_run.id, options);
}
