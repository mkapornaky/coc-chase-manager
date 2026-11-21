"""Pure chase logic (CoC 7e, chapter 7). No UI imports."""

import functools
import json
import random
from dataclasses import asdict, dataclass, field, fields, replace
from enum import StrEnum
from pathlib import Path

FORMAT_VERSION = 3
READABLE_VERSIONS = (1, 2, FORMAT_VERSION)  # 1: hazards kept apart; 2: Chase.investigators list



def mutation(fn):
    """Wrap every state-changing Chase method: snapshot for undo, run, autosave.

    The method itself writes its log entries with self.log_event(...); they are kept in
    last_entries so the UI can show them. Nested calls (a mutation calling another,
    e.g. a dice roll) share the outer snapshot and entries.
    """
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        if self._in_mutation:
            return fn(self, *args, **kwargs)
        snapshot = self.to_json()
        self.last_entries = []
        self._in_mutation = True
        try:
            result = fn(self, *args, **kwargs)
        finally:
            self._in_mutation = False
        self._forget_stale_ties()
        self.history.append((snapshot, self.last_entries))
        self.save()
        return result
    return wrapper


class Side(StrEnum):
    PURSUER = "pursuer"
    FLEEING = "fleeing"


class SpeedResult(StrEnum):
    EXTREME = "extreme"
    SUCCESS = "success"
    FAIL = "fail"


class HazardKind(StrEnum):
    HAZARD = "hazard"
    BARRIER = "barrier"  # blocks until passed or broken


class Difficulty(StrEnum):
    REGULAR = "regular"
    HARD = "hard"
    EXTREME = "extreme"


class Caller(StrEnum):
    """Who may call the next sudden hazard."""
    KEEPER = "keeper"
    PLAYERS = "players"


def _optional(enum, value):
    return None if value is None else enum(value)


SPEED_MOD = {SpeedResult.EXTREME: 1, SpeedResult.SUCCESS: 0, SpeedResult.FAIL: -1}
# D100 result level -> speed result
SPEED_FROM_LEVEL = {"critical": SpeedResult.EXTREME, "extreme": SpeedResult.EXTREME, "hard": SpeedResult.SUCCESS,
                    "regular": SpeedResult.SUCCESS, "failure": SpeedResult.FAIL, "fumble": SpeedResult.FAIL}
LEVELS = list(SPEED_FROM_LEVEL)  # best first
PEDAL_DISTANCES = range(2, 6)  # Pedal to the Metal: 2-5 locations


def success_level(roll: int, target: int) -> str:
    """7e result level of a D100 roll against target."""
    if roll == 1:
        return "critical"
    if roll == 100 or (target < 50 and roll >= 96):
        return "fumble"
    if roll <= target // 5:
        return "extreme"
    if roll <= target // 2:
        return "hard"
    return "regular" if roll <= target else "failure"


def default_location_name(index: int) -> str:
    return f"Location {index + 1}"


