# XDR MVP Starter

This project is a practical starting point for an Extended Detection and Response (XDR) service.

It includes:

- Telemetry ingestion API for multiple security sources.
- IOC management.
- Core detection rules (IOC match, auth brute-force, suspicious process behavior).
- Alert lifecycle management.
- Response action queueing for containment workflows.

## Architecture

- API Layer: FastAPI endpoints for events, alerts, and response actions.
- Orchestration Layer: `XDRService` coordinates ingestion, detection, alert lifecycle, and response workflows.
- Detection Layer: Pluggable rule engine with IOC match, brute-force, and suspicious-process rules.
- Persistence Layer: SQLite using SQLModel models.
- Response Layer: Queue response actions tied to alerts.

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the service:

```bash
uvicorn src.main:app --reload
```

4. Open API docs:

- http://127.0.0.1:8000/docs

5. Open the live dashboard:

- http://127.0.0.1:8000/dashboard

## Example Workflow

1. Add an IOC:

```bash
curl -X POST "http://127.0.0.1:8000/iocs" \
  -H "Content-Type: application/json" \
  -d '{
    "ioc_type": "domain",
    "value": "evil.example",
    "confidence": 90
  }'
```

2. Ingest an event that matches that IOC:

```bash
curl -X POST "http://127.0.0.1:8000/events" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "proxy",
    "host": "workstation-1",
    "event_type": "web_request",
    "severity": "medium",
    "details": {
      "url": "https://evil.example/payload"
    }
  }'
```

3. List alerts:

```bash
curl "http://127.0.0.1:8000/alerts"
```

4. Queue a response action for alert ID 1:

```bash
curl -X POST "http://127.0.0.1:8000/alerts/1/respond" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "isolate_host"
  }'
```

## Testing

Run:

```bash
pytest
```

## Next Improvements

- Add authentication and role-based access control.
- Integrate queue workers to execute response actions against real tools.
- Add streaming ingestion (Kafka or message bus).
- Expand detections with MITRE ATT&CK mapped techniques.
- Add asset and identity context enrichment.