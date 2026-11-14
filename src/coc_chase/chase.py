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
class Participant:
    name: str
    side: str  # "pursuer" or "fleeing"
    dex: int
    mov: int
    speed_value: int
    speed_result: str | None = None  # "extreme" / "success" / "fail"
    location: int = 0  # index into Chase.locations
    actions_left: int = 0

    @property
    def adjusted_mov(self) -> int:
        return self.mov + SPEED_MOD.get(self.speed_result, 0)


@dataclass
class Chase:
    participants: list[Participant] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    escaped: list[str] = field(default_factory=list)
    round: int = 0  # 0 = not established yet
    slowest_mov: int = 0
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

    def get(self, name: str) -> Participant:
        return next(p for p in self.participants if p.name == name)

    @mutation
    def set_speed_result(self, name: str, result: str) -> None:
        p = self.get(name)
        p.speed_result = result
        self.log_event(f"{name} speed roll {result}, MOV {p.adjusted_mov}")

    @mutation
    def establish(self, start_range: int = 2) -> None:
        """One-on-one: escape check, or place pursuer `start_range` behind and start round 1."""
        # ponytail: one-on-one only; multi-participant placement/elimination is ticket 06
        fastest_pursuer = max(p.adjusted_mov for p in self.participants if p.side == "pursuer")
        self.escaped = [p.name for p in self.participants
                        if p.side == "fleeing" and p.adjusted_mov > fastest_pursuer]
        if self.escaped:
            self.log_event(f"{', '.join(self.escaped)} escapes, no chase is played")
            return
        for p in self.participants:
            p.location = start_range if p.side == "fleeing" else 0
        self.locations = [f"Location {i + 1}" for i in range(start_range + 2)]
        # Stored, not derived: leaving the chase must not recalculate movement actions.
        self.slowest_mov = min(p.adjusted_mov for p in self.participants)
        self.round = 1
        self._reset_actions()
        self.log_event(f"Chase established, range {start_range}")

    def movement_actions(self, p: Participant) -> int:
        return 1 + p.adjusted_mov - self.slowest_mov

    def dex_order(self) -> list[Participant]:
        return sorted(self.participants, key=lambda p: p.dex, reverse=True)

    def current_turn(self) -> Participant | None:
        return next((p for p in self.dex_order() if p.actions_left > 0), None)

    @mutation
    def move(self, name: str) -> None:
        p = self.get(name)
        p.actions_left -= 1
        p.location += 1
        while p.location >= len(self.locations):
            self.locations.append(f"Location {len(self.locations) + 1}")
        self.log_event(f"{name} moves → {self.locations[p.location]}")

    @mutation
    def end_round(self) -> None:
        self.round += 1
        self._reset_actions()
        self.log_event(f"Round {self.round} begins")

    def _reset_actions(self) -> None:
        for p in self.participants:
            p.actions_left = self.movement_actions(p)
