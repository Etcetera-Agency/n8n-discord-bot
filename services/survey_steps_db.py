from __future__ import annotations

from typing import Iterable, List, Dict, Any, Optional

from databases import Database


class SurveyStepsDB:
    """Asynchronous interface to the ``n8n_survey_steps_missed`` table."""

    def __init__(self, database_url: str, db: Optional[Database] = None) -> None:
        self.database_url = database_url
        self.db = db or Database(database_url)

    async def _connect(self) -> None:
        if not self.db.is_connected:
            await self.db.connect()

    async def close(self) -> None:
        if self.db.is_connected:
            await self.db.disconnect()

    async def upsert_step(self, session_id: str, step_name: str, completed: bool) -> Dict[str, str]:
        """Insert or update a step record for a session."""

        await self._connect()
        query = (
            "INSERT INTO n8n_survey_steps_missed (session_id, step_name, completed, updated) "
            "VALUES (:session_id, :step_name, :completed, CURRENT_TIMESTAMP) "
            "ON CONFLICT (session_id, step_name) DO UPDATE SET "
            "completed = excluded.completed, updated = excluded.updated"
        )
        await self.db.execute(query, {"session_id": session_id, "step_name": step_name, "completed": completed})
        return {"status": "ok"}

    async def fetch_week(self, session_id: str, week_start: Any) -> List[Dict[str, Any]]:
        """Return statuses for a session from the given week start."""

        await self._connect()

        params = {"session_id": session_id, "week_start": week_start}

        if self.database_url.startswith("postgres"):
            query = (
                "SELECT DISTINCT ON (step_name) step_name, completed, updated "
                "FROM n8n_survey_steps_missed "
                "WHERE session_id = :session_id AND updated >= :week_start "
                "ORDER BY step_name, updated DESC"
            )
        else:
            query = (
                "SELECT step_name, completed, updated FROM ("
                "SELECT step_name, completed, updated, "
                "ROW_NUMBER() OVER (PARTITION BY step_name ORDER BY updated DESC) AS rn "
                "FROM n8n_survey_steps_missed "
                "WHERE session_id = :session_id AND updated >= :week_start"
                ") AS ranked WHERE rn = 1 ORDER BY step_name"
            )

        rows = await self.db.fetch_all(query, params)
        return [dict(r) for r in rows]

    async def pending_steps(self, session_id: str, week_start: Any, all_steps: Iterable[str]) -> List[str]:
        """Return expected steps not completed for the current week."""

        records = await self.fetch_week(session_id, week_start)
        done = {r["step_name"] for r in records if r["completed"]}
        return [s for s in all_steps if s not in done]

