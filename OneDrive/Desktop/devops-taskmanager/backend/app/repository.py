from datetime import datetime

import pymysql
from pymysql.cursors import DictCursor

from .validation import STATUSES

COLUMNS = "id, title, description, status, priority, created_at, updated_at"
UPDATABLE_FIELDS = frozenset({"title", "description", "status", "priority"})


def _serialize(row):
    if row is None:
        return None
    return {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in row.items()}


class MySQLTaskRepository:
    """Opens one short-lived connection per call; PyMySQL connections are not thread-safe."""

    def __init__(self, settings):
        self._settings = settings

    def _connect(self):
        s = self._settings
        return pymysql.connect(
            host=s.db_host,
            port=s.db_port,
            user=s.db_user,
            password=s.db_password,
            database=s.db_name,
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=True,
            connect_timeout=5,
        )

    @staticmethod
    def _fetch(cur, task_id):
        cur.execute(f"SELECT {COLUMNS} FROM tasks WHERE id = %s", (task_id,))
        return _serialize(cur.fetchone())

    def ping(self):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")

    def list(self, status=None):
        sql, params = f"SELECT {COLUMNS} FROM tasks", ()
        if status:
            sql, params = sql + " WHERE status = %s", (status,)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql + " ORDER BY id DESC", params)
            return [_serialize(row) for row in cur.fetchall()]

    def get(self, task_id):
        with self._connect() as conn, conn.cursor() as cur:
            return self._fetch(cur, task_id)

    def create(self, fields):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (title, description, status, priority) VALUES (%s, %s, %s, %s)",
                (
                    fields["title"],
                    fields.get("description"),
                    fields.get("status", "todo"),
                    fields.get("priority", "medium"),
                ),
            )
            return self._fetch(cur, cur.lastrowid)

    def update(self, task_id, fields):
        if not fields or not UPDATABLE_FIELDS.issuperset(fields):
            raise ValueError("Unsupported update fields")
        # Column names come from the whitelist above; values are always parameterised.
        assignments = ", ".join(f"{name} = %s" for name in fields)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(f"UPDATE tasks SET {assignments} WHERE id = %s", (*fields.values(), task_id))
            return self._fetch(cur, task_id)

    def delete(self, task_id):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            return cur.rowcount > 0

    def stats(self):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT status, COUNT(*) AS count FROM tasks GROUP BY status")
            rows = cur.fetchall()
        by_status = {status: 0 for status in STATUSES}
        by_status.update({row["status"]: row["count"] for row in rows})
        return {"total": sum(by_status.values()), "by_status": by_status}
