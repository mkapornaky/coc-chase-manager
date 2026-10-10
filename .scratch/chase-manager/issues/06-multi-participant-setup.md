# 06: Multi-participant setup

**What to build:** Establishing a chase with any number of pursuers and fleeing characters. After speed results, pursuers slower than the slowest fleeing character are dropped, and fleeing characters faster than every pursuer are flagged "may escape". Placement: the slowest pursuer goes at the back (on a Keeper-chosen location), other pursuers go ahead by their MOV difference, the slowest fleeing character goes 2 ahead of the foremost pursuer (1 as an option), and other fleeing characters go ahead of the slowest one by their MOV difference. DEX ties are flagged, with an opposed DEX roll button or manual reordering. The Keeper can adjust placement, movement actions, and order before round 1. A flag shows when a pursuer is on the same location as a fleeing character.

**Blocked by:** 01 (Tracer bullet: one-on-one chase on a blank track), 03 (Dice roller)

**Status:** ready-for-agent

- [ ] Elimination and the "may escape" flag follow the multi-participant rules
- [ ] Placement matches the rules, with a range 1/2 option and a chosen start location
- [ ] DEX ties are flagged and resolvable by an opposed roll or a manual reorder
- [ ] Pre-round-1 adjustments are possible and logged
- [ ] The same-location flag appears whenever a pursuer shares a location with a fleeing character
- [ ] Tests: a mixed group places correctly, the slow pursuer is dropped, and the fast fleeing character is flagged
