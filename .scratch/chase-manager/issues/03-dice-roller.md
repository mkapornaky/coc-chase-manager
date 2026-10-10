# 03: Dice roller

**What to build:** The Keeper can roll for NPCs from the app. They can roll D100 against a value with 0–2 bonus or penalty dice and get the result level (Fumble / Failure / Regular / Hard / Extreme / Critical), and do quick NxDy rolls (1D3, 1D6, 2D10…). An NPC speed-roll button rolls against the participant's speed-roll value and applies the MOV adjustment. A monster skill fallback helper uses full, ½, or ⅕ of DEX (or another characteristic) as the target. Every roll is written to the event log. All randomness goes through an injectable random source.

**Blocked by:** 02 (Autosave, undo and event log)

**Status:** ready-for-agent

- [ ] D100 with bonus/penalty dice uses the correct tens die (lowest for bonus, highest for penalty)
- [ ] The result level follows the 7e thresholds, including fumble rules (96+ when the target is below 50, otherwise 100)
- [ ] NxDy rolls work for any count and size
- [ ] The NPC speed-roll button sets that participant's speed result
- [ ] The fallback helper offers full, ½, and ⅕ targets
- [ ] Every roll appears in the log with its inputs and result
- [ ] Tests use a seeded or fixed-sequence random source
