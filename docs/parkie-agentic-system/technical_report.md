# Agentic Log-Driven Parking Operations System (PARKIE-like)

## 1) Product investigation summary (HL Robotics PARKIE)

Based on HL Robotics public product pages, PARKIE is positioned as an **indoor autonomous parking robot** that:
- Navigates independently in indoor parking facilities.
- Detects obstacles/open spaces/driving paths.
- Lifts vehicles by identifying wheel spacing and vehicle center.
- Targets space efficiency claims (up to ~30% more parking capacity) in converted structures.

Sources used for this investigation:
- https://www.hlrobotics.co.kr/parkie
- https://en.hlrobotics.co.kr/parkie
- https://en.hlrobotics.co.kr/News/?bmode=view&idx=167557796

> Note: This report uses publicly available marketing-level information and builds a realistic engineering scenario around it, not internal proprietary implementation details.

---

## 2) Scenario definition (realistic operations)

### Site profile
- Facility: mixed-use tower parking hub (B2~B6), 620 vehicle capacity.
- Fleet: 28 parking robots (R001~R028), 2 charging zones per floor.
- Hours: 24/7, with peak periods 07:30–09:30 and 17:30–20:30 local time.
- Interfaces:
  - Kiosk + mobile app for request intake.
  - License plate OCR + wheel-position sensors at handoff bays.
  - Lift/elevator coordination for multi-level movement.

### User journeys
1. **Park vehicle**:
   - User enters bay, confirms plate and destination policy.
   - Agent system creates a `PARK` mission and dispatches a robot.
   - Robot picks vehicle, routes to assigned slot, confirms parked state.

2. **Fetch vehicle**:
   - User requests retrieval via app/kiosk ETA target.
   - System creates `FETCH` mission, robot retrieves and delivers to pickup bay.

### Failure scenarios to handle
- Sensor mismatch (plate vs wheel geometry mismatch).
- Navigation blockage (temporary aisle obstacle).
- Elevator timeout / floor transfer failure.
- Robot low battery before mission completion.
- Database write latency causing stale mission state.
- Lost robot heartbeat.

---

## 3) Agentic architecture

### Core agents
1. **Request Orchestrator Agent**
   - Interprets user intent (`PARK`, `FETCH`, `CANCEL`).
   - Creates mission objects and state machine entries.

2. **Dispatch & Routing Agent**
   - Selects robot based on proximity, battery, load, health.
   - Plans route with floor and elevator constraints.

3. **Fault Recovery Agent**
   - Consumes system logs/events.
   - Executes retries and fallback policy:
     - retry navigation up to N times,
     - reassign robot,
     - escalate to human operator,
     - trigger safe-hold.

4. **Customer Comms Agent**
   - Sends ETA updates and incident notifications.
   - Issues SLA apology credits when thresholds breached.

5. **Ops Reporting Agent**
   - Produces hourly/daily incident and utilization reports.

### State machine (mission)
`RECEIVED -> VALIDATED -> ASSIGNED -> ENROUTE_PICKUP -> LIFTING -> ENROUTE_DROP -> COMPLETED`

Failure branches:
- `FAILED_RETRYABLE` (auto retry)
- `FAILED_ESCALATED` (human intervention)
- `CANCELLED`

---

## 4) Observability and log strategy

### Log event envelope
Each event should include:
- `event_id`, `ts_utc`, `site_id`, `mission_id`, `robot_id`
- `agent_name`, `severity`, `event_type`, `error_code`
- `payload` (JSON), `trace_id`, `span_id`

### Error taxonomy
- `SENSOR_*`: perception and calibration
- `NAV_*`: motion planning and obstacle handling
- `ELEV_*`: inter-floor transfer
- `BAT_*`: power and charging
- `DB_*`: persistence and consistency
- `NET_*`: connectivity and heartbeat

### Retry policy example
- `NAV_BLOCKED`: exponential backoff (2s, 5s, 10s), max 3 attempts.
- `ELEV_TIMEOUT`: retry once, then re-route to alternate elevator.
- `DB_TIMEOUT`: write-through queue with idempotency key.

---

## 5) Proposed tech implementation

- **Python 3.12+** with **uv** for dependency and environment management.
- **openai-agents >= 0.12.5** for agent orchestration.
  - Must disable built-in tracing:
    ```python
    from agents import set_tracing_disabled
    set_tracing_disabled(disabled=True)
    ```
- **fastmcp >= 3.1.1** to expose robot-control and diagnostics tool endpoints.
- **PostgreSQL 16** for mission/event persistence.
- **FastAPI** for API ingress (`/missions`, `/events`, `/health`, `/ops/report`).
- **langfuse >= 4.0.6 (Cloud)** for observability and prompt/agent traces.
- **Docker + Docker Compose** for deployment and local integration environment.

---

## 6) Data model (high level)

### `missions`
- `mission_id` (PK), `mission_type`, `status`, `site_id`, `vehicle_plate`
- `requested_at`, `assigned_robot_id`, `priority`, `eta_seconds`

### `robot_status`
- `robot_id` (PK), `floor`, `battery_pct`, `state`, `last_heartbeat`
- `current_mission_id`, `health_score`

### `system_events`
- `event_id` (PK), `ts_utc`, `mission_id`, `robot_id`, `severity`
- `event_type`, `error_code`, `payload_json`, `resolved`

### `incident_reports`
- `incident_id`, `opened_at`, `closed_at`, `root_cause`, `action_taken`
- `sla_impact_seconds`, `customer_notified`

---

## 7) Mock dataset scope and realism choices

Provided mock data includes:
- 50 mission rows with mixed PARK/FETCH demand.
- 12 robots with realistic battery and health spreads.
- 300+ chronological event logs with:
  - normal flow transitions,
  - intermittent retries,
  - escalated failures,
  - operator interventions.

Realism assumptions:
- Peak-time fetch demand spikes.
- Low battery correlated with higher failure probability.
- Elevator-related failures concentrated at inter-floor transfers.
- Retries often recover navigation faults but less so for sensor mismatch.

---

## 8) Improvement roadmap

1. Add simulation harness for Monte Carlo failure injection.
2. Introduce policy-learning loop from historical incidents.
3. Add digital twin for garage topology and congestion prediction.
4. Add cost model (energy, wait time, robot wear) for optimized dispatch.
5. Define safety case artifacts for ISO 3691-4 / operational risk review.

