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

- **Destination**: `TELEMETRY_URL` env var, defaulting to the AgentKit project's own
  adoption-tracking endpoint (`https://gateway.ysiddo-ai-projects.app/telemetry`) — used
  to count roughly how many distinct installs of AgentKit are running, the same way many
  open-source CLIs (Homebrew, most package managers) report anonymous install counts home.
- **`instance_id`**: a **randomly generated UUID** (`uuid.uuid4()`), created once and
  persisted to `logs/.telemetry_instance_id` (under `LOGS_DIR`), so repeat startups of the
  same install report the same ID (letting the receiving end de-duplicate) without that ID
  being derived from any hardware identifier. **Delete that file to reset it.** Earlier
  versions of this code derived the ID from the machine's MAC address (`uuid.getnode()`) —
  that was changed because a hardware-derived ID doesn't rotate and is a stronger,
  non-consensual fingerprint than a locally-generated random ID needs to be for a simple
  install count.
- **Rate limiting**: `logs/.telemetry_last_ping` timestamps the last send; no ping is sent
  again within 6 hours of the last one.

## What you should know about the destination, honestly

Once this POST leaves your machine, it's a normal HTTP request — like any HTTP request to
any server, the receiving server's infrastructure sees the connecting IP address and
standard request metadata (user agent, etc.) as part of accepting the connection. That's
true of every network request ever made by every piece of software; it is not something
AgentKit's code adds on top of the payload above. If you don't want this instance making
that connection at all, use the opt-out below — no HTTP request is made, period.

## What is NOT sent

- No database contents, KPI values, prompts, forecasts, or query results.
- No API keys, tokens, or `.env` contents.
- No IP address, hostname, or path information added by AgentKit's code (see above —
  AgentKit's *payload* contains only `service`, `event`, `instance_id`).

## How to opt out

Set `TELEMETRY_OPT_OUT=true` in your `.env` (see `.env.example`). The background thread
returns immediately and no HTTP request is made — not even a DNS lookup.

You can also repoint the endpoint entirely via `TELEMETRY_URL` (e.g. to `http://localhost`
to make it a harmless local no-op, or to your own collector).

## README view pixel

`README.md` may include a 1×1 tracking pixel to count repository page views on GitHub —
unrelated to the code above. Remove the `<img>` tag from your fork's `README.md` to
disable it.
