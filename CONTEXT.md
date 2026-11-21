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

**Location**:
A place the chase passes through. Moving from one location to a connected one costs one movement action.
_Avoid_: Stop, node, space

**Connection**:
The way from one location forward to another. It holds at most one obstacle. A location with more than one outgoing connection is a fork, and one with more than one incoming connection is where routes rejoin.
_Avoid_: Gap, edge, link

**Obstacle**:
Anything on a connection that stands in a participant's way: a hazard or a barrier.

**Hazard**:
An obstacle you get past by attempting a skill roll. Failing costs you actions or damage, but you still get through.
_Avoid_: Using "hazard" to mean any obstacle

**Barrier**:
An obstacle that blocks you until you pass it or smash through. It has hit points.
_Avoid_: Using "hazard" to mean any obstacle

**Layout**:
The shape of a chase: its locations and the connections between them. Usually a straight line, sometimes forking into routes that rejoin or end separately. Never loops back.
_Avoid_: Track (when you mean the structure), map

**Branch**:
A route leaving a fork. Participants on different branches are still in the same chase, with one shared round and turn order.

**Round**:
One pass through the turn order, in which every participant gets a turn. Movement actions are refreshed at the start of each round.

**Turn**:
One participant's chance to act within a round, spending their movement actions on moving, obstacles or conflict.

**Turn order**:
The order participants take their turns in each round. It starts sorted by DEX, then changes through DEX tie rolls, the Keeper reordering by hand, and delays.
_Avoid_: DEX order (except to mean "sorted by DEX", as in DEX tie)
