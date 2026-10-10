# Spec: CoC Chase Manager v1

Status: ready-for-agent

## Problem Statement

As a Call of Cthulhu 7th edition Keeper, running a chase at the table means juggling a lot of bookkeeping at once: speed rolls and adjusted MOV, who is placed where on a string of locations, how many movement actions each participant has (relative to the slowest participant), DEX order, movement-action debt carried between rounds, hazards and barriers between locations (with barrier hit points dropping), NPC dice rolls, vehicle build, and whose turn it is to call a sudden hazard. Doing this on paper slows the scene down and kills the tension a chase is supposed to create. Mistakes (forgetting debt, miscounting movement actions after someone joins) are easy and hard to notice.

## Solution

A small Keeper-only Python app (NiceGUI, running locally in a browser tab or as a native desktop window) that tracks a chase end to end according to the 7th edition chase rules. The Keeper preps chases ahead of time (locations, hazards/barriers, NPCs) as JSON files, loads a reusable party roster of investigators, and runs the chase from one screen. Players roll their own dice and the Keeper enters outcomes; the app rolls for NPCs, does the arithmetic, runs the turn order, and surfaces rule reminders as badges. It does not enforce rules: the Keeper can override any position, count, or order at any time. Every change is autosaved, undoable, and written to a readable event log.

## User Stories

### Prep and files

1. As a Keeper, I want to create a chase as a string of named locations with short read-aloud descriptions, so that I can describe the scene as characters move through it.
2. As a Keeper, I want to place a hazard or barrier between two adjacent locations, so that the track matches how the rules position obstacles.
3. As a Keeper, I want each hazard/barrier to record a name, type (hazard or barrier), suggested skill(s), difficulty (Regular/Hard/Extreme), and notes, so that I don't have to remember them mid-session.
4. As a Keeper, I want barriers to have current and maximum hit points, so that I can track characters or vehicles smashing through them.
5. As a Keeper, I want to add NPC and monster participants to a prepped chase with their stats, so that the chase is ready to run when the scene starts.
6. As a Keeper, I want to save a chase I built or tweaked in the app to the chases folder under a name, so that I can reuse it or prep in the app instead of a text editor.
7. As a Keeper, I want the app to list prepped chases from the chases folder in a dropdown, so that I can load one without a file picker.
8. As a Keeper, I want chase and party files to be plain, human-readable JSON, so that I can edit them by hand and keep them next to my scenario notes.
9. As a Keeper, I want to keep investigators in a separate party roster file, so that I don't retype the same characters for every chase.
10. As a Keeper, I want the app to list party rosters from the parties folder and add a roster's investigators to the current chase, so that setup takes seconds.
11. As a Keeper, I want to start a blank chase with no file, so that I can improvise when the players do something unexpected.
12. As a Keeper, I want to prep and run on the same screen, so that I can adjust a prepped chase in the middle of play without switching modes.

### Participants

13. As a Keeper, I want each participant to have a name, side (pursuer or fleeing), DEX, base MOV, and a speed-roll value (CON, or Drive Auto for drivers), so that the app can establish the chase.
14. As a Keeper, I want optional current/max HP on a participant, so that I can track hazard and attack damage without a separate sheet.
15. As a Keeper, I want to mark a participant as a vehicle with current/max build, so that vehicle damage and impairment are tracked.
16. As a Keeper, I want to mark a participant as a passenger in a specific vehicle, so that they act in DEX order but have no speed roll and no movement actions.
17. As a Keeper, I want a free-text notes field on each participant, so that I can jot down relevant skills or conditions.
18. As a Keeper, I want to edit any participant's fields during the chase, so that I can fix mistakes or apply changes the rules don't cover.
19. As a Keeper, I want to remove a participant who leaves the chase without recalculating anyone else's movement actions, so that the app follows the rule that leaving needs no recalculation.

### Establishing the chase (Part 1)

20. As a Keeper, I want the app to roll speed rolls for NPCs against their speed-roll value, so that I don't have to roll for every cultist.
21. As a Keeper, I want to enter each player's speed-roll result as Extreme / Success / Fail, so that players keep rolling their own dice.
22. As a Keeper, I want adjusted MOV to be base MOV +1 on an Extreme success, unchanged on a success, and −1 on a failure, for the whole chase, so that I don't do the math.
23. As a Keeper, I want pursuers slower than the slowest fleeing character dropped from the chase, so that the participant list matches the rules.
24. As a Keeper, I want fleeing characters faster than every pursuer flagged as "may escape", so that I can narrate the escape or let them stay.
25. As a Keeper, I want a one-on-one chase where the fleeing character is faster to be flagged as an escape with no chase played out, so that I can move the game on.

