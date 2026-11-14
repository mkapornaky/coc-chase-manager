from coc_chase.chase import Chase, Hazard, Participant
from test_dice import FixedRng


def mud_chase(rng=None):
    """Harvey (MOV 5) vs farmer (MOV 6), mud in the gap ahead of the farmer."""
    chase = Chase(rng=rng) if rng else Chase()
    chase.add(Participant("Harvey", "fleeing", dex=55, mov=6, speed_value=60))
    chase.add(Participant("Farmer", "pursuer", dex=50, mov=7, speed_value=50, hp=12, max_hp=12))
    chase.set_speed_result("Harvey", "fail")
    chase.set_speed_result("Farmer", "fail")
    chase.establish()
    chase.add_hazard(1, Hazard("mud", skill="DEX", difficulty="regular", notes="slippery"))
    return chase


def test_mud_farmer_fails_with_no_actions_left_and_carries_one_debt():
    chase = mud_chase()
    chase.move("Harvey")
    chase.move("Farmer")  # 1 action left, mud ahead
    assert chase.hazard_ahead("Farmer").name == "mud"
    chase.resolve_hazard("Farmer", passed=False, lost=1, damage=2)
    farmer = chase.get("Farmer")
    assert farmer.location == 2
    assert farmer.actions_left == 0
    assert farmer.debt == 1
    assert farmer.hp == 10
    chase.end_round()
    assert farmer.actions_left == 1
    assert farmer.debt == 0


def test_cautious_bonus_dice_cost_one_action_each_capped_at_two():
    chase = mud_chase()
    farmer = chase.get("Farmer")
    farmer.location, farmer.actions_left = 1, 5
    chase.resolve_hazard("Farmer", passed=True, bonus=3)
    assert farmer.actions_left == 2  # 1 to cross + 2 bonus dice
    assert farmer.location == 2
    assert farmer.debt == 0
    assert chase.log[-1] == "R1: Farmer passes hazard mud (2 bonus dice)"


def test_failed_hazard_rolls_1d3_when_not_entered_and_logs_it():
    chase = mud_chase(rng=FixedRng(3))
    farmer = chase.get("Farmer")
    farmer.location = 1
    chase.resolve_hazard("Farmer", passed=False)  # 2 actions: 1 to cross, 3 lost
    assert (farmer.actions_left, farmer.debt, farmer.location) == (0, 2, 2)
    assert chase.log[-2:] == ["R1: Farmer lost actions 1D3: 3",
                              "R1: Farmer fails hazard mud, −3 actions, debt 2"]


def test_debt_larger_than_a_round_carries_over_again():
    chase = mud_chase()
    farmer = chase.get("Farmer")
    farmer.debt = 3
    chase.end_round()
    assert (farmer.actions_left, farmer.debt) == (0, 1)


def test_hazard_resolution_is_undoable_and_round_trips():
    chase = mud_chase()
    before = chase.to_json()
    chase.move("Farmer")
    chase.resolve_hazard("Farmer", passed=False, lost=2, damage=3)
    assert Chase.from_json(chase.to_json()) == chase
    chase.undo()
    chase.undo()
    assert chase.to_json() == before
