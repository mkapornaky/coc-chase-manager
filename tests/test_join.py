from coc_chase.chase import Chase, Participant
from test_setup import apartment_chase


def test_new_slowest_joiner_recalculates_everyone_keeping_spent_actions():
    chase = apartment_chase()  # slowest MOV 5 (Harvey)
    chase.move("Cultist A")  # 3 actions -> 2 left
    chase.join(Participant("Old Man", "fleeing", dex=40, mov=5, speed_value=40), 6, "fail")
    old_man = chase.get("Old Man")
    assert old_man.location == 6
    assert old_man.adjusted_mov == 4
    assert chase.movement_actions(chase.get("Cultist A")) == 4
    assert chase.get("Cultist A").actions_left == 3
    assert chase.get("Harvey").actions_left == 2
    assert old_man.actions_left == 1
    assert chase == Chase.from_json(chase.to_json())


def test_too_slow_joining_pursuer_is_flagged_and_changes_nothing():
    chase = apartment_chase()  # slowest fleeing MOV 5 (Harvey)
    chase.join(Participant("Cultist D", "pursuer", dex=50, mov=5, speed_value=50), 0, "fail")
    assert chase.unable_to_join == ["Cultist D"]
    assert "Cultist D" not in [p.name for p in chase.participants]
    assert chase.slowest_mov == 5
    assert chase.get("Harvey").actions_left == 1


def test_pursuer_matching_slowest_fleeing_joins():
    chase = apartment_chase()
    chase.join(Participant("Cultist D", "pursuer", dex=50, mov=5, speed_value=50), 1, "success")
    assert chase.unable_to_join == []
    assert chase.get("Cultist D").actions_left == 1


def test_leaving_never_recalculates():
    chase = apartment_chase()  # Harvey is the slowest, MOV 5
    chase.remove("Harvey")
    assert "Harvey" not in [p.name for p in chase.participants]
    assert chase.slowest_mov == 5
    assert chase.get("Cultist A").actions_left == 3
    chase.end_round()
    assert chase.get("Cultist A").actions_left == 3
    assert chase.log[-2] == "R1: Harvey leaves the chase"
