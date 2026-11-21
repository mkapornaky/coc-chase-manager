from coc_chase.chase import Chase, Participant
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


def test_debt_override_is_paid_next_round_and_logged():
    chase = mud_chase()
    chase.set_debt("Farmer", 1)
    assert "Farmer debt set to 1" in chase.log[-1]
    chase.end_round()
    farmer = chase.get("Farmer")
    assert (farmer.actions_left, farmer.debt) == (1, 0)  # 2 actions, 1 paid


def test_end_chase_stops_the_round_flow():
    chase = mud_chase()
    chase.end_chase()
    assert chase.current_turn() is None
    chase.end_round()
    assert chase.round == 1


def test_targets_are_participants_on_the_other_side():
    from test_setup import apartment_chase
    chase = apartment_chase()
    assert chase.targets("Harvey") == ["Cultist A", "Cultist B", "Cultist C"]
    assert chase.targets("Cultist A") == ["Harvey", "Brian", "Scott"]


def test_had_turn_marks_participants_before_the_current_turn():
    chase = mud_chase()  # Harvey DEX 55 acts before Farmer DEX 50
    assert not chase.had_turn("Harvey") and not chase.had_turn("Farmer")
    chase.delay("Harvey")
    assert chase.current_turn().name == "Farmer"
    assert not chase.had_turn("Harvey")  # delayed: still to act
    chase.attack("Farmer", "Harvey")
    chase.other_action("Farmer", "shouts")
    assert chase.had_turn("Farmer") and not chase.had_turn("Harvey")
    chase.end_round()
    assert not chase.had_turn("Harvey") and not chase.had_turn("Farmer")


def test_nobody_has_had_a_turn_in_setup_or_after_the_chase_ends():
    setup = Chase()
    setup.add(Participant("Harvey", "fleeing", dex=55, mov=6, speed_value=60))
    assert not chase_had_any_turn(setup)
    chase = mud_chase()
    chase.move("Harvey")
    chase.end_chase()
    assert not chase_had_any_turn(chase)


def chase_had_any_turn(chase):
    return any(chase.had_turn(p.name) for p in chase.participants)
