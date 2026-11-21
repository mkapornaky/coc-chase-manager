# Chase layout is a forward-only graph with a main route

Chases are usually a straight line, but some fork into branches that rejoin or end separately, so a layout is a set of locations joined by connections that only point forward (no loops), each connection holding at most one obstacle. We ruled out loops because they make "ahead" and "behind" meaningless and no chase we know of needs them; we ruled out a tree because routes must be able to rejoin. The first exit at each fork is the main route, so the opening placement at the start of the chase can still run along a line.

## Consequences

- Obstacles belong to connections, not locations (version 3 files kept them as a location's `hazard_after`; they are converted on load).
- A participant's position is a location, not a distance along the line; the way out of a fork is chosen when moving, before any obstacle is resolved.
- Moving more than one location in one go (Pedal to the Metal) stops at a fork, as it stops at an obstacle.