### Cut to the chase (Part 2)

26. As a Keeper, I want the app to place participants automatically: the slowest pursuer at the back, other pursuers ahead by their MOV difference, the slowest fleeing character 2 locations ahead of the foremost pursuer, and other fleeing characters ahead of the slowest one by their MOV difference, so that setup follows the multi-participant rules.
27. As a Keeper, I want to choose a starting range of 1 instead of 2, so that I can run a tenser chase in exceptional circumstances.
28. As a Keeper, I want to choose which prepped location the rearmost pursuer starts at, so that placement maps onto my location string.
29. As a Keeper, I want each participant's movement actions calculated as 1 plus the difference between their MOV and the slowest participant's MOV, so that faster characters get more actions.
30. As a Keeper, I want DEX order calculated highest to lowest, so that turns run in the right order.
31. As a Keeper, I want DEX ties flagged with a button to roll an opposed DEX roll for NPCs, or reorder by hand, so that ties are resolved per the rules.
32. As a Keeper, I want to adjust placement, movement actions, and order before round 1 starts, so that I can fit the result to the fiction.

### Running rounds (Parts 3–4)

33. As a Keeper, I want the app to highlight whose turn it is, in DEX order, so that I always know who acts next.
34. As a Keeper, I want to see each participant's movement actions remaining and total for the round, so that I know what they can still do.
35. As a Keeper, I want a "move" action that spends 1 movement action and advances the participant 1 location, so that clear-ground movement is one click.
36. As a Keeper, I want moving into a gap with a hazard to show the hazard's skill, difficulty, and notes, so that I can call for the right roll.
37. As a Keeper, I want to spend 1 or 2 movement actions for cautious bonus dice on a hazard roll, capped at 2, so that the cautious approach costs the right amount.
38. As a Keeper, I want to record a hazard roll as passed or failed, so that the outcome is logged.
39. As a Keeper, I want a failed hazard to let me roll or enter 1D3 lost movement actions and optional damage to HP or build, so that the penalty is applied correctly.
40. As a Keeper, I want the participant to move on to the next location after a hazard whether they pass or fail, so that hazards follow the rules.
41. As a Keeper, I want a barrier to block movement until it is passed or broken, so that barriers behave differently from hazards.
42. As a Keeper, I want to apply damage to a barrier's hit points (characters' damage, or 1D10 per point of build for vehicles), and have it stop being a barrier at 0 HP, so that smashing through is tracked.
43. As a Keeper, I want lost movement actions beyond what a participant has left this round carried as debt into the next round, so that I never forget a delay.
44. As a Keeper, I want a participant's debt shown on their token and in the turn panel, so that it's visible at a glance.
45. As a Keeper, I want an "attack" action that spends 1 movement action, so that initiating an attack costs the right amount.
46. As a Keeper, I want a "fighting maneuver succeeded against X" action that applies the hazard-failure outcome (1D3 lost actions, optional damage) to the target, so that trip/push maneuvers are tracked.
47. As a Keeper, I want an "other action" option (spell, picking a lock, firing while stopped) that spends 1 movement action with a free-text note, so that anything else can be logged.
48. As a Keeper, I want a participant to be able to delay their turn and act later, so that the delay rule is supported.
49. As a Keeper, I want an "end round" button that resets movement actions, subtracts debt, and starts the next round in DEX order, so that rounds advance cleanly.
50. As a Keeper, I want the round number shown, so that I can reference it in the log and for timed events.
51. As a Keeper, I want to directly set any participant's location, movement actions, or debt at any time, so that I can override the app when the fiction calls for it.
52. As a Keeper, I want moving past the last location to add a new blank location, so that the chase never runs off the map.
53. As a Keeper, I want a "roll random hazard" button on any gap (D100: 01–59 clear, 60+ Regular, 85+ Hard, 96+ Extreme, with an optional bonus or penalty die for the environment), so that I can generate terrain fairly.
54. As a Keeper, I want to add, edit, or remove locations and hazards during the chase, so that I can improvise.

### Joining mid-chase

55. As a Keeper, I want to add a participant mid-chase with a speed roll and place them on a location of my choice, so that latecomers can join.
56. As a Keeper, I want a joining pursuer whose MOV is below the slowest fleeing character flagged as unable to join, so that the rules are followed.
57. As a Keeper, I want everyone's movement actions recalculated when a new slowest participant joins, so that action counts stay correct.

### Vehicles and passengers

