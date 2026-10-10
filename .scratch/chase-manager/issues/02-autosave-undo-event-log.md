# 02: Autosave, undo and event log

**What to build:** A safety net for the live chase. Every change is autosaved to a JSON file, and the app resumes it on startup. The Keeper can undo the last action repeatedly. A readable event log panel shows what happened (e.g. "R2: Farmer moves 2 → loc 4"). The full chase state, including round, positions, debt, and log, serializes to and from versioned JSON.

**Blocked by:** 01 (Tracer bullet: one-on-one chase on a blank track)

**Status:** ready-for-agent

- [ ] Every mutating operation writes the autosave file
- [ ] On startup, an existing autosave is loaded and the chase resumes exactly where it was
- [ ] Undo restores the state before the last operation, can be repeated, and removes that log entry
- [ ] Every mutating operation writes a human-readable log line, tagged with the round number
- [ ] The JSON includes a format version field
- [ ] Tests: a JSON round trip gives an equal state; undo after a move restores the position and the log
