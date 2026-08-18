# Changelog

## [0.1.11] - 2026-08-18
### Fixed
- Internal-token gate now checks the documented `X-AgentKit-Internal-Token` /
  `AGENTKIT_INTERNAL_TOKEN` and the documented `REQUIRE_INTERNAL_TOKEN` flag
  (default off), instead of an undocumented flag and a header/env var name
  that belonged to a different, private system.
- Session-scoped audit trail: `policy.py`'s `AuditRecord`/`audit_log()` and
  `pack_runtime.py`'s `call_pack_tool()` now accept a per-visitor session id
  so one browser session's tool-call history isn't visible to another.

## [0.1.3] - 2026-07-16
### Changed
- Standardized package structure and FastMCP integrations.
- Verified AGPL-3.0 compliance.
