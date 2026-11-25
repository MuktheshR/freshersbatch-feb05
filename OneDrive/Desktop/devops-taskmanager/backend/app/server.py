import json
import logging
import os
import re
import signal
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .config import Settings
from .repository import MySQLTaskRepository
from .validation import STATUSES, ValidationError, validate_task

logger = logging.getLogger("taskmgr")

MAX_BODY_BYTES = 64 * 1024
TASK_DETAIL_PATH = re.compile(r"^/api/tasks/(\d+)$")

COLLECTION_ROUTES = {
    "/api/health": {"GET": "_health"},
    "/api/stats": {"GET": "_stats"},
    "/api/tasks": {"GET": "_list_tasks", "POST": "_create_task"},
}
DETAIL_ROUTES = {
    "GET": "_get_task",
    "PUT": "_update_task",
    "PATCH": "_update_task",
    "DELETE": "_delete_task",
}


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class TaskServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, repository):
        super().__init__(address, ApiHandler)
        self.repository = repository


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "taskmgr"
    sys_version = ""

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_DELETE(self):
        self._dispatch("DELETE")

    @property
    def repo(self):
        return self.server.repository

    # ---- plumbing -----------------------------------------------------------

    def _dispatch(self, method):
        url = urlsplit(self.path)
        path = url.path.rstrip("/") or "/"
        self.query = parse_qs(url.query)
        try:
            handler, args = self._resolve(method, path)
            handler(*args)
        except ApiError as err:
            self._send_json(err.status, {"error": err.message})
        except ValidationError as err:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Validation failed", "details": err.details})
        except Exception:
            logger.exception("Unhandled error on %s %s", method, path)
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Internal server error"})

    def _resolve(self, method, path):
        match = TASK_DETAIL_PATH.match(path)
        if match:
            methods, args = DETAIL_ROUTES, (int(match.group(1)),)
        elif path in COLLECTION_ROUTES:
            methods, args = COLLECTION_ROUTES[path], ()
        else:
            raise ApiError(HTTPStatus.NOT_FOUND, "Not found")
        if method not in methods:
            raise ApiError(HTTPStatus.METHOD_NOT_ALLOWED, "Method not allowed")
        return getattr(self, methods[method]), args

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ApiError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length") from None
        if length <= 0:
            raise ApiError(HTTPStatus.BAD_REQUEST, "Request body is required")
        if length > MAX_BODY_BYTES:
            raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request body too large")
        try:
            return json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ApiError(HTTPStatus.BAD_REQUEST, "Invalid JSON body") from None

    def _send_json(self, status, payload=None):
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        if payload is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def log_message(self, format, *args):
        logger.info("%s - %s", self.address_string(), format % args)

    # ---- endpoints ----------------------------------------------------------

    def _health(self):
        try:
            self.repo.ping()
        except Exception as exc:
            logger.warning("Health check failed: %s", exc)
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "degraded", "database": "down"})
            return
        self._send_json(HTTPStatus.OK, {"status": "ok", "database": "up"})

    def _stats(self):
        self._send_json(HTTPStatus.OK, self.repo.stats())

    def _list_tasks(self):
        status = self.query.get("status", [None])[0]
        if status and status not in STATUSES:
            raise ApiError(HTTPStatus.BAD_REQUEST, f"status must be one of: {', '.join(STATUSES)}")
        self._send_json(HTTPStatus.OK, self.repo.list(status))

    def _create_task(self):
        fields = validate_task(self._read_json())
        self._send_json(HTTPStatus.CREATED, self.repo.create(fields))

    def _get_task(self, task_id):
        self._send_json(HTTPStatus.OK, self._require(self.repo.get(task_id)))

    def _update_task(self, task_id):
        fields = validate_task(self._read_json(), partial=True)
        self._send_json(HTTPStatus.OK, self._require(self.repo.update(task_id, fields)))

    def _delete_task(self, task_id):
        if not self.repo.delete(task_id):
            raise ApiError(HTTPStatus.NOT_FOUND, "Task not found")
        self._send_json(HTTPStatus.NO_CONTENT)

    @staticmethod
    def _require(task):
        if task is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "Task not found")
        return task


def main():
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    settings = Settings.from_env()
    server = TaskServer((settings.host, settings.port), MySQLTaskRepository(settings))

    # As PID 1 in a container, Python ignores SIGTERM unless a handler is installed.
    def _shutdown(signum, _frame):
        logger.info("Received signal %s, shutting down", signum)
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("Listening on %s:%s", settings.host, settings.port)
    with server:
        server.serve_forever()
    logger.info("Server stopped")


if __name__ == "__main__":
    main()