def fallback_targets(value: int) -> dict[str, int]:
    """Monster skill fallback: full, half or one-fifth of a characteristic (e.g. DEX)."""
    return {"full": value, "half": value // 2, "fifth": value // 5}


def _dice(n: int, kind: str) -> str:
    return f"{n} {kind} {'die' if n == 1 else 'dice'}"


@dataclass
class Hazard:
    """Obstacle between a location and the next one (that location's hazard_after)."""
    name: str
    skill: str = ""  # suggested skill(s), free text
    difficulty: Difficulty = Difficulty.REGULAR
    notes: str = ""
    kind: HazardKind = HazardKind.HAZARD
    hp: int | None = None  # barriers only
    max_hp: int | None = None

    def __post_init__(self):  # values loaded from JSON arrive as plain strings
        self.difficulty = Difficulty(self.difficulty)
        self.kind = HazardKind(self.kind)


@dataclass
class Location:
    name: str
    description: str = ""  # read-aloud text
    hazard_after: Hazard | None = None  # between this location and the next

    @classmethod
    def from_dict(cls, data: dict) -> "Location":
        hazard = data.get("hazard_after")
        return cls(str(data["name"]), data.get("description", ""), Hazard(**hazard) if hazard else None)


def locations_from_v1(locations: list[dict], hazards: dict) -> list[Location]:
    """Version 1 kept hazards apart, keyed by gap index (gap i = after location i)."""
    by_gap = {int(i): h for i, h in hazards.items()}
    return [Location.from_dict(loc | {"hazard_after": by_gap.get(i)}) for i, loc in enumerate(locations)]


@dataclass
class Participant:
    name: str
    side: Side
    dex: int
    mov: int
    speed_value: int
    speed_result: SpeedResult | None = None
    location: int = 0  # index into Chase.locations
    actions_left: int = 0
    debt: int = 0  # lost movement actions carried into the next round
    hp: int | None = None
    max_hp: int | None = None
    build: int | None = None  # vehicles only
    max_build: int | None = None
    pedal: int = 0  # Pedal to the Metal locations still to travel (stopped at a hazard)
    pedal_penalty: int = 0  # penalty dice on hazards during that acceleration
    navigated: bool = False  # a passenger navigated: next Pedal to the Metal has 1 penalty die less
    vehicle: str | None = None  # passenger in this vehicle: no speed roll, rides along, 1 action
    passenger_action: bool = False  # passengers only: this round's one action is still unused
    notes: str = ""  # Keeper's free text: skills, conditions
    investigator: bool = False  # a player's character: never saved as an NPC, players roll their own dice

    def __post_init__(self):  # values loaded from JSON arrive as plain strings
        self.side = Side(self.side)
        self.speed_result = _optional(SpeedResult, self.speed_result)

    @property
    def is_vehicle(self) -> bool:
        return self.build is not None

    @property
    def is_passenger(self) -> bool:
        return self.vehicle is not None

    @property
    def adjusted_mov(self) -> int:
        return self.mov + SPEED_MOD.get(self.speed_result, 0)


@dataclass
class Chase:
    participants: list[Participant] = field(default_factory=list)
    locations: list[Location] = field(default_factory=list)
    escaped: list[str] = field(default_factory=list)
    may_escape: list[str] = field(default_factory=list)
    unable_to_join: list[str] = field(default_factory=list)  # pursuers too slow to join mid-chase
    left_behind: list[Participant] = field(default_factory=list)  # dropped at establish; still saved as prep
    order: list[str] = field(default_factory=list)  # Keeper turn order; empty = by DEX
    round: int = 0  # 0 = not established yet
    slowest_mov: int = 0
    delayed: list[str] = field(default_factory=list)  # this round only, acting after everyone else
    sudden_caller: Caller | None = None  # None = either side may call the next sudden hazard
    ended: bool = False
    resolved_ties: list[list[str]] = field(default_factory=list)  # DEX ties settled, by exact membership
    log:list[str] = field(default_factory=list)
    # Not state (compare=False): excluded from JSON, equality and undo snapshots.
    history: list[tuple[str, list[str]]] = field(default_factory=list, repr=False, compare=False)
    last_entries: list[str] = field(default_factory=list, repr=False, compare=False)  # by the last mutation
    autosave: Path | None = field(default=None, repr=False, compare=False)
    rng: random.Random = field(default_factory=random.Random, repr=False, compare=False)
    _in_mutation: bool = field(default=False, repr=False, compare=False)

    def __post_init__(self):
        self.sudden_caller = _optional(Caller, self.sudden_caller)

    def to_json(self) -> str:
        """Full live state. Fields with compare=False (rng, undo history, autosave path) are not state."""
        data = {f.name: getattr(self, f.name) for f in fields(self) if f.compare}
        return json.dumps({"version": FORMAT_VERSION, **data}, default=asdict, indent=2)

    @classmethod
    def from_json(cls, text: str) -> "Chase":
        data = json.loads(text)
        version = data.pop("version", None)
        if version not in READABLE_VERSIONS:
            raise ValueError("unsupported chase file version")
        if version == 1:
            descriptions = data.pop("descriptions", {})
            names = [{"name": n, "description": descriptions.get(str(i), "")} for i, n in enumerate(data["locations"])]
            data["locations"] = locations_from_v1(names, data.pop("hazards", {}))
        else:
            data["locations"] = [Location.from_dict(loc) for loc in data["locations"]]
        investigators = data.pop("investigators", [])  # versions 1-2
        data["participants"] = [Participant(**p) for p in data["participants"]]
        for p in data["participants"]:
            p.investigator = p.investigator or p.name in investigators
        data["left_behind"] = [Participant(**p) for p in data.get("left_behind", [])]
        return cls(**data)

    @classmethod
    def load(cls, path: Path) -> "Chase":
        """Resume the autosave at `path` if present, else a blank chase that autosaves there."""
        try:
            chase = cls.from_json(path.read_text()) if path.exists() else cls()
        except ValueError as e:
            raise ValueError(f"{path.name}: {e}") from e
        chase.autosave = path
        return chase

    def save(self) -> None:
        if self.autosave:
            tmp = self.autosave.with_suffix(".tmp")
            tmp.write_text(self.to_json())
            tmp.replace(self.autosave)  # atomic: a crash mid-write keeps the old file

    def log_event(self, text: str) -> None:
        entry = f"R{self.round}: {text}"
        self.log.append(entry)
        self.last_entries.append(entry)

    def undo(self) -> list[str] | None:
        """Revert the last mutation. Returns the log entries it wrote, or None if there is nothing to undo."""
        if not self.history:
            return None
        snapshot, entries = self.history.pop()
        self.replace_with(Chase.from_json(snapshot))
        self.save()
        return entries

    def replace_with(self, other: "Chase") -> None:
        """Take over all of `other`'s state; history, autosave path and rng stay. Not logged or snapshotted."""
        for f in fields(self):
            if f.compare:
                setattr(self, f.name, getattr(other, f.name))

    @mutation
    def roll(self, count: int, sides: int, label: str = "") -> int:
        """NxDy, e.g. roll(1, 3) for 1D3. Logged."""
        total = sum(self.rng.randint(1, sides) for _ in range(count))
        self.log_event(f"{label + ' ' if label else ''}{count}D{sides}: {total}")
        return total

    @mutation
    def roll_d100(self, target: int, bonus: int = 0, label: str = "") -> tuple[int, str]:
        """D100 vs target. bonus > 0: that many bonus dice, < 0: penalty dice (max 2). Logged."""
        result = self._d100(bonus)
        level = success_level(result, target)
        dice = f" ({abs(bonus)} {'bonus' if bonus > 0 else 'penalty'})" if bonus else ""
        self.log_event(f"{label + ' ' if label else ''}D100 vs {target}{dice}: {result} {level}")
        return result, level

    def _d100(self, bonus: int = 0) -> int:
        """Unlogged D100 with bonus (> 0) or penalty (< 0) dice."""
        units = self.rng.randint(0, 9)
        rolls = [(self.rng.randint(0, 9) * 10 + units) or 100 for _ in range(1 + abs(bonus))]
        return min(rolls) if bonus >= 0 else max(rolls)

    @mutation
    def roll_speed(self, name: str) -> None:
        """NPC speed roll against the participant's speed-roll value."""
        p = self.get(name)
        _, level = self.roll_d100(p.speed_value, label=f"{name} speed roll")
        self.set_speed_result(name, SPEED_FROM_LEVEL[level])

    @mutation
    def add(self, participant: Participant) -> None:
        self.participants.append(participant)
        self.log_event(f"{participant.name} ({participant.side}) joins")

    @mutation
    def remove(self, name: str) -> None:
        """Leave the chase. Movement actions are not recalculated (slowest_mov is stored)."""
        self.participants.remove(self.get(name))
        self.log_event(f"{name} leaves the chase")

    def get(self, name: str) -> Participant:
        return next(p for p in self.participants if p.name == name)

    @mutation
    def set_speed_result(self, name: str, result: SpeedResult) -> None:
        p = self.get(name)
        p.speed_result = SpeedResult(result)
        self.log_event(f"{name} speed roll {result}, MOV {p.adjusted_mov}")

    @mutation
    def establish(self, start_range: int = 2, start_location: int = 0) -> None:
        """Eliminate, place, compute movement actions and start round 1 (rulebook p. 146).

        One-on-one (passengers aside) with the fleeing character faster: they escape, no chase is played.
        Otherwise faster fleeing characters are flagged in `may_escape`, and pursuers slower than the
        slowest fleeing character are left behind (moved to `left_behind`). The slowest pursuer starts on
        `start_location`, the slowest fleeing character `start_range` ahead of the foremost pursuer.
        """
        pursuers = [p for p in self.participants if p.side == Side.PURSUER and not p.is_passenger]
        fleeing = [p for p in self.participants if p.side == Side.FLEEING and not p.is_passenger]
        fastest_pursuer = max(p.adjusted_mov for p in pursuers)
        faster = [p.name for p in fleeing if p.adjusted_mov > fastest_pursuer]
        if faster and len(pursuers) == len(fleeing) == 1:
            self.escaped = faster
            self.log_event(f"{', '.join(faster)} escapes, no chase is played")
            return
        self.may_escape = faster
        if faster:
            self.log_event(f"{', '.join(faster)} may escape")
        slowest_fleeing = min(p.adjusted_mov for p in fleeing)
        for p in pursuers:
            if p.adjusted_mov < slowest_fleeing:
                self.participants.remove(p)
                self.left_behind.append(p)
                self.log_event(f"{p.name} is left behind")
        pursuers = [p for p in self.participants if p.side == Side.PURSUER and not p.is_passenger]
        slowest_pursuer = min((p.adjusted_mov for p in pursuers), default=fastest_pursuer)
        for p in pursuers:
            p.location = start_location + p.adjusted_mov - slowest_pursuer
        front = start_location + fastest_pursuer - slowest_pursuer + start_range
        for p in fleeing:
            p.location = front + p.adjusted_mov - slowest_fleeing
        for p in pursuers + fleeing:
            self._carry(p)
        self._pad(max(p.location for p in self.participants) + 1)
        # Stored, not derived: leaving the chase must not recalculate movement actions.
        self.slowest_mov = min(p.adjusted_mov for p in pursuers + fleeing)
        self.round = 1
        self._reset_actions()
        self.log_event(f"Chase established, range {start_range}")

    @mutation
    def join(self, participant: Participant, location: int, speed_result: SpeedResult | None = None) -> None:
        """Join a running chase (rulebook p. 142). speed_result None = NPC speed roll.

        A pursuer slower than the slowest fleeing character is flagged in `unable_to_join`
        and left out. A new slowest participant shifts everyone's movement actions (spent ones stay spent).
        """
        p = participant
        self.add(p)
        if p.is_passenger:  # no speed roll, never the slowest
            p.actions_left, p.passenger_action = 0, True
            self.set_location(p.name, self.get(p.vehicle).location)
            return
        if speed_result is None:
            self.roll_speed(p.name)
        else:
            self.set_speed_result(p.name, speed_result)
        fleeing = [o.adjusted_mov for o in self.participants if o.side == Side.FLEEING and not o.is_passenger]
        if p.side == Side.PURSUER and fleeing and p.adjusted_mov < min(fleeing):
            self.participants.remove(p)
            self.unable_to_join.append(p.name)
            self.log_event(f"{p.name} is too slow to join")
            return
        if p.adjusted_mov < self.slowest_mov:
            for other in self.participants:
                if not other.is_passenger:
                    other.actions_left += self.slowest_mov - p.adjusted_mov
            self.slowest_mov = p.adjusted_mov
            self.log_event(f"{p.name} is the new slowest, movement actions recalculated")
        p.actions_left = self.movement_actions(p)
        self.set_location(p.name, location)

    @mutation
    def set_location(self, name: str, location: int) -> None:
        """Keeper override: put a participant on any location."""
        self.get(name).location = location
        self.get(name).pedal = 0
        self._carry(self.get(name))
        self._pad(location)
        self.log_event(f"{name} placed on {self.locations[location].name}")

    @mutation
    def set_actions(self, name: str, actions: int) -> None:
        """Keeper override: movement actions left this round."""
        self.get(name).actions_left = actions
        self.log_event(f"{name} movement actions set to {actions}")

    @mutation
    def set_debt(self, name: str, debt: int) -> None:
        """Keeper override: movement-action debt carried into the next round."""
        self.get(name).debt = debt
        self.log_event(f"{name} debt set to {debt}")

    @mutation
    def set_build(self, name: str, build: int) -> None:
        """Keeper override: a vehicle's current build (collisions, failed hazards)."""
        self.get(name).build = build
        self.log_event(f"{name} build set to {build}")

    @mutation
    def edit_participant(self, name: str, /, **changes) -> None:
        """Keeper edit of any Participant field. A new name follows into every list that refers to it.

        Giving HP or build to someone without a maximum makes it their starting value.
        """
        unknown = set(changes) - {f.name for f in fields(Participant)}
        if unknown:
            raise ValueError(f"unknown participant fields: {', '.join(sorted(unknown))}")
        p = self.get(name)
        changes = {k: v for k, v in changes.items() if getattr(p, k) != v}
        edited = replace(p, **changes)  # validates (e.g. an unknown side) before anything changes
        for k in changes:
            setattr(p, k, getattr(edited, k))
        if p.max_hp is None:
            p.max_hp = p.hp
        if p.max_build is None:
            p.max_build = p.build
        if "location" in changes:  # as set_location: stop accelerating, carry passengers, extend the layout
            p.pedal = 0
            self._carry(p)
            self._pad(p.location)
        new = changes.get("name")
        if new:
            for names in (self.order, self.delayed, self.may_escape, *self.resolved_ties):
                names[:] = [new if n == name else n for n in names]
            for o in self.participants:
                if o.vehicle == name:
                    o.vehicle = new
        if changes:
            shown = {**changes, **({"location": self.locations[p.location].name} if "location" in changes else {})}
            self.log_event(f"{name} edited: " + ", ".join(f"{k} {v}" for k, v in shown.items()))

    def badges(self, name: str) -> list[str]:
        p = self.get(name)
        badges = [f"passenger in {p.vehicle}"] if p.is_passenger else []
        if p.is_vehicle:
            if p.build <= 0:
                badges.append("undriveable")
            elif p.build <= p.max_build // 2:
                badges.append("impaired: 1 penalty die")
        if p.pedal:
            badges.append(f"pedal to the metal: {_dice(p.pedal_penalty, 'penalty')}")
        return badges

    def ready_to_establish(self) -> bool:
        """Both sides present and every speed roll in (passengers make none)."""
        sides = {p.side for p in self.participants if not p.is_passenger}
        return sides == set(Side) and all(
            p.speed_result for p in self.participants if not p.is_passenger)

    def targets(self, name: str) -> list[str]:
        """Who `name` can attack or maneuver: everyone on the other side."""
        side = self.get(name).side
        return [p.name for p in self.participants if p.side != side]

    def same_location(self) -> list[int]:
        """Locations where a pursuer shares a location with a fleeing character."""
        sides: dict[int, set[str]] = {}
        for p in self.participants:
            sides.setdefault(p.location, set()).add(p.side)
        return sorted(loc for loc, s in sides.items() if len(s) == 2)

    def movement_actions(self, p: Participant) -> int:
        """Passengers: 0 movement actions (their 1 action per turn is `passenger_action`)."""
        if p.is_passenger:
            return 0
        return 1 + p.adjusted_mov - self.slowest_mov

    def dex_order(self) -> list[Participant]:
        """Highest DEX first, unless the Keeper or an opposed DEX roll set `order`.

        Anyone missing from `order` (e.g. later joiners) goes right after the last participant with
        the same DEX, else after the last with a higher DEX, else first; the ordered keep their relative order.
        """
        by_dex = sorted(self.participants, key=lambda p: -p.dex)
        if not self.order:
            return by_dex
        result = [p for name in self.order for p in self.participants if p.name == name]
        for p in by_dex:
            if p.name not in self.order:
                after = ([i for i, o in enumerate(result) if o.dex == p.dex]
                         or [i for i, o in enumerate(result) if o.dex > p.dex])
                result.insert(after[-1] + 1 if after else 0, p)
        return result

    def dex_ties(self) -> list[list[str]]:
        """Unresolved groups of names sharing a DEX, in turn order.

        A tie is its exact set of members: once anyone joins or leaves it, it is a new, unresolved tie.
        """
        groups: dict[int, list[str]] = {}
        for p in self.dex_order():
            groups.setdefault(p.dex, []).append(p.name)
        resolved = [set(t) for t in self.resolved_ties]
        return [g for g in groups.values() if len(g) > 1 and set(g) not in resolved]

    def _forget_stale_ties(self) -> None:
        """Drop resolved ties whose exact membership no longer shares a DEX (a join, DEX edit or removal)."""
        groups: dict[int, set[str]] = {}
        for p in self.participants:
            groups.setdefault(p.dex, set()).add(p.name)
        self.resolved_ties = [t for t in self.resolved_ties if set(t) in groups.values()]

    @mutation
    def reorder(self, names: list[str]) -> None:
        """Keeper sets the turn order (or overrides DEX outright).

        Resolves each DEX tie whose members' relative order this changes.
        """
        before = [p.name for p in self.dex_order()]
        for tie in self.dex_ties():
            if [n for n in before if n in tie] != [n for n in names if n in tie]:
                self.resolved_ties.append(tie)
        self.order = list(names)
        self.log_event(f"Order set: {', '.join(names)}")

    @mutation
    def keep_dex_order(self, tie: list[str]) -> None:
        """Keeper confirms a DEX tie's current order."""
        self.resolved_ties.append(list(tie))
        self.log_event(f"DEX tie kept in order: {', '.join(tie)}")

    @mutation
    def roll_dex_ties(self) -> None:
        """Opposed DEX roll within each unresolved tie of NPCs only (players roll for investigators):
        better result level first, then lower roll.

        Identical results are rerolled; the reroll only orders those tied with each other.
        """
        order = [p.name for p in self.dex_order()]
        groups = [g for g in self.dex_ties() if not any(self.get(n).investigator for n in g)]
        if not groups:
            self.log_event("No NPC DEX ties to roll")
            return
        for group in groups:
            results = {name: [] for name in group}
            pending = group
            while pending:
                for name in pending:
                    roll, level = self.roll_d100(self.get(name).dex, label=f"{name} opposed DEX")
                    results[name].append((LEVELS.index(level), roll))
                rolled = list(results.values())
                pending = [n for n in group if rolled.count(results[n]) > 1]
            slots = sorted(order.index(n) for n in group)  # tied members need not sit together
            for i, name in zip(slots, sorted(group, key=results.get)):
                order[i] = name
            self.resolved_ties.append(group)
        self.reorder(order)

    def turn_order(self) -> list[Participant]:
        """DEX order with this round's delayed participants moved to the end, latest delay last."""
        order = [p for p in self.dex_order() if p.name not in self.delayed]
        return order + [self.get(n) for n in self.delayed]

    def current_turn(self) -> Participant | None:
        if self.ended:
            return None
        return next((p for p in self.turn_order() if p.actions_left > 0 or p.pedal or p.passenger_action), None)

    def had_turn(self, name: str) -> bool:
        """Comes before the current turn in turn order (nobody in setup or after the chase ends)."""
        if self.round == 0 or self.ended:
            return False
        order = [p.name for p in self.turn_order()]
        current = self.current_turn()
        return order.index(name) < (order.index(current.name) if current else len(order))

    @mutation
    def delay(self, name: str) -> None:
        if name in self.delayed:
            self.delayed.remove(name)
        self.delayed.append(name)
        self.log_event(f"{name} delays")

    @mutation
    def move(self, name: str) -> None:
        p = self.get(name)
        p.actions_left -= 1
        p.pedal = 0
        self._advance(p)
        self.log_event(f"{name} moves → {self.locations[p.location].name}")

    @mutation
    def pedal_to_the_metal(self, name: str, distance: int) -> None:
        """Vehicle accelerates: 1 movement action for `distance` (2-5) locations (rulebook p. 140).

        2-3 locations = 1 penalty die on hazards, 4-5 = 2. It stops at the first hazard ahead;
        resolve_hazard then crosses it for free and carries on, unless the roll fails.
        """
        p = self.get(name)
        penalty = (1 if distance <= 3 else 2) - p.navigated
        p.navigated = False
        text = f"{name} puts the pedal to the metal: {distance} locations ({_dice(penalty, 'penalty')})"
        text += self._spend(p, 1)
        p.pedal_penalty = penalty
        self._accelerate(p, distance)
        self.log_event(f"{text} → {self.locations[p.location].name}")

    def _accelerate(self, p: Participant, distance: int) -> None:
        """Advance up to `distance` locations, stopping in front of any hazard."""
        while distance and not self.locations[p.location].hazard_after:
            self._advance(p)
            distance -= 1
        p.pedal = distance

    def _advance(self, p: Participant) -> None:
        p.location += 1
        self._pad(p.location)
        self._carry(p)

    def _pad(self, index: int) -> None:
        """Append blank locations until `index` exists."""
        self.locations += [Location(default_location_name(i)) for i in range(len(self.locations), index + 1)]

    def _carry(self, vehicle: Participant) -> None:
        """Passengers ride along with their vehicle."""
        for o in self.participants:
            if o.vehicle == vehicle.name:
                o.location = vehicle.location

    @mutation
    def navigate(self, name: str, passed: bool) -> None:
        """Passenger's Spot Hidden / Navigate roll: on a success the vehicle's next Pedal to the Metal
        has 1 penalty die less. Uses the passenger's action."""
        p = self.get(name)
        text = f"{name} navigates for {p.vehicle}"
        if passed:
            self.get(p.vehicle).navigated = True
            text += ": next Pedal to the Metal −1 penalty die"
        else:
            text += ", no help"
        self.log_event(text + self._spend(p, 1))

    @mutation
    def add_hazard(self, gap: int, hazard: Hazard) -> None:
        """Place (or replace) the hazard between location `gap` and `gap + 1`."""
        self.locations[gap].hazard_after = hazard
        self.log_event(f"Hazard {hazard.name} placed after {self.locations[gap].name}")

    @mutation
    def roll_random_hazard(self, gap: int, bonus: int = 0) -> None:
        """D100 for the gap: 01-59 clear (logged only, any hazard stays), 60+ regular, 85+ hard, 96+ extreme.

        bonus = 1 for a quiet environment, -1 for an especially hazardous one.
        """
        roll = self._d100(bonus)
        difficulty = (Difficulty.EXTREME if roll >= 96 else Difficulty.HARD if roll >= 85
                      else Difficulty.REGULAR if roll >= 60 else None)
        if difficulty:
            self.locations[gap].hazard_after = Hazard("random hazard", difficulty=difficulty)
        dice = f" ({abs(bonus)} {'bonus' if bonus > 0 else 'penalty'})" if bonus else ""
        self.log_event(f"Random hazard after {self.locations[gap].name}{dice} D100: {roll} {difficulty or 'clear'}")

    @mutation
    def remove_hazard(self, gap: int) -> None:
        location = self.locations[gap]
        hazard, location.hazard_after = location.hazard_after, None
        for p in self.participants:
            if p.location == gap:
                p.pedal = 0  # stopped in front of it: the acceleration is over
        self.log_event(f"Hazard {hazard.name} removed after {location.name}")

    @mutation
    def add_location(self, index: int, name: str = "", description: str = "") -> None:
        """Insert a location before `index`; everything from `index` on shifts one along.

        A blank name becomes "Location <number>", like the locations padded in automatically.
        """
        name = name.strip() or default_location_name(index)
        self._shift(index, 1)
        self.locations.insert(index, Location(name, description))
        self.log_event(f"{name} added")

    @mutation
    def edit_location(self, index: int, name: str, description: str = "") -> None:
        self.locations[index].name = name
        self.locations[index].description = description
        self.log_event(f"Location {index + 1} is now {name}")

    @mutation
    def remove_location(self, index: int) -> None:
        """Drop a location and the hazard after it. Participants on it stay on the index (the next one)."""
        location = self.locations.pop(index)
        self._shift(index + 1, -1)
        for p in self.participants:
            p.location = min(p.location, len(self.locations) - 1)
        self.log_event(f"{location.name} removed")

    def _shift(self, start: int, delta: int) -> None:
        """Move participants on index >= start by delta."""
        for p in self.participants:
            if p.location >= start:
                p.location += delta

    def hazard_ahead(self, name: str) -> Hazard | None:
        return self.locations[self.get(name).location].hazard_after

    @mutation
    def resolve_hazard(self, name: str, passed: bool, bonus: int = 0,
                       lost: int | None = None, damage: int = 0) -> None:
        """Cross the hazard ahead: 1 movement action plus `bonus` cautious bonus dice (max 2, and
        no more than the actions left after crossing).

        On a fail, `lost` movement actions (None = roll 1D3) and optional HP damage.
        Actions spent beyond what is left become debt. Moves on to the next location either way,
        except a failed barrier: no 1D3 by default, and the participant stays put.
        """
        p = self.get(name)
        hazard = self.hazard_ahead(name)
        pedal, p.pedal = p.pedal, 0  # mid-acceleration: crossing is already paid for
        cost = 0 if pedal else 1
        bonus = max(0, min(bonus, 2, p.actions_left - cost))  # only actions actually left, never debt
        cost += bonus
        blocked = hazard.kind == HazardKind.BARRIER and not passed
        text = f"{name} {'passes' if passed else 'fails'} {hazard.kind} {hazard.name}"
        if bonus:
            text += f" ({bonus} bonus {'die' if bonus == 1 else 'dice'})"
        if blocked and lost is None:
            lost = 0
        if not passed:
            lost, outcome = self._fail_outcome(p, lost, damage)
            cost += lost
            text += outcome
        self.log_event(text + self._spend(p, cost))
        if not blocked:
            self._advance(p)
        if pedal and passed:
            self._accelerate(p, pedal - 1)

    @mutation
    def damage_barrier(self, name: str, damage: int | None = None) -> None:
        """Spend 1 movement action smashing the barrier ahead. At 0 HP it is gone; the participant stays.

        damage None = a vehicle rolls 1D10 per point of build.
        """
        p = self.get(name)
        if damage is None:
            damage = self.roll(p.build, 10, label=f"{name} barrier damage")
        location = self.locations[p.location]
        barrier = location.hazard_after
        barrier.hp = max(0, barrier.hp - damage)
        text = f"{name} deals {damage} damage to barrier {barrier.name} ({barrier.hp}/{barrier.max_hp} HP)"
        if barrier.hp == 0:
            location.hazard_after = None
            text += ", broken"
        self.log_event(text + self._spend(p, 1))

    def _fail_outcome(self, p: Participant, lost: int | None, damage: int) -> tuple[int, str]:
        """Hazard-failure outcome: `lost` actions (None = roll 1D3) and optional HP damage."""
        if lost is None:
            lost = self.roll(1, 3, label=f"{p.name} lost actions")
        text = f", −{lost} actions" if lost else ""
        if damage and p.is_vehicle:
            p.build -= damage
            text += f", −{damage} build ({p.build})"
        elif damage and p.hp is not None:
            p.hp -= damage
            text += f", −{damage} HP ({p.hp})"
        return lost, text

    def _spend(self, p: Participant, cost: int) -> str:
        """Spend movement actions; whatever is not left becomes debt. Returns a log suffix.

        A passenger instead uses up their one action this turn, never debt.
        """
        if p.is_passenger:
            p.passenger_action = p.passenger_action and not cost
            return ""
        p.pedal = 0  # any other action ends a Pedal to the Metal acceleration
        p.actions_left -= cost
        if p.actions_left >= 0:
            return ""
        p.debt += -p.actions_left
        p.actions_left = 0
        return f", debt {p.debt}"

    @mutation
    def attack(self, name: str, target: str) -> None:
        """Initiate an attack: 1 movement action. The Keeper runs the combat roll."""
        self.log_event(f"{name} attacks {target}" + self._spend(self.get(name), 1))

    @mutation
    def other_action(self, name: str, note: str) -> None:
        """Anything else (spell, lock, firing while stopped): 1 movement action."""
        self.log_event(f"{name}: {note}" + self._spend(self.get(name), 1))

    @mutation
    def maneuver(self, name: str, target: str, lost: int | None = None, damage: int = 0) -> None:
        """Successful fighting maneuver: 1 action for `name`, hazard-failure outcome for `target`."""
        t = self.get(target)
        lost, outcome = self._fail_outcome(t, lost, damage)
        spent = self._spend(self.get(name), 1)
        self.log_event(f"{name} maneuvers {target}{spent}{outcome}" + self._spend(t, lost))

    @mutation
    def call_sudden_hazard(self, caller: Caller) -> None:
        """`caller` calls a sudden hazard; the other side calls the next one."""
        caller = Caller(caller)
        self.sudden_caller = Caller.PLAYERS if caller == Caller.KEEPER else Caller.KEEPER
        self.log_event(f"Sudden hazard called by {caller}")

    @mutation
    def end_chase(self) -> None:
        self.ended = True
        self.log_event("Chase ends")

    @mutation
    def end_round(self) -> None:
        if self.ended:
            return
        self.round += 1
        self.delayed = []
        self._reset_actions()
        for p in self.participants:
            paid = min(p.debt, p.actions_left)
            p.actions_left -= paid
            p.debt -= paid
        self.log_event(f"Round {self.round} begins")

    def _reset_actions(self) -> None:
        for p in self.participants:
            p.actions_left = self.movement_actions(p)
            p.passenger_action = p.is_passenger
            p.pedal = 0