58. As a Keeper, I want to announce Pedal to the Metal for a vehicle's movement action (2–5 locations for 1 action), so that vehicles can accelerate.
59. As a Keeper, I want a badge showing "2–3 locations: 1 penalty die, 4–5: 2 penalty dice on hazards" when accelerating, so that I apply the right penalty.
60. As a Keeper, I want an accelerating vehicle that fails a hazard roll to stop at that hazard, so that the rule about stopping on a failed hazard is followed.
61. As a Keeper, I want a passenger who successfully navigates to reduce the vehicle's next Pedal to the Metal penalty by 1 die, so that navigation helps.
62. As a Keeper, I want an "impaired: 1 penalty die" badge when a vehicle's build is at half its starting value or less, so that I remember the penalty.
63. As a Keeper, I want an "undriveable" badge when a vehicle's build reaches 0, so that I know it's out of the chase.

### Flags and reminders

64. As a Keeper, I want a flag when a pursuer is on the same location as a fleeing character, so that I know an attack is possible.
65. As a Keeper, I want an indicator of whose turn it is to call a sudden hazard (Keeper or players), toggled when one is called, so that the alternation rule is tracked.
66. As a Keeper, I want an "end chase" button, so that I decide when the chase is over (escape, capture, hiding, losing the trail).

### Dice

67. As a Keeper, I want to roll D100 against a value with 0–2 bonus or penalty dice and get the result level (Fumble / Failure / Regular / Hard / Extreme / Critical), so that NPC rolls are quick.
68. As a Keeper, I want quick NxDy rolls (1D3, 1D6, 2D10, etc.), so that damage and lost actions are one click.
69. As a Keeper, I want a monster skill fallback helper that uses full, half, or one-fifth DEX (or another characteristic) as the target, so that monsters without listed skills can still roll.
70. As a Keeper, I want every roll written to the log with its result, so that I can show or check it later.

### Safety net

71. As a Keeper, I want the live chase autosaved to disk on every change, so that a crash or restart loses nothing.
72. As a Keeper, I want the app to resume the autosaved chase on startup, so that I can pick up where I left off.
73. As a Keeper, I want undo for the last action, repeatable, so that misclicks are harmless.
74. As a Keeper, I want a readable event log ("R2: Farmer moves 2 → loc 4", "Farmer fails hazard mud, −1D3 = −2 actions"), so that I can answer "what happened last round?"

### Layout and running

75. As a Keeper, I want the track shown as a horizontal, scrollable row of location cards with hazard/barrier chips between them and participant tokens on their locations, so that the chase reads like the rulebook's dot diagram.
76. As a Keeper, I want a side panel with DEX order, the current turn, movement actions left/total, debt, and badges, so that I can run the round without hunting.
77. As a Keeper, I want to run the app on my laptop as a browser tab or a native desktop window, so that it fits how I play.
78. As a Keeper, I want to open the app from a tablet on the same network, so that I'm not tied to the laptop.
79. As a Keeper, I want the UI in English with the rulebook's terms, so that it matches the book.

## Implementation Decisions

- **Stack:** Python 3.12+, managed with `uv` and a `pyproject.toml`. NiceGUI is the only runtime dependency; pytest is a dev dependency. The app runs either in browser mode or in NiceGUI's native mode (pywebview), which is the path to a desktop app.
- **Two modules:**
  - **Chase logic module:** pure Python dataclasses and functions with no UI imports. It owns all state and rules: participants, locations, hazards/barriers, setup (speed results, elimination, placement, movement actions, DEX order), turn flow, actions, debt, joining, vehicle and passenger rules, flags/badges, sudden-hazard alternation, dice, the event log, undo, and JSON serialization.
  - **UI module:** a thin NiceGUI layer that renders state and calls the logic module. No rules logic lives in the UI.
- **Chase interface (shape, not final names):** one `Chase` object exposing operations such as add/edit/remove participant, add/edit/remove location and hazard, apply speed result / roll NPC speed, establish (eliminate + place + compute actions and order), start round, move, spend cautious bonus dice, resolve hazard (pass/fail with lost actions and damage), damage barrier, attack, apply maneuver, other action, delay, pedal-to-the-metal move, join mid-chase, set overrides, end round, end chase, undo, to/from JSON. Derived values (movement actions, flags, badges, current turn) are computed from state, not stored redundantly.
- **Dice:** all randomness flows through an injected `random.Random`-compatible source (or a fixed roll sequence) passed to the chase. The UI uses a normal unseeded source.
- **Rule enforcement posture:** the app computes and reminds but never blocks. Every computed value has a Keeper override, and overrides are logged.
- **Undo:** snapshot the chase state before each mutating operation and keep a stack. Undo restores the previous snapshot. The log is part of the state, so undo also removes the log entry.
- **Persistence:**
  - The live chase is written to an autosave JSON file after every mutation and loaded on startup if present.
  - Prepped chases live in a chases folder and party rosters in a parties folder, both JSON, listed in dropdowns.
  - "Save as" writes the current chase's prep content (locations, hazards, NPCs) to the chases folder.
