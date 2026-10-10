# 08: Joining and leaving mid-chase

**What to build:** The Keeper can add a participant to a running chase with a speed roll and place them on a chosen location. A joining pursuer whose MOV is below the slowest fleeing character is flagged as unable to join. If the newcomer is the new slowest participant, everyone's movement actions are recalculated. Removing a participant does not recalculate anything.

**Blocked by:** 06 (Multi-participant setup)

**Status:** ready-for-agent

- [ ] Join takes a speed result and a location
- [ ] A too-slow joining pursuer is flagged
- [ ] A new slowest participant triggers recalculation for all participants
- [ ] Leaving never recalculates
- [ ] Tests for recalculation on join and no recalculation on leave
