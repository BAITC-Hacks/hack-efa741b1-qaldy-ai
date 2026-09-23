import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.domain.models import ActivityRecord
from app.domain.errors import ActivityAlreadyCompleted


@dataclass(frozen=True)
class StoredValidation:
    token: str
    package_hash: str
    payload: dict[str, Any]
    preview: dict[str, Any]
    expires_at: datetime


@dataclass(frozen=True)
class StoredApplyResult:
    batch_id: str
    package_hash: str
    inserted_employees: int
    inserted_history: int
    no_op_employees: int
    no_op_history: int
    idempotent_replay: bool = False


class SQLiteRepository:
    """Small stdlib-only persistence boundary for MVP overlay and imports."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._memory_connection: sqlite3.Connection | None = None
        if self.path == ":memory:":
            self._memory_connection = self._new_connection()
        self.initialize()

    def _new_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=10,
            isolation_level=None,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        if self.path != ":memory:":
            connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        if self._memory_connection is not None:
            yield self._memory_connection
            return
        connection = self._new_connection()
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS overlay_completions (
                    record_id TEXT PRIMARY KEY,
                    employee_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    activity_date TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status = 'completed'),
                    completion_pct INTEGER NOT NULL CHECK (completion_pct = 100),
                    assigned_by TEXT NOT NULL,
                    source TEXT NOT NULL CHECK (source = 'overlay'),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS completion_idempotency (
                    employee_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    record_id TEXT NOT NULL REFERENCES overlay_completions(record_id),
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (employee_id, event_id, idempotency_key)
                );
                CREATE INDEX IF NOT EXISTS idx_overlay_employee
                    ON overlay_completions(employee_id, activity_date, record_id);

                CREATE TABLE IF NOT EXISTS import_validations (
                    token TEXT PRIMARY KEY,
                    package_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    preview_json TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS import_batches (
                    batch_id TEXT PRIMARY KEY,
                    validation_token TEXT NOT NULL,
                    package_hash TEXT NOT NULL UNIQUE,
                    result_json TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS import_idempotency (
                    idempotency_key TEXT PRIMARY KEY,
                    package_hash TEXT NOT NULL,
                    batch_id TEXT NOT NULL REFERENCES import_batches(batch_id),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS imported_employees (
                    employee_id TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    batch_id TEXT NOT NULL REFERENCES import_batches(batch_id)
                );
                CREATE TABLE IF NOT EXISTS imported_activity_history (
                    record_id TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    batch_id TEXT NOT NULL REFERENCES import_batches(batch_id)
                );
                CREATE TABLE IF NOT EXISTS runtime_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                INSERT OR IGNORE INTO runtime_metadata (key, value)
                    VALUES ('dataset_revision', '0');
                """
            )
            completion_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(completion_idempotency)"
                ).fetchall()
            }
            if "result_json" not in completion_columns:
                connection.execute(
                    "ALTER TABLE completion_idempotency ADD COLUMN result_json TEXT"
                )

    def ping(self) -> None:
        """Raise when the configured database cannot serve a trivial query."""
        with self.connection() as connection:
            row = connection.execute("SELECT 1").fetchone()
        if row is None or row[0] != 1:
            raise RuntimeError("SQLite readiness query returned an unexpected result")

    def dataset_revision(self) -> int:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT value FROM runtime_metadata WHERE key = 'dataset_revision'"
            ).fetchone()
        if row is None:
            raise RuntimeError("Dataset revision metadata is missing")
        return int(row["value"])

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    def list_completion_records(self) -> tuple[ActivityRecord, ...]:
        with self.connection() as connection:
            rows = connection.execute(
                """SELECT record_id, employee_id, event_id, activity_date,
                          status, completion_pct, assigned_by, source
                   FROM overlay_completions
                   ORDER BY activity_date, record_id"""
            ).fetchall()
        return tuple(
            ActivityRecord(
                record_id=row["record_id"],
                employee_id=row["employee_id"],
                event_id=row["event_id"],
                activity_date=date.fromisoformat(row["activity_date"]),
                status=row["status"],
                completion_pct=row["completion_pct"],
                assigned_by=row["assigned_by"],
                source=row["source"],
            )
            for row in rows
        )

    def find_completion(
        self,
        employee_id: str,
        event_id: str,
        idempotency_key: str,
    ) -> ActivityRecord | None:
        with self.connection() as connection:
            row = connection.execute(
                """SELECT c.record_id, c.employee_id, c.event_id, c.activity_date,
                          c.status, c.completion_pct, c.assigned_by, c.source
                   FROM completion_idempotency i
                   JOIN overlay_completions c ON c.record_id = i.record_id
                   WHERE i.employee_id = ? AND i.event_id = ?
                     AND i.idempotency_key = ?""",
                (employee_id, event_id, idempotency_key),
            ).fetchone()
        return None if row is None else self._activity_from_row(row)

    def find_completion_snapshot(
        self,
        employee_id: str,
        event_id: str,
        idempotency_key: str,
    ) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                """SELECT result_json
                   FROM completion_idempotency
                   WHERE employee_id = ? AND event_id = ?
                     AND idempotency_key = ?""",
                (employee_id, event_id, idempotency_key),
            ).fetchone()
        if row is None or row["result_json"] is None:
            return None
        return json.loads(row["result_json"])

    def save_completion_snapshot(
        self,
        employee_id: str,
        event_id: str,
        idempotency_key: str,
        snapshot: dict[str, Any],
    ) -> None:
        encoded = json.dumps(
            snapshot,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        with self.connection() as connection:
            cursor = connection.execute(
                """UPDATE completion_idempotency
                   SET result_json = ?
                   WHERE employee_id = ? AND event_id = ?
                     AND idempotency_key = ?""",
                (encoded, employee_id, event_id, idempotency_key),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Completion idempotency record is missing")

    def record_completion(
        self,
        employee_id: str,
        event_id: str,
        activity_date: date,
        idempotency_key: str,
        repeatable: bool = False,
    ) -> tuple[ActivityRecord, bool]:
        """Insert once and return (record, is_replay), safe across processes."""
        now = self._utc_now().isoformat()
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                previous = connection.execute(
                    """SELECT c.record_id, c.employee_id, c.event_id, c.activity_date,
                              c.status, c.completion_pct, c.assigned_by, c.source
                       FROM completion_idempotency i
                       JOIN overlay_completions c ON c.record_id = i.record_id
                       WHERE i.employee_id = ? AND i.event_id = ?
                         AND i.idempotency_key = ?""",
                    (employee_id, event_id, idempotency_key),
                ).fetchone()
                if previous is not None:
                    connection.commit()
                    return self._activity_from_row(previous), True

                if not repeatable and connection.execute(
                    """SELECT 1 FROM overlay_completions
                       WHERE employee_id = ? AND event_id = ? LIMIT 1""",
                    (employee_id, event_id),
                ).fetchone() is not None:
                    raise ActivityAlreadyCompleted

                record = ActivityRecord(
                    record_id=f"OVL-{uuid.uuid4()}",
                    employee_id=employee_id,
                    event_id=event_id,
                    activity_date=activity_date,
                    status="completed",
                    completion_pct=100,
                    assigned_by="self",
                    source="overlay",
                )
                connection.execute(
                    """INSERT INTO overlay_completions
                       (record_id, employee_id, event_id, activity_date, status,
                        completion_pct, assigned_by, source, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record.record_id,
                        employee_id,
                        event_id,
                        activity_date.isoformat(),
                        record.status,
                        record.completion_pct,
                        record.assigned_by,
                        record.source,
                        now,
                    ),
                )
                connection.execute(
                    """INSERT INTO completion_idempotency
                       (employee_id, event_id, idempotency_key, record_id, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (employee_id, event_id, idempotency_key, record.record_id, now),
                )
                connection.commit()
                return record, False
            except Exception:
                connection.rollback()
                raise

    @staticmethod
    def _activity_from_row(row: sqlite3.Row) -> ActivityRecord:
        return ActivityRecord(
            record_id=row["record_id"],
            employee_id=row["employee_id"],
            event_id=row["event_id"],
            activity_date=date.fromisoformat(row["activity_date"]),
            status=row["status"],
            completion_pct=row["completion_pct"],
            assigned_by=row["assigned_by"],
            source=row["source"],
        )

    def save_validation(
        self,
        token: str,
        package_hash: str,
        payload: dict[str, Any],
        preview: dict[str, Any],
        expires_at: datetime,
    ) -> None:
        now = self._utc_now().isoformat()
        with self.connection() as connection:
            connection.execute(
                "DELETE FROM import_validations WHERE expires_at <= ?",
                (now,),
            )
            connection.execute(
                """INSERT INTO import_validations
                   (token, package_hash, payload_json, preview_json, expires_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    token,
                    package_hash,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    json.dumps(preview, ensure_ascii=False, sort_keys=True),
                    expires_at.isoformat(),
                    now,
                ),
            )

    def get_validation(self, token: str) -> StoredValidation | None:
        with self.connection() as connection:
            row = connection.execute(
                """SELECT token, package_hash, payload_json, preview_json, expires_at
                   FROM import_validations WHERE token = ?""",
                (token,),
            ).fetchone()
        if row is None:
            return None
        return StoredValidation(
            token=row["token"],
            package_hash=row["package_hash"],
            payload=json.loads(row["payload_json"]),
            preview=json.loads(row["preview_json"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
        )

    def apply_import(
        self,
        validation: StoredValidation,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> StoredApplyResult:
        """Apply validated rows atomically with no-op/reject-on-conflict semantics."""
        applied_at = now or self._utc_now()
        if validation.expires_at <= applied_at:
            raise ValueError("validation_token expired")
        employees = validation.payload.get(
            "apply_employees", validation.payload.get("employees", [])
        )
        history = validation.payload.get(
            "apply_history", validation.payload.get("history", [])
        )

        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                replay = connection.execute(
                    """SELECT b.result_json, b.batch_id, b.package_hash
                       FROM import_idempotency i
                       JOIN import_batches b ON b.batch_id = i.batch_id
                       WHERE i.idempotency_key = ?""",
                    (idempotency_key,),
                ).fetchone()
                if replay is not None:
                    if replay["package_hash"] != validation.package_hash:
                        raise ValueError("idempotency key already used for another package")
                    result_data = json.loads(replay["result_json"])
                    connection.commit()
                    return StoredApplyResult(
                        **result_data,
                        idempotent_replay=True,
                    )

                same_batch = connection.execute(
                    "SELECT result_json FROM import_batches WHERE package_hash = ?",
                    (validation.package_hash,),
                ).fetchone()
                if same_batch is not None:
                    result_data = json.loads(same_batch["result_json"])
                    connection.execute(
                        """INSERT INTO import_idempotency
                           (idempotency_key, package_hash, batch_id, created_at)
                           VALUES (?, ?, ?, ?)""",
                        (
                            idempotency_key,
                            validation.package_hash,
                            result_data["batch_id"],
                            applied_at.isoformat(),
                        ),
                    )
                    connection.commit()
                    return StoredApplyResult(**result_data, idempotent_replay=True)

                employee_actions = self._plan_rows(
                    connection,
                    "imported_employees",
                    "employee_id",
                    employees,
                )
                history_actions = self._plan_rows(
                    connection,
                    "imported_activity_history",
                    "record_id",
                    history,
                )
                batch_id = f"IMP-{uuid.uuid4()}"
                result_data = {
                    "batch_id": batch_id,
                    "package_hash": validation.package_hash,
                    "inserted_employees": sum(action[0] == "insert" for action in employee_actions),
                    "inserted_history": sum(action[0] == "insert" for action in history_actions),
                    "no_op_employees": sum(action[0] == "noop" for action in employee_actions)
                    + int(validation.payload.get("seed_no_op_employees", 0)),
                    "no_op_history": sum(action[0] == "noop" for action in history_actions)
                    + int(validation.payload.get("seed_no_op_history", 0)),
                }
                connection.execute(
                    """INSERT INTO import_batches
                       (batch_id, validation_token, package_hash, result_json, applied_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        batch_id,
                        validation.token,
                        validation.package_hash,
                        json.dumps(result_data, sort_keys=True),
                        applied_at.isoformat(),
                    ),
                )
                self._insert_planned_rows(
                    connection, "imported_employees", "employee_id", employee_actions, batch_id
                )
                self._insert_planned_rows(
                    connection,
                    "imported_activity_history",
                    "record_id",
                    history_actions,
                    batch_id,
                )
                connection.execute(
                    """INSERT INTO import_idempotency
                       (idempotency_key, package_hash, batch_id, created_at)
                       VALUES (?, ?, ?, ?)""",
                    (
                        idempotency_key,
                        validation.package_hash,
                        batch_id,
                        applied_at.isoformat(),
                    ),
                )
                if result_data["inserted_employees"] or result_data["inserted_history"]:
                    connection.execute(
                        """UPDATE runtime_metadata
                           SET value = CAST(value AS INTEGER) + 1
                           WHERE key = 'dataset_revision'"""
                    )
                connection.commit()
                return StoredApplyResult(**result_data)
            except Exception:
                connection.rollback()
                raise

    @staticmethod
    def _canonical_row(row: dict[str, Any]) -> tuple[str, str]:
        encoded = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        import hashlib

        return hashlib.sha256(encoded.encode("utf-8")).hexdigest(), encoded

    def _plan_rows(
        self,
        connection: sqlite3.Connection,
        table: str,
        id_column: str,
        rows: list[dict[str, Any]],
    ) -> list[tuple[str, str, str, str]]:
        planned: list[tuple[str, str, str, str]] = []
        for row in rows:
            external_id = str(row[id_column])
            content_hash, payload_json = self._canonical_row(row)
            existing = connection.execute(
                f"SELECT content_hash FROM {table} WHERE {id_column} = ?",
                (external_id,),
            ).fetchone()
            if existing is None:
                planned.append(("insert", external_id, content_hash, payload_json))
            elif existing["content_hash"] == content_hash:
                planned.append(("noop", external_id, content_hash, payload_json))
            else:
                raise ValueError(f"conflict: {id_column} {external_id} has different content")
        return planned

    @staticmethod
    def _insert_planned_rows(
        connection: sqlite3.Connection,
        table: str,
        id_column: str,
        actions: list[tuple[str, str, str, str]],
        batch_id: str,
    ) -> None:
        for action, external_id, content_hash, payload_json in actions:
            if action != "insert":
                continue
            connection.execute(
                f"INSERT INTO {table} ({id_column}, content_hash, payload_json, batch_id) "
                "VALUES (?, ?, ?, ?)",
                (external_id, content_hash, payload_json, batch_id),
            )

    def list_imported_employees(self) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM imported_employees ORDER BY employee_id"
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def list_imported_history(self) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM imported_activity_history ORDER BY record_id"
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]