- **JSON shapes:**
  - A chase file contains locations (ordered; name, description), hazards keyed by the gap between locations, and NPC participants.
  - A party file contains investigator participants.
  - The autosave contains the full live state, including round, positions, debt, log, and the sudden-hazard caller.
  - Each file carries a version field so the format can evolve.
- **Positions:** participants sit on location indices along a single linear track. Hazards are attached to the gap between location *i* and *i+1*. Moving past the last index appends a blank location.
- **Movement actions:** 1 + (participant MOV − slowest non-passenger MOV), recomputed when a new slowest participant joins, and not recomputed when someone leaves. Passengers have 0 movement actions and one action per turn.
- **Vehicle rules covered:** MOV, build, impaired at ≤ half starting build (rounded down), undriveable at 0, Pedal to the Metal (2–3 locations = 1 penalty die, 4–5 = 2, stopping on a failed hazard), passenger navigation reducing the penalty by 1 die, and barrier damage of 1D10 per point of build.
- **Language:** English UI and log text, using rulebook terms (location, hazard, barrier, movement action, MOV, build, speed roll, pursuer, fleeing character).

## Testing Decisions

- **One seam:** the public interface of the chase logic module. Tests build a `Chase`, call its operations, and assert on observable state: positions, movement actions remaining and total, debt, DEX order, current turn, flags and badges, barrier HP, build, and log entries. No tests reach into private helpers.
- **Deterministic dice:** tests inject a seeded random source or a fixed roll sequence so NPC speed rolls, random hazards, and 1D3 penalties are reproducible.
- **Persistence tested at the same seam:** round-trip a chase through its JSON serialization and assert the state is equal. No separate file-format tests.
- **No UI tests:** the UI module is a thin layer over the logic module, and testing it costs more than it catches at this size.
- **The rulebook's worked examples are the main test cases:**
  - Harvey vs. farmer speed roll: Harvey Extreme (6→7), farmer fails (7→6), Harvey escapes and no chase is played.
  - The alternative: Harvey fails (MOV 5), farmer 6. The chase starts 2 locations apart, the farmer gets 2 movement actions to Harvey's 1, and Harvey (DEX 55) moves before the farmer (DEX 50). By the end of round 1 the gap is 1.
  - Mud hazard: the farmer fails, loses 1D3 = 1 action with none left, so he carries 1 debt into the next round and has 1 action that round.
  - Fence barrier: 5 HP, Harvey deals 3 and it drops to 2. Harvey stays on his location because the barrier still blocks.
  - Multi-participant placement: pursuers spaced by MOV difference, the slowest fleeing character 2 ahead of the foremost pursuer, the others spaced by MOV difference, a slower pursuer eliminated, a faster fleeing character flagged.
  - Joining mid-chase with a new slowest participant recalculates everyone's movement actions.
  - Police-car Pedal to the Metal: penalty badge at 2–3 and 4–5 locations, and stopping on a failed hazard.
  - Undo restores the previous state, including the log.
- **Prior art:** none, as this is a new repo. Use plain pytest functions without fixtures frameworks.

## Out of Scope

- Splitting up into multiple simultaneous chases (run a second chase instead).
- UI for hiding and escaping (Tracking or Spot Hidden judgments); the Keeper uses "end chase".
- The vehicular collision table (Table VI) and automatic collision damage; the Keeper enters damage.
- Switching movement modes (on foot ↔ swimming ↔ driving) as a dedicated feature; the Keeper edits MOV.
- Driver major-wound loss-of-control automation.
- A player-facing view or second screen.
- A portrait/vertical tablet layout.
- Rule enforcement that blocks Keeper actions.
- Full character sheets or skill lists beyond the listed fields.
- A built-in vehicle reference table picker.

## Further Notes

- Source rules: Call of Cthulhu 7th edition, chapter 7 (Chases), pp. 132–147. The PDF is in the repo root.
- The desktop path is NiceGUI native mode. Because the logic module has no UI dependencies, a later rewrite in another UI toolkit only replaces the UI module.
- The Keeper is the only user. The app runs on a trusted local machine or LAN, so there is no authentication.
