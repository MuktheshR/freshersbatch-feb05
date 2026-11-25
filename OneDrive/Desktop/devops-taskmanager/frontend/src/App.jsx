import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

const STATUSES = [
  { value: "todo", label: "To Do" },
  { value: "in_progress", label: "In Progress" },
  { value: "done", label: "Done" },
];
const PRIORITIES = ["low", "medium", "high"];
const EMPTY_FORM = { title: "", description: "", priority: "medium" };

export default function App() {
  const [tasks, setTasks] = useState([]);
  const [stats, setStats] = useState({ total: 0, by_status: {} });
  const [filter, setFilter] = useState("");
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState("checking");

  const refresh = useCallback(async () => {
    try {
      const [taskList, statData] = await Promise.all([api.listTasks(filter), api.stats()]);
      setTasks(taskList);
      setStats(statData);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    api
      .health()
      .then(() => setHealth("up"))
      .catch(() => setHealth("down"));
  }, []);

  async function run(action) {
    try {
      await action();
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  function handleCreate(e) {
    e.preventDefault();
    if (!form.title.trim()) {
      setError("Title is required");
      return;
    }
    run(async () => {
      await api.createTask(form);
      setForm(EMPTY_FORM);
    });
  }

  function handleDelete(id) {
    if (window.confirm("Delete this task?")) run(() => api.deleteTask(id));
  }

  return (
    <div className="container">
      <header>
        <h1>Task Manager</h1>
        <span className={`badge health-${health}`}>API: {health}</span>
      </header>

      <section className="stats">
        <div className="stat">
          <strong>{stats.total}</strong>
          <span>Total</span>
        </div>
        {STATUSES.map((s) => (
          <div className="stat" key={s.value}>
            <strong>{stats.by_status[s.value] ?? 0}</strong>
            <span>{s.label}</span>
          </div>
        ))}
      </section>

      <form className="card" onSubmit={handleCreate}>
        <input
          placeholder="Task title"
          maxLength={200}
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
        />
        <textarea
          placeholder="Description (optional)"
          maxLength={2000}
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
        <div className="row">
          <select
            value={form.priority}
            onChange={(e) => setForm({ ...form, priority: e.target.value })}
          >
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p} priority
              </option>
            ))}
          </select>
          <button type="submit">Add task</button>
        </div>
      </form>

      {error && (
        <div className="error" role="alert">
          {error}
          <button className="link" onClick={() => setError("")}>
            dismiss
          </button>
        </div>
      )}

      <div className="row filter">
        <label htmlFor="filter">Filter:</label>
        <select id="filter" value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">All</option>
          {STATUSES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <p>Loading...</p>
      ) : tasks.length === 0 ? (
        <p className="muted">No tasks yet.</p>
      ) : (
        <ul className="tasks">
          {tasks.map((task) => (
            <li key={task.id} className={`card task status-${task.status}`}>
              <div className="task-head">
                <h3>{task.title}</h3>
                <span className={`badge priority-${task.priority}`}>{task.priority}</span>
              </div>
              {task.description && <p>{task.description}</p>}
              <div className="row">
                <select
                  value={task.status}
                  onChange={(e) => run(() => api.updateTask(task.id, { status: e.target.value }))}
                >
                  {STATUSES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
                <small className="muted">
                  {new Date(task.created_at).toLocaleString()}
                </small>
                <button className="danger" onClick={() => handleDelete(task.id)}>
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
