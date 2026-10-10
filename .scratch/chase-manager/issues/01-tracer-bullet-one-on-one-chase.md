# 01: Tracer bullet: one-on-one chase on a blank track

**What to build:** The thinnest end-to-end chase. The Keeper launches the app (browser tab or native window), adds one pursuer and one fleeing character by hand (name, side, DEX, base MOV, speed-roll value), and enters each speed result (Extreme / Success / Fail). If the fleeing character's adjusted MOV is higher, the app flags an escape and no chase is played. Otherwise the app places the pursuer 2 locations behind the fleeing character on a rendered horizontal track. It shows each participant's movement actions (1 + MOV difference to the slowest) and DEX order, highlights whose turn it is, and lets the Keeper Move (spend 1 movement action, advance 1 location) and End round (reset movement actions, next round). This sets up the project skeleton (uv, pyproject, NiceGUI) and the split between the pure chase logic module and the thin UI module.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `uv run` starts the app in browser mode; a flag or option starts it in NiceGUI native mode
- [ ] The chase logic module has no UI imports
- [ ] Adjusted MOV is base +1 on Extreme, +0 on Success, −1 on Fail
- [ ] A faster fleeing character is flagged as escaped and no chase is placed
- [ ] Otherwise the participants are placed 2 locations apart, with enough locations created to show them
- [ ] Movement actions and DEX order (highest first) are computed and shown; the current turn is highlighted
- [ ] Move and End round work and the track re-renders
- [ ] Tests at the chase interface: Harvey Extreme (6→7) vs. farmer Fail (7→6) escapes; Harvey Fail (5) vs. farmer (6) starts 2 apart, farmer has 2 movement actions, Harvey (DEX 55) acts first, and the gap is 1 at the end of round 1
