import random

from coc_chase.chase import Chase, Participant, fallback_targets, success_level


class FixedRng:
    """Returns the given randint values in order (units die first, then tens dice)."""
    def __init__(self, *values):
        self.values = list(values)

    def randint(self, a, b):
        v = self.values.pop(0)
        assert a <= v <= b
        return v


def test_d100_bonus_die_keeps_lowest_tens_penalty_keeps_highest():
    # units 3, tens dice 7 and 2
    assert Chase(rng=FixedRng(3, 7, 2)).roll_d100(50, bonus=1) == (23, "hard")
    assert Chase(rng=FixedRng(3, 7, 2)).roll_d100(50, bonus=-1) == (73, "failure")


def test_result_levels_follow_7e_thresholds():
    assert success_level(1, 10) == "critical"
    assert success_level(10, 50) == "extreme"
    assert success_level(11, 50) == "hard"
    assert success_level(25, 50) == "hard"
    assert success_level(50, 50) == "regular"
    assert success_level(51, 50) == "failure"
    assert success_level(96, 49) == "fumble"
    assert success_level(96, 50) == "failure"
    assert success_level(99, 99) == "regular"
    assert success_level(100, 99) == "fumble"


def test_d100_zero_zero_is_100():
    assert Chase(rng=FixedRng(0, 0)).roll_d100(99) == (100, "fumble")
    # bonus die: 00+0 is 100, so the 30 is kept
    assert Chase(rng=FixedRng(0, 0, 3)).roll_d100(50, bonus=1) == (30, "regular")


def test_nxdy_sums_count_dice_of_given_size():
    chase = Chase(rng=FixedRng(4, 10))
    assert chase.roll(2, 10) == 14
    assert chase.log == ["R0: 2D10: 14"]


def test_npc_speed_roll_sets_speed_result_and_logs():
    chase = Chase(rng=FixedRng(5, 0))  # rolls 05 vs 50: extreme
    chase.add(Participant("Cultist", "pursuer", dex=50, mov=8, speed_value=50))
    chase.roll_speed("Cultist")
    assert chase.get("Cultist").speed_result == "extreme"
    assert chase.get("Cultist").adjusted_mov == 9
    assert chase.log[-2] == "R0: Cultist speed roll D100 vs 50: 5 extreme"


def test_d100_log_shows_inputs_and_result():
    chase = Chase(rng=FixedRng(3, 7, 2))
    chase.roll_d100(40, bonus=-1, label="Farmer Jump")
    assert chase.log == ["R0: Farmer Jump D100 vs 40 (1 penalty): 73 failure"]


def test_fallback_offers_full_half_fifth():
    assert fallback_targets(55) == {"full": 55, "half": 27, "fifth": 11}


def test_nested_roll_undoes_in_one_step():
    chase = Chase(rng=FixedRng(5, 0))
    chase.add(Participant("Cultist", "pursuer", dex=50, mov=8, speed_value=50))
    chase.roll_speed("Cultist")
    chase.undo()
    assert chase.get("Cultist").speed_result is None
    assert len(chase.history) == 1


def test_seeded_rng_is_reproducible():
    rolls = [Chase(rng=random.Random(7)).roll_d100(50, bonus=2) for _ in range(2)]
    assert rolls[0] == rolls[1]
