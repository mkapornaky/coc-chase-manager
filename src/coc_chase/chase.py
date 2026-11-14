"""Pure chase logic (CoC 7e, chapter 7). No UI imports."""

import random
from dataclasses import dataclass, field

SPEED_MOD = {"extreme": 1, "success": 0, "fail": -1}


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
    rng: random.Random = field(default_factory=random.Random, repr=False, compare=False)

    def add(self, participant: Participant) -> None:
        self.participants.append(participant)

    def get(self, name: str) -> Participant:
        return next(p for p in self.participants if p.name == name)

    def set_speed_result(self, name: str, result: str) -> None:
        self.get(name).speed_result = result

    def establish(self, start_range: int = 2) -> None:
        """One-on-one: escape check, or place pursuer `start_range` behind and start round 1."""
        # ponytail: one-on-one only; multi-participant placement/elimination is ticket 06
        fastest_pursuer = max(p.adjusted_mov for p in self.participants if p.side == "pursuer")
        self.escaped = [p.name for p in self.participants
                        if p.side == "fleeing" and p.adjusted_mov > fastest_pursuer]
        if self.escaped:
            return
        for p in self.participants:
            p.location = start_range if p.side == "fleeing" else 0
        self.locations = [f"Location {i + 1}" for i in range(start_range + 2)]
        # Stored, not derived: leaving the chase must not recalculate movement actions.
        self.slowest_mov = min(p.adjusted_mov for p in self.participants)
        self.round = 1
        self._reset_actions()

    def movement_actions(self, p: Participant) -> int:
        return 1 + p.adjusted_mov - self.slowest_mov

    def dex_order(self) -> list[Participant]:
        return sorted(self.participants, key=lambda p: p.dex, reverse=True)

    def current_turn(self) -> Participant | None:
        return next((p for p in self.dex_order() if p.actions_left > 0), None)

    def move(self, name: str) -> None:
        p = self.get(name)
        p.actions_left -= 1
        p.location += 1
        while p.location >= len(self.locations):
            self.locations.append(f"Location {len(self.locations) + 1}")

    def end_round(self) -> None:
        self.round += 1
        self._reset_actions()

    def _reset_actions(self) -> None:
        for p in self.participants:
            p.actions_left = self.movement_actions(p)
