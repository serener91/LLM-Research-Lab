from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from agents import Agent, Runner, set_tracing_disabled
from fastapi import FastAPI
from pydantic import BaseModel

set_tracing_disabled(disabled=True)

app = FastAPI(title="Parkie Agentic Ops API", version="0.1.0")


class MissionRequest(BaseModel):
    mission_id: str
    mission_type: str
    vehicle_plate: str
    priority: int = 2


class EventIn(BaseModel):
    mission_id: str
    robot_id: str
    severity: str
    event_type: str
    error_code: str = ""
    payload: dict[str, Any] = {}


orchestrator = Agent(
    name="request_orchestrator",
    instructions=(
        "You orchestrate parking robot missions. Always produce short JSON with"
        " action, rationale, and next_state. Respect safety-first policies."
    ),
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "ts_utc": datetime.now(UTC).isoformat()}


@app.post("/missions")
async def create_mission(req: MissionRequest) -> dict[str, Any]:
    prompt = (
        f"mission_id={req.mission_id}, mission_type={req.mission_type}, "
        f"vehicle_plate={req.vehicle_plate}, priority={req.priority}. "
        "Return next operational step."
    )
    result = await Runner.run(orchestrator, prompt)
    return {"received": req.model_dump(), "agent_output": result.final_output}


@app.post("/events")
def ingest_event(evt: EventIn) -> dict[str, Any]:
    retry = evt.error_code in {"NAV_BLOCKED", "DB_TIMEOUT", "ELEV_TIMEOUT"}
    return {
        "accepted": True,
        "mission_id": evt.mission_id,
        "ts_utc": datetime.now(UTC).isoformat(),
        "recommended_action": "retry" if retry else "escalate",
    }
