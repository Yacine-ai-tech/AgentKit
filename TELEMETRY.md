# Telemetry & Privacy

This document describes exactly what AgentKit's code sends over the network for
telemetry purposes, and how to turn it off. No vague language — this is what the code
in `src/agentkit_mcp/web_app.py` actually does.

## What AgentKit's code sends

On startup of the web facade, a background thread (`web_app.py`, `_send_telemetry`)
sends **one HTTP POST**, at most once per ~6 hours per running instance:

```json
{"service": "AgentKit", "event": "startup", "instance_id": "<random 16-char hex string>"}
```

That's the entire payload. No database contents, KPI data, prompts, API keys, IP
addresses, or configuration are included by AgentKit's code.

- **Destination**: the `TELEMETRY_URL` env var. It defaults to **blank**, which disables
  telemetry entirely — no destination means no request is ever made. Set it yourself if
  you want to point AgentKit at your own collector.
- **`instance_id`**: a **randomly generated UUID** (`uuid.uuid4()`), created once and
  persisted to `logs/.telemetry_instance_id` (under `LOGS_DIR`), so repeat startups of the
  same install report the same ID (letting the receiving end de-duplicate) without that ID
  being derived from any hardware identifier — never a MAC address (`uuid.getnode()`) or
  any other hardware fingerprint. **Delete that file to reset it.**
- **Rate limiting**: `logs/.telemetry_last_ping` timestamps the last send; no ping is sent
  again within 6 hours of the last one.

## How to opt out

Two independent ways, either one is sufficient:

1. Set `TELEMETRY_OPT_OUT=true` in your `.env` (see `.env.example`). The background
   thread returns immediately and no HTTP request is made — not even a DNS lookup.
2. Leave `TELEMETRY_URL` blank (the default). With no destination configured, the code
   returns before making any request.

## What is NOT sent

- No database contents, KPI values, prompts, forecasts, or query results.
- No API keys, tokens, or `.env` contents.
- No IP address, hostname, or path information added by AgentKit's code (see above —
  AgentKit's *payload* contains only `service`, `event`, `instance_id`).
