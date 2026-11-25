async function request(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (res.status === 204) return null;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const details = body.details ? `: ${Object.values(body.details).join(" ")}` : "";
    throw new Error(`${body.error || `Request failed (${res.status})`}${details}`);
  }
  return body;
}

export const api = {
  health: () => request("/health"),
  stats: () => request("/stats"),
  listTasks: (status) =>
    request(status ? `/tasks?status=${encodeURIComponent(status)}` : "/tasks"),
  createTask: (task) => request("/tasks", { method: "POST", body: JSON.stringify(task) }),
  updateTask: (id, changes) =>
    request(`/tasks/${id}`, { method: "PATCH", body: JSON.stringify(changes) }),
  deleteTask: (id) => request(`/tasks/${id}`, { method: "DELETE" }),
};
