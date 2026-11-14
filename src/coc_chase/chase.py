"""Pure chase logic (CoC 7e, chapter 7). No UI imports."""

import functools
import json
import random
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

FORMAT_VERSION = 1



def mutation(fn):
    """Wrap every state-changing Chase method: snapshot for undo, run, autosave.

    The method itself writes its log line with self.log_event(...).
    Nested calls (a mutation calling another, e.g. a dice roll) share the outer snapshot.
    """
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        if self._in_mutation:
            return fn(self, *args, **kwargs)
        snapshot = self.to_json()
        self._in_mutation = True
        try:
            result = fn(self, *args, **kwargs)
        finally:
            self._in_mutation = False
        self.history.append(snapshot)
        self.save()
        return result
    return wrapper


SPEED_MOD = {"extreme": 1, "success": 0, "fail": -1}
# D100 result level -> speed result
SPEED_FROM_LEVEL = {"critical": "extreme", "extreme": "extreme", "hard": "success",
                    "regular": "success", "failure": "fail", "fumble": "fail"}
LEVELS = list(SPEED_FROM_LEVEL)  # best first


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


def fallback_targets(value: int) -> dict[str, int]:
    """Monster skill fallback: full, half or one-fifth of a characteristic (e.g. DEX)."""
    return {"full": value, "half": value // 2, "fifth": value // 5}


@dataclass
class Hazard:
    """Obstacle in the gap between location i and i+1 (keyed by i in Chase.hazards)."""
    name: str
    skill: str = ""  # suggested skill(s), free text
    difficulty: str = "regular"  # "regular" / "hard" / "extreme"
    notes: str = ""


@dataclass
class Participant:
    name: str
    side: str  # "pursuer" or "fleeing"
    dex: int
    mov: int
    speed_value: int
    speed_result: str | None = None  # "extreme" / "success" / "fail"
    location: int = 0  # index into Chase.locations
    actions_left: int = 0
    debt: int = 0  # lost movement actions carried into the next round
    hp: int | None = None
    max_hp: int | None = None

    @property
    def adjusted_mov(self) -> int:
        return self.mov + SPEED_MOD.get(self.speed_result, 0)


@dataclass
class Chase:
    participants: list[Participant] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    hazards: dict[int, Hazard] = field(default_factory=dict)  # gap i = between location i and i+1
    escaped: list[str] = field(default_factory=list)
    may_escape: list[str] = field(default_factory=list)
    unable_to_join: list[str] = field(default_factory=list)  # pursuers too slow to join mid-chase
    order: list[str] = field(default_factory=list)  # Keeper turn order; empty = by DEX
    round: int = 0  # 0 = not established yet
    slowest_mov: int = 0
    delayed: list[str] = field(default_factory=list)  # this round only, acting after everyone else
    sudden_caller: str | None = None  # "keeper" / "players" may call the next sudden hazard; None = either
    ended: bool = False
    log: list[str] = field(default_factory=list)
    # Not state (compare=False): excluded from JSON, equality and undo snapshots.
    history: list[str] = field(default_factory=list, repr=False, compare=False)
    autosave: Path | None = field(default=None, repr=False, compare=False)
    rng: random.Random = field(default_factory=random.Random, repr=False, compare=False)
    _in_mutation: bool = field(default=False, repr=False, compare=False)

    def to_json(self) -> str:
        """Full live state. Fields with compare=False (rng, undo history, autosave path) are not state."""
        data = {f.name: getattr(self, f.name) for f in fields(self) if f.compare}
        return json.dumps({"version": FORMAT_VERSION, **data}, default=asdict, indent=2)

    @classmethod
    def from_json(cls, text: str) -> "Chase":
        data = json.loads(text)
        if data.pop("version", None) != FORMAT_VERSION:
            raise ValueError("unsupported chase file version")
        data["participants"] = [Participant(**p) for p in data["participants"]]
        data["hazards"] = {int(i): Hazard(**h) for i, h in data["hazards"].items()}
        return cls(**data)

    @classmethod
    def load(cls, path: Path) -> "Chase":
        """Resume the autosave at `path` if present, else a blank chase that autosaves there."""
        chase = cls.from_json(path.read_text()) if path.exists() else cls()
        chase.autosave = path
        return chase

    def save(self) -> None:
        if self.autosave:
            tmp = self.autosave.with_suffix(".tmp")
            tmp.write_text(self.to_json())
            tmp.replace(self.autosave)  # atomic: a crash mid-write keeps the old file

    def log_event(self, text: str) -> None:
        self.log.append(f"R{self.round}: {text}")

    def undo(self) -> None:
        if not self.history:
            return
        previous = Chase.from_json(self.history.pop())
        for f in fields(self):
            if f.compare:
                setattr(self, f.name, getattr(previous, f.name))
        self.save()

    @mutation
    def roll(self, count: int, sides: int, label: str = "") -> int:
        """NxDy, e.g. roll(1, 3) for 1D3. Logged."""
        total = sum(self.rng.randint(1, sides) for _ in range(count))
        self.log_event(f"{label + ' ' if label else ''}{count}D{sides}: {total}")
        return total

    @mutation
    def roll_d100(self, target: int, bonus: int = 0, label: str = "") -> tuple[int, str]:
        """D100 vs target. bonus > 0: that many bonus dice, < 0: penalty dice (max 2). Logged."""
        units = self.rng.randint(0, 9)
        rolls = [(self.rng.randint(0, 9) * 10 + units) or 100 for _ in range(1 + abs(bonus))]
        result = min(rolls) if bonus >= 0 else max(rolls)
        level = success_level(result, target)
        dice = f" ({abs(bonus)} {'bonus' if bonus > 0 else 'penalty'})" if bonus else ""
        self.log_event(f"{label + ' ' if label else ''}D100 vs {target}{dice}: {result} {level}")
        return result, level

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
    def set_speed_result(self, name: str, result: str) -> None:
        p = self.get(name)
        p.speed_result = result
        self.log_event(f"{name} speed roll {result}, MOV {p.adjusted_mov}")

    @mutation
    def establish(self, start_range: int = 2, start_location: int = 0) -> None:
        """Eliminate, place, compute movement actions and start round 1 (rulebook p. 146).

        Every fleeing character faster than every pursuer: they escape, no chase is played.
        Otherwise faster ones are flagged in `may_escape`, and pursuers slower than the
        slowest fleeing character are left behind (removed). The slowest pursuer starts on
        `start_location`, the slowest fleeing character `start_range` ahead of the foremost pursuer.
        """
        pursuers = [p for p in self.participants if p.side == "pursuer"]
        fleeing = [p for p in self.participants if p.side == "fleeing"]
        fastest_pursuer = max(p.adjusted_mov for p in pursuers)
        faster = [p.name for p in fleeing if p.adjusted_mov > fastest_pursuer]
        if len(faster) == len(fleeing):
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
                self.log_event(f"{p.name} is left behind")
        pursuers = [p for p in self.participants if p.side == "pursuer"]
        slowest_pursuer = min(p.adjusted_mov for p in pursuers)
        for p in pursuers:
            p.location = start_location + p.adjusted_mov - slowest_pursuer
        front = start_location + fastest_pursuer - slowest_pursuer + start_range
        for p in fleeing:
            p.location = front + p.adjusted_mov - slowest_fleeing
        last = max(p.location for p in self.participants) + 1
        self.locations += [f"Location {i + 1}" for i in range(len(self.locations), last + 1)]
        # Stored, not derived: leaving the chase must not recalculate movement actions.
        self.slowest_mov = min(p.adjusted_mov for p in self.participants)
        self.round = 1
        self._reset_actions()
        self.log_event(f"Chase established, range {start_range}")

    @mutation
    def join(self, participant: Participant, location: int, speed_result: str | None = None) -> None:
        """Join a running chase (rulebook p. 142). speed_result None = NPC speed roll.

        A pursuer slower than the slowest fleeing character is flagged in `unable_to_join`
        and left out. A new slowest participant shifts everyone's movement actions (spent ones stay spent).
        """
        p = participant
        self.add(p)
        if speed_result is None:
            self.roll_speed(p.name)
        else:
            self.set_speed_result(p.name, speed_result)
        fleeing = [o.adjusted_mov for o in self.participants if o.side == "fleeing"]
        if p.side == "pursuer" and fleeing and p.adjusted_mov < min(fleeing):
            self.participants.remove(p)
            self.unable_to_join.append(p.name)
            self.log_event(f"{p.name} is too slow to join")
            return
        if p.adjusted_mov < self.slowest_mov:
            for other in self.participants:
                other.actions_left += self.slowest_mov - p.adjusted_mov
            self.slowest_mov = p.adjusted_mov
            self.log_event(f"{p.name} is the new slowest, movement actions recalculated")
        p.actions_left = self.movement_actions(p)
        self.set_location(p.name, location)

    @mutation
    def set_location(self, name: str, location: int) -> None:
        """Keeper override: put a participant on any location."""
        self.get(name).location = location
        self.locations += [f"Location {i + 1}" for i in range(len(self.locations), location + 1)]
        self.log_event(f"{name} placed on {self.locations[location]}")

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

    def same_location(self) -> list[int]:
        """Locations where a pursuer shares a location with a fleeing character."""
        sides: dict[int, set[str]] = {}
        for p in self.participants:
            sides.setdefault(p.location, set()).add(p.side)
        return sorted(loc for loc, s in sides.items() if len(s) == 2)

    def movement_actions(self, p: Participant) -> int:
        return 1 + p.adjusted_mov - self.slowest_mov

    def dex_order(self) -> list[Participant]:
        """Highest DEX first, unless the Keeper or an opposed DEX roll set `order`.

        Names missing from `order` (e.g. later joiners) go after it, by DEX.
        """
        rank = {name: i for i, name in enumerate(self.order)}
        return sorted(self.participants, key=lambda p: (rank.get(p.name, len(rank)), -p.dex))

    def dex_ties(self) -> list[list[str]]:
        """Groups of names sharing a DEX, until an order is set (by reorder or roll_dex_ties)."""
        if self.order:
            return []
        groups: dict[int, list[str]] = {}
        for p in self.dex_order():
            groups.setdefault(p.dex, []).append(p.name)
        return [g for g in groups.values() if len(g) > 1]

    @mutation
    def reorder(self, names: list[str]) -> None:
        """Keeper sets the turn order (resolves DEX ties, or overrides DEX outright)."""
        self.order = list(names)
        self.log_event(f"Order set: {', '.join(names)}")

    @mutation
    def roll_dex_ties(self) -> None:
        """Opposed DEX roll within each tied group: better result level first, then lower roll."""
        # ponytail: equal level and roll keeps current order instead of rerolling
        order = [p.name for p in self.dex_order()]
        for group in self.dex_ties():
            results = {}
            for name in group:
                roll, level = self.roll_d100(self.get(name).dex, label=f"{name} opposed DEX")
                results[name] = (LEVELS.index(level), roll)
            start = order.index(group[0])
            order[start:start + len(group)] = sorted(group, key=results.get)
        self.reorder(order)

    def turn_order(self) -> list[Participant]:
        """DEX order with this round's delayed participants moved to the end, latest delay last."""
        order = [p for p in self.dex_order() if p.name not in self.delayed]
        return order + [self.get(n) for n in self.delayed]

    def current_turn(self) -> Participant | None:
        if self.ended:
            return None
        return next((p for p in self.turn_order() if p.actions_left > 0), None)

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
        self._advance(p)
        self.log_event(f"{name} moves → {self.locations[p.location]}")

    def _advance(self, p: Participant) -> None:
        p.location += 1
        while p.location >= len(self.locations):
            self.locations.append(f"Location {len(self.locations) + 1}")

    @mutation
    def add_hazard(self, gap: int, hazard: Hazard) -> None:
        """Place (or replace) the hazard between location `gap` and `gap + 1`."""
        self.hazards[gap] = hazard
        self.log_event(f"Hazard {hazard.name} placed after {self.locations[gap]}")

    def hazard_ahead(self, name: str) -> Hazard | None:
        return self.hazards.get(self.get(name).location)

    @mutation
    def resolve_hazard(self, name: str, passed: bool, bonus: int = 0,
                       lost: int | None = None, damage: int = 0) -> None:
        """Cross the hazard ahead: 1 movement action plus `bonus` cautious bonus dice (max 2).

        On a fail, `lost` movement actions (None = roll 1D3) and optional HP damage.
        Actions spent beyond what is left become debt. Moves on to the next location either way.
        """
        p = self.get(name)
        hazard = self.hazard_ahead(name)
        bonus = min(bonus, 2)
        cost = 1 + bonus
        text = f"{name} {'passes' if passed else 'fails'} hazard {hazard.name}"
        if bonus:
            text += f" ({bonus} bonus {'die' if bonus == 1 else 'dice'})"
        if not passed:
            lost, outcome = self._fail_outcome(p, lost, damage)
            cost += lost
            text += outcome
        self.log_event(text + self._spend(p, cost))
        self._advance(p)

    def _fail_outcome(self, p: Participant, lost: int | None, damage: int) -> tuple[int, str]:
        """Hazard-failure outcome: `lost` actions (None = roll 1D3) and optional HP damage."""
        if lost is None:
            lost = self.roll(1, 3, label=f"{p.name} lost actions")
        text = f", −{lost} actions"
        if damage and p.hp is not None:
            p.hp -= damage
            text += f", −{damage} HP ({p.hp})"
        return lost, text

    def _spend(self, p: Participant, cost: int) -> str:
        """Spend movement actions; whatever is not left becomes debt. Returns a log suffix."""
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
    def call_sudden_hazard(self, caller: str) -> None:
        """`caller` ("keeper" / "players") calls a sudden hazard; the other side calls the next one."""
        self.sudden_caller = "players" if caller == "keeper" else "keeper"
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
