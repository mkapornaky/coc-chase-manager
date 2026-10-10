# 10: Vehicles and passengers

**What to build:** Car chases. A participant can be a vehicle with current/max build, showing an "impaired: 1 penalty die" badge at half its starting build or less (rounded down) and "undriveable" at 0. Pedal to the Metal is announced before moving and moves 2–5 locations for 1 movement action, with a penalty badge (2–3 locations = 1 penalty die, 4–5 = 2 on hazards). The vehicle stops at a hazard it fails. Vehicles damage barriers by 1D10 per point of build. Passengers are flagged as "passenger in <vehicle>", make no speed roll, have 0 movement actions, act once in DEX order, and can navigate (a successful Spot Hidden or Navigate roll reduces the next Pedal to the Metal penalty by 1 die).

**Blocked by:** 05 (Barriers and track editing), 07 (Conflict and other actions)

**Status:** ready-for-agent

- [ ] Vehicle build is tracked; the impaired and undriveable badges appear at the right thresholds
- [ ] Pedal to the Metal moves the announced distance and shows the correct penalty
- [ ] A failed hazard during acceleration stops the vehicle; further movement costs a new action
- [ ] Vehicle barrier damage rolls 1D10 per build point
- [ ] Passengers have no speed roll or movement actions but get a turn in DEX order
- [ ] Navigation reduces the next acceleration penalty by 1 die
- [ ] Movement actions ignore passengers when finding the slowest participant
- [ ] Test: police-car example: penalty badges and stopping on the failed hazard
