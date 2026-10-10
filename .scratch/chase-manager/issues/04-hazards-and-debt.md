# 04: Hazards and movement-action debt

**What to build:** The Keeper can place a hazard in the gap between two locations (name, suggested skill(s), difficulty, notes) and see it as a chip on the track. When a participant moves into that gap, the app shows the hazard. The Keeper can spend 1–2 movement actions on cautious bonus dice (max 2), then record pass or fail. On a failure, 1D3 movement actions are lost (rolled or entered), with optional HP damage. The participant moves on to the next location either way. Lost actions beyond what's left this round carry as debt into the next round, shown on the token and in the side panel. Participants gain optional current/max HP.

**Blocked by:** 01 (Tracer bullet: one-on-one chase on a blank track), 03 (Dice roller)

**Status:** ready-for-agent

- [ ] Hazards can be added to a gap and render as chips between location cards
- [ ] Bonus dice cost 1 movement action each, capped at 2
- [ ] Pass or fail moves the participant to the next location
- [ ] On a fail, 1D3 lost actions are applied, excess becomes debt, and debt is subtracted at the start of the next round
- [ ] Optional HP damage is applied and shown
- [ ] All of it is logged and undoable
- [ ] Test: mud example: the farmer fails with 0 actions left, loses 1, and has 1 movement action next round
