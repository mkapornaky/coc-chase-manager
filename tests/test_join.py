import pytest

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


def test_joiner_takes_their_dex_place_in_a_set_order():
    chase = Chase()
    chase.add(Participant("Harvey", "fleeing", dex=55, mov=8, speed_value=50))
    chase.add(Participant("Cultist", "pursuer", dex=30, mov=8, speed_value=50))
    chase.set_speed_result("Harvey", "success")
    chase.set_speed_result("Cultist", "success")
    chase.establish()
    chase.reorder(["Harvey", "Cultist"])
    chase.join(Participant("Ghoul", "pursuer", dex=90, mov=8, speed_value=50), 0, "success")
    assert [p.name for p in chase.dex_order()] == ["Ghoul", "Harvey", "Cultist"]


@pytest.mark.parametrize("dex, expected", [
    (50, ["Harvey", "Brian", "New", "Cultist"]),
    (20, ["Harvey", "Brian", "Cultist", "New"]),
    (90, ["New", "Harvey", "Brian", "Cultist"]),
    (70, ["Harvey", "Brian", "New", "Cultist"]),
])
def test_joiner_placement_keeps_the_keepers_order(dex, expected):
    chase = Chase()
    for name, d in (("Harvey", 40), ("Brian", 70), ("Cultist", 30)):
        chase.add(Participant(name, "fleeing", dex=d, mov=8, speed_value=50))
    chase.reorder(["Harvey", "Brian", "Cultist"])
    chase.add(Participant("New", "pursuer", dex=dex, mov=8, speed_value=50))
    assert [p.name for p in chase.dex_order()] == expected
    assert chase.dex_ties() == ([["Brian", "New"]] if dex == 70 else [])


def test_without_a_set_order_highest_dex_goes_first():
    chase = Chase()
    for name, d in (("Harvey", 40), ("Brian", 70), ("Cultist", 30)):
        chase.add(Participant(name, "fleeing", dex=d, mov=8, speed_value=50))
    assert [p.name for p in chase.dex_order()] == ["Brian", "Harvey", "Cultist"]


def test_joiner_goes_right_after_the_participant_sharing_their_dex():
    chase = Chase()
    for name, d in (("A", 50), ("B", 80)):
        chase.add(Participant(name, "fleeing", dex=d, mov=8, speed_value=50))
    chase.reorder(["A", "B"])
    chase.add(Participant("New", "pursuer", dex=50, mov=8, speed_value=50))
    assert [p.name for p in chase.dex_order()] == ["A", "New", "B"]
