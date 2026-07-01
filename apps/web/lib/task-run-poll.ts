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
  bar_count?: number;
  market?: string;
  symbol?: string;
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

function asSucceededTaskRun(
  taskName: string,
  resultJson: Record<string, unknown>,
): TaskRunItem {
  return {
    id: "sync",
    status: "succeeded",
    task_name: taskName,
    result_json: resultJson,
  };
}

export function normalizeActionResponse(payload: EnqueueResponse, taskName: string): TaskRunItem {
  if (payload.status === "ingested") {
    return asSucceededTaskRun(taskName, {
      market: payload.market,
      bar_count: payload.bar_count,
      status: "ingested",
    });
  }

  if (payload.status === "refreshed" && payload.symbol) {
    return asSucceededTaskRun(taskName, {
      symbol: payload.symbol,
      market: payload.market,
      status: "refreshed",
    });
  }

  if (payload.task_run?.status === "succeeded") {
    return payload.task_run;
  }

  if (payload.status === "dispatch_failed") {
    throw new Error(
      payload.error ??
        payload.task_run?.error_message ??
        "Background worker unavailable. Start Redis, Celery worker, and beat.",
    );
  }

  if (payload.status === "dispatched" && payload.task_run) {
    return payload.task_run;
  }

  throw new Error(payload.error ?? "Failed to dispatch background task");
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
    const payload = (await response.json()) as { item?: TaskRunItem; task_run?: TaskRunItem };
    const item = payload.item ?? payload.task_run;
    if (!item) {
      throw new Error("Task run response missing item");
    }
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
  options?: { intervalMs?: number; timeoutMs?: number; taskName?: string },
): Promise<TaskRunItem> {
  const response = await fetch(url, { method: "POST" });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  const payload = (await response.json()) as EnqueueResponse;
  const taskName = options?.taskName ?? "background.task";

  if (payload.status === "ingested" || payload.status === "refreshed") {
    return normalizeActionResponse(payload, taskName);
  }

  if (payload.status === "dispatched" && payload.task_run?.id) {
    if (payload.task_run.status === "succeeded") {
      return payload.task_run;
    }
    if (payload.task_run.status === "failed") {
      throw new Error(payload.task_run.error_message ?? "Task failed");
    }
    return pollTaskRun(payload.task_run.id, options);
  }

  return normalizeActionResponse(payload, taskName);
}
