from coc_chase.chase import Chase
from test_hazards import mud_chase


def test_maneuver_costs_attacker_one_action_and_target_carries_debt():
    chase = mud_chase()
    harvey, farmer = chase.get("Harvey"), chase.get("Farmer")
    farmer.location, farmer.actions_left = harvey.location, 1
    harvey.actions_left = 1
    chase.maneuver("Farmer", "Harvey", lost=3, damage=2)
    assert farmer.actions_left == 0
    assert harvey.actions_left == 0
    assert harvey.debt == 2
    assert harvey.location == 2  # a maneuver does not move the target
    chase.end_round()
    assert harvey.actions_left == 0  # 1 action next round, paid to debt
    assert harvey.debt == 1


def test_attack_and_other_action_each_cost_one_action_and_are_logged():
    chase = mud_chase()
    farmer = chase.get("Farmer")
    farmer.actions_left = 2
    chase.attack("Farmer", "Harvey")
    chase.other_action("Farmer", "picks the lock")
    assert farmer.actions_left == 0
    assert farmer.location == 0
    assert "Farmer attacks Harvey" in chase.log[-2]
    assert "picks the lock" in chase.log[-1]


def test_delay_moves_participant_to_the_end_of_this_round_only():
    chase = mud_chase()  # Harvey DEX 55 acts before Farmer DEX 50
    assert chase.current_turn().name == "Harvey"
    chase.delay("Harvey")
    assert chase.current_turn().name == "Farmer"
    assert [p.name for p in chase.turn_order()] == ["Farmer", "Harvey"]
    chase.end_round()
    assert chase.current_turn().name == "Harvey"


def test_sudden_hazard_caller_alternates_and_either_side_may_call_first():
    chase = mud_chase()
    assert chase.sudden_caller is None  # either side
    chase.call_sudden_hazard("players")
    assert chase.sudden_caller == "keeper"
    chase.call_sudden_hazard("keeper")
    assert chase.sudden_caller == "players"
    assert Chase.from_json(chase.to_json()) == chase


def test_overrides_set_location_actions_and_debt_and_are_logged():
    chase = mud_chase()
    chase.set_override("Farmer", location=6, actions_left=3, debt=1)
    farmer = chase.get("Farmer")
    assert (farmer.location, farmer.actions_left, farmer.debt) == (6, 3, 1)
    assert len(chase.locations) == 7
    assert "Farmer override" in chase.log[-1]


def test_end_chase_stops_the_round_flow():
    chase = mud_chase()
    chase.end_chase()
    assert chase.current_turn() is None
    chase.end_round()
    assert chase.round == 1
