# 05: Barriers and track editing

**What to build:** The Keeper can add, edit, and remove locations (name, description) and hazards/barriers during play. A barrier (type = barrier, with current/max HP) blocks movement until it is passed or broken. The Keeper can apply damage to its HP, and at 0 HP it stops being a barrier. When someone moves past the last location, the app adds a blank location. A "roll random hazard" button on any gap rolls D100 (01–59 clear, 60+ Regular, 85+ Hard, 96+ Extreme), with an optional bonus or penalty die for the environment.

**Blocked by:** 04 (Hazards and movement-action debt)

**Status:** ready-for-agent

- [ ] Locations and hazards/barriers can be added, edited, and removed at any time
- [ ] An unpassed barrier keeps the participant on their location
- [ ] Barrier damage reduces HP; at 0 it is no longer a barrier
- [ ] Moving past the end appends a blank location
- [ ] The random hazard roll fills the gap with the rolled difficulty and logs the roll
- [ ] Test: fence example: 5 HP, Harvey deals 3, it drops to 2, and Harvey stays on his location
