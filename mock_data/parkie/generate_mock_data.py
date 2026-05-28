from __future__ import annotations

import csv
import json
import random
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

random.seed(42)

OUT_DIR = Path(__file__).parent


@dataclass
class Mission:
    mission_id: str
    mission_type: str
    status: str
    site_id: str
    vehicle_plate: str
    requested_at: str
    assigned_robot_id: str
    priority: int
    eta_seconds: int


@dataclass
class RobotStatus:
    robot_id: str
    floor: str
    battery_pct: float
    state: str
    last_heartbeat: str
    current_mission_id: str
    health_score: float


def plate() -> str:
    return f"{random.randint(10, 99)}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.randint(1000,9999)}"


def build_missions(start: datetime, n: int = 50) -> list[Mission]:
    rows: list[Mission] = []
    for i in range(1, n + 1):
        mission_type = "FETCH" if random.random() < 0.55 else "PARK"
        requested = start + timedelta(seconds=i * random.randint(45, 140))
        rid = f"R{random.randint(1,12):03d}"
        rows.append(
            Mission(
                mission_id=f"M{i:05d}",
                mission_type=mission_type,
                status=random.choice(["COMPLETED", "COMPLETED", "FAILED_RETRYABLE", "FAILED_ESCALATED"]),
                site_id="SEOUL_TOWER_B",
                vehicle_plate=plate(),
                requested_at=requested.isoformat(),
                assigned_robot_id=rid,
                priority=random.choice([1, 1, 2, 3]),
                eta_seconds=random.randint(120, 700),
            )
        )
    return rows


def build_robots(start: datetime) -> list[RobotStatus]:
    rows: list[RobotStatus] = []
    for i in range(1, 13):
        rid = f"R{i:03d}"
        rows.append(
            RobotStatus(
                robot_id=rid,
                floor=random.choice(["B2", "B3", "B4", "B5", "B6"]),
                battery_pct=round(random.uniform(18, 99), 1),
                state=random.choice(["IDLE", "BUSY", "CHARGING", "RECOVERY"]),
                last_heartbeat=(start + timedelta(seconds=random.randint(0, 12))).isoformat(),
                current_mission_id=random.choice(["", f"M{random.randint(1,50):05d}"]),
                health_score=round(random.uniform(0.81, 0.99), 3),
            )
        )
    return rows


def build_events(missions: list[Mission]) -> list[dict]:
    events = []
    eid = 1
    err_pool = [
        ("NAV_BLOCKED", "WARN"),
        ("ELEV_TIMEOUT", "ERROR"),
        ("SENSOR_WHEEL_MISMATCH", "ERROR"),
        ("DB_TIMEOUT", "WARN"),
        ("BAT_LOW", "WARN"),
    ]
    for m in missions:
        t0 = datetime.fromisoformat(m.requested_at)
        flow = [
            "MISSION_RECEIVED",
            "MISSION_VALIDATED",
            "ROBOT_ASSIGNED",
            "ENROUTE_PICKUP",
            "LIFTING_VEHICLE",
            "ENROUTE_DROP",
        ]
        for step in flow:
            events.append(
                {
                    "event_id": f"E{eid:06d}",
                    "ts_utc": (t0 + timedelta(seconds=eid % 37)).isoformat(),
                    "site_id": m.site_id,
                    "mission_id": m.mission_id,
                    "robot_id": m.assigned_robot_id,
                    "agent_name": random.choice([
                        "request_orchestrator",
                        "dispatch_routing",
                        "fault_recovery",
                        "customer_comms",
                    ]),
                    "severity": "INFO",
                    "event_type": step,
                    "error_code": "",
                    "payload": {"attempt": 1, "note": "state transition"},
                }
            )
            eid += 1

        if m.status != "COMPLETED":
            err, sev = random.choice(err_pool)
            events.append(
                {
                    "event_id": f"E{eid:06d}",
                    "ts_utc": (t0 + timedelta(seconds=eid % 53)).isoformat(),
                    "site_id": m.site_id,
                    "mission_id": m.mission_id,
                    "robot_id": m.assigned_robot_id,
                    "agent_name": "fault_recovery",
                    "severity": sev,
                    "event_type": "MISSION_EXCEPTION",
                    "error_code": err,
                    "payload": {"retry_scheduled": m.status == "FAILED_RETRYABLE", "max_retries": 3},
                }
            )
            eid += 1

        events.append(
            {
                "event_id": f"E{eid:06d}",
                "ts_utc": (t0 + timedelta(seconds=eid % 67)).isoformat(),
                "site_id": m.site_id,
                "mission_id": m.mission_id,
                "robot_id": m.assigned_robot_id,
                "agent_name": "ops_reporting",
                "severity": "INFO" if m.status == "COMPLETED" else "WARN",
                "event_type": "MISSION_FINALIZED",
                "error_code": "" if m.status == "COMPLETED" else "FINAL_WITH_ISSUE",
                "payload": {"final_status": m.status},
            }
        )
        eid += 1
    return events


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    start = datetime(2026, 5, 20, 7, 30, tzinfo=UTC)
    missions = build_missions(start)
    robots = build_robots(start)
    events = build_events(missions)

    write_csv(OUT_DIR / "missions.csv", [asdict(m) for m in missions])
    write_csv(OUT_DIR / "robot_status.csv", [asdict(r) for r in robots])
    write_csv(
        OUT_DIR / "system_events.csv",
        [{**e, "payload": json.dumps(e["payload"], ensure_ascii=False)} for e in events],
    )


if __name__ == "__main__":
    main()
