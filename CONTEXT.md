# Chase Manager

A Keeper's tool for running Call of Cthulhu 7e chases at the table.

## Language

**Keeper**:
The person running the game and the only user of the app.
_Avoid_: Administrator, admin, GM

**Log entry**:
One line in the event log, a permanent record of something that happened in the chase.
_Avoid_: Message, history item

**Notification**:
Short-lived feedback on what the Keeper just did, including actions that were refused and why. It is never part of the event log.
_Avoid_: Toast, alert, popup

**Investigator**:
A player's character. Their player rolls their own dice, and the Keeper enters the result.
_Avoid_: PC, player (the player is the person, not the character)

**NPC**:
Any participant that isn't an investigator, including monsters and vehicles. The app rolls their dice.
_Avoid_: Enemy, mob

**DEX tie**:
Two or more participants with the same DEX, whose turn order still has to be settled by an opposed DEX roll or by the Keeper.
