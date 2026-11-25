import http.client
import json
import threading

import pytest

from app.server import TaskServer
from app.validation import STATUSES


class InMemoryTaskRepository:
    """Test double with the same interface as MySQLTaskRepository."""

    def __init__(self):
        self._tasks = {}
        self._next_id = 1
        self.healthy = True

    def ping(self):
        if not self.healthy:
            raise ConnectionError("database unreachable")

    def list(self, status=None):
        tasks = sorted(self._tasks.values(), key=lambda t: t["id"], reverse=True)
        return [dict(t) for t in tasks if status is None or t["status"] == status]

    def get(self, task_id):
        task = self._tasks.get(task_id)
        return dict(task) if task else None

    def create(self, fields):
        task = {
            "id": self._next_id,
            "title": fields["title"],
            "description": fields.get("description"),
            "status": fields.get("status", "todo"),
            "priority": fields.get("priority", "medium"),
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }
        self._tasks[task["id"]] = task
        self._next_id += 1
        return dict(task)

    def update(self, task_id, fields):
        if task_id not in self._tasks:
            return None
        self._tasks[task_id].update(fields)
        return dict(self._tasks[task_id])

    def delete(self, task_id):
        return self._tasks.pop(task_id, None) is not None

    def stats(self):
        by_status = {s: 0 for s in STATUSES}
        for task in self._tasks.values():
            by_status[task["status"]] += 1
        return {"total": len(self._tasks), "by_status": by_status}


@pytest.fixture
def api():
    repo = InMemoryTaskRepository()
    server = TaskServer(("127.0.0.1", 0), repo)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    def call(method, path, body=None, raw=None):
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        payload = raw if raw is not None else (json.dumps(body) if body is not None else None)
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        conn.request(method, path, body=payload, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp.status, (json.loads(data) if data else None)

    call.repo = repo
    yield call
    server.shutdown()
    server.server_close()


def test_health_ok(api):
    assert api("GET", "/api/health") == (200, {"status": "ok", "database": "up"})


def test_health_reports_db_down(api):
    api.repo.healthy = False
    status, body = api("GET", "/api/health")
    assert status == 503
    assert body["database"] == "down"


def test_create_and_get_task(api):
    status, created = api("POST", "/api/tasks", {"title": "  Write Jenkinsfile ", "priority": "high"})
    assert status == 201
    assert created["title"] == "Write Jenkinsfile"
    assert created["status"] == "todo"

    status, fetched = api("GET", f"/api/tasks/{created['id']}")
    assert status == 200
    assert fetched == created


def test_create_requires_title(api):
    status, body = api("POST", "/api/tasks", {"title": "   "})
    assert status == 400
    assert "title" in body["details"]


def test_create_rejects_invalid_enum(api):
    status, body = api("POST", "/api/tasks", {"title": "x", "priority": "urgent"})
    assert status == 400
    assert "priority" in body["details"]


def test_create_rejects_invalid_json(api):
    status, body = api("POST", "/api/tasks", raw="{not json")
    assert status == 400
    assert body["error"] == "Invalid JSON body"


def test_list_with_status_filter(api):
    api("POST", "/api/tasks", {"title": "a"})
    api("POST", "/api/tasks", {"title": "b", "status": "done"})

    status, tasks = api("GET", "/api/tasks?status=done")
    assert status == 200
    assert [t["title"] for t in tasks] == ["b"]

    status, _ = api("GET", "/api/tasks?status=bogus")
    assert status == 400


def test_update_task(api):
    _, task = api("POST", "/api/tasks", {"title": "a"})
    status, updated = api("PATCH", f"/api/tasks/{task['id']}", {"status": "in_progress"})
    assert status == 200
    assert updated["status"] == "in_progress"


def test_update_requires_fields(api):
    _, task = api("POST", "/api/tasks", {"title": "a"})
    status, _ = api("PUT", f"/api/tasks/{task['id']}", {"unknown": 1})
    assert status == 400


def test_delete_task(api):
    _, task = api("POST", "/api/tasks", {"title": "a"})
    assert api("DELETE", f"/api/tasks/{task['id']}") == (204, None)
    assert api("GET", f"/api/tasks/{task['id']}")[0] == 404
    assert api("DELETE", f"/api/tasks/{task['id']}")[0] == 404


def test_stats(api):
    api("POST", "/api/tasks", {"title": "a"})
    api("POST", "/api/tasks", {"title": "b", "status": "done"})
    status, stats = api("GET", "/api/stats")
    assert status == 200
    assert stats == {"total": 2, "by_status": {"todo": 1, "in_progress": 0, "done": 1}}


def test_unknown_route_and_method(api):
    assert api("GET", "/api/nope")[0] == 404
    assert api("DELETE", "/api/tasks")[0] == 405
