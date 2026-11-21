from coc_chase.chase import Chase, Participant
from test_dice import FixedRng


def apartment_chase(start_range=2, start_location=0):
    """Rulebook example: Brian, Scott and Harvey flee three cultists."""
    chase = Chase()
    for name, side, dex, mov, result in [
        ("Harvey", "fleeing", 55, 6, "fail"),
        ("Brian", "fleeing", 70, 8, "success"),
        ("Scott", "fleeing", 60, 9, "extreme"),
        ("Cultist A", "pursuer", 50, 8, "fail"),
        ("Cultist B", "pursuer", 50, 8, "fail"),
        ("Cultist C", "pursuer", 50, 8, "extreme"),
    ]:
        chase.add(Participant(name, side, dex=dex, mov=mov, speed_value=50))
        chase.set_speed_result(name, result)
    chase.establish(start_range, start_location)
    return chase


def locations(chase):
    return {p.name: p.location for p in chase.participants}


def test_mixed_group_places_per_rulebook_example():
    chase = apartment_chase()
    assert locations(chase) == {"Cultist A": 0, "Cultist B": 0, "Cultist C": 2,
                                "Harvey": 4, "Brian": 7, "Scott": 9}
    assert [chase.movement_actions(chase.get(n)) for n in ("Harvey", "Cultist A", "Brian", "Cultist C")] \
        == [1, 3, 4, 5]
    assert chase.round == 1
    assert len(chase.locations) > 9


def test_fast_fleeing_character_is_flagged_and_still_placed():
    chase = apartment_chase()
    assert chase.may_escape == ["Scott"]
    assert chase.escaped == []


def test_pursuer_slower_than_slowest_fleeing_is_left_behind():
    chase = Chase()
    chase.add(Participant("Harvey", "fleeing", dex=55, mov=6, speed_value=50))
    chase.add(Participant("Hound", "pursuer", dex=60, mov=8, speed_value=50))
    chase.add(Participant("Ghoul", "pursuer", dex=40, mov=5, speed_value=50))
    for name in ("Harvey", "Hound", "Ghoul"):
        chase.set_speed_result(name, "success")
    chase.establish()
    assert [p.name for p in chase.participants] == ["Harvey", "Hound"]
    assert locations(chase) == {"Hound": 0, "Harvey": 2}
    assert "R0: Ghoul is left behind" in chase.log


def names(participants):
    return [p.name for p in participants]


def test_dex_ties_are_flagged_and_resolved_by_manual_reorder():
    chase = apartment_chase()
    assert chase.dex_ties() == [["Cultist A", "Cultist B", "Cultist C"]]
    chase.reorder(["Brian", "Scott", "Harvey", "Cultist C", "Cultist A", "Cultist B"])
    assert names(chase.dex_order()) == ["Brian", "Scott", "Harvey", "Cultist C", "Cultist A", "Cultist B"]
    assert chase.dex_ties() == []
    assert chase.log[-1].startswith("R1: Order set: Brian, Scott")


def test_manual_reorder_can_override_dex_before_round_one():
    chase = apartment_chase()
    chase.reorder(["Harvey", "Brian", "Scott", "Cultist A", "Cultist B", "Cultist C"])
    assert chase.current_turn().name == "Harvey"


def test_dex_tie_resolved_by_opposed_dex_roll():
    chase = apartment_chase()
    # units then tens per D100: A rolls 80 (failure), B 05 (extreme), C 30 (hard)
    chase.rng = FixedRng(0, 8, 5, 0, 0, 3)
    chase.roll_dex_ties()
    assert names(chase.dex_order()) == ["Brian", "Scott", "Harvey", "Cultist B", "Cultist C", "Cultist A"]
    assert chase.dex_ties() == []


def test_keeper_adjusts_placement_and_movement_actions_logged():
    chase = apartment_chase()
    chase.set_location("Brian", 12)
    chase.set_actions("Harvey", 2)
    assert chase.get("Brian").location == 12
    assert len(chase.locations) > 12
    assert chase.get("Harvey").actions_left == 2
    assert chase.log[-2:] == ["R1: Brian placed on Location 13", "R1: Harvey movement actions set to 2"]


def test_same_location_flag():
    chase = apartment_chase()
    assert chase.same_location() == []
    chase.set_location("Cultist C", 4)
    assert chase.same_location() == [4]
    chase.set_location("Cultist A", 2)  # pursuers together: no flag
    chase.set_location("Cultist B", 2)
    assert chase.same_location() == [4]


def test_range_one_from_chosen_start_location():
    chase = apartment_chase(start_range=1, start_location=3)
    assert locations(chase) == {"Cultist A": 3, "Cultist B": 3, "Cultist C": 5,
                                "Harvey": 6, "Brian": 9, "Scott": 11}


def test_faster_fleeing_in_a_group_chase_may_escape_but_the_chase_starts():
    chase = Chase()
    chase.add(Participant("Harvey", "fleeing", dex=55, mov=9, speed_value=50))
    chase.add(Participant("Hound", "pursuer", dex=60, mov=8, speed_value=50))
    chase.add(Participant("Ghoul", "pursuer", dex=40, mov=7, speed_value=50))
    for name in ("Harvey", "Hound", "Ghoul"):
        chase.set_speed_result(name, "success")
    chase.establish()
    assert chase.escaped == []
    assert chase.may_escape == ["Harvey"]
    assert chase.round == 1
    assert "R0: Hound is left behind" in chase.log  # slower than the slowest fleeing character


def test_one_on_one_escape_ignores_passengers():
    chase = Chase()
    chase.add(Participant("Harvey", "fleeing", dex=55, mov=14, speed_value=50, build=5, max_build=5))
    chase.add(Participant("Hilda", "fleeing", dex=60, mov=7, speed_value=0, vehicle="Harvey"))
    chase.add(Participant("Police", "pursuer", dex=50, mov=13, speed_value=50, build=5, max_build=5))
    chase.set_speed_result("Harvey", "success")
    chase.set_speed_result("Police", "success")
    chase.establish()
    assert chase.escaped == ["Harvey"]


def test_identical_opposed_dex_results_are_rerolled_between_the_tied_only():
    chase = apartment_chase()
    # A and B both roll 30 (hard), C 05 (extreme); reroll: A 80 (failure), B 10 (hard)
    chase.rng = FixedRng(0, 3, 0, 3, 5, 0, 0, 8, 0, 1)
    chase.roll_dex_ties()
    assert names(chase.dex_order())[3:] == ["Cultist C", "Cultist B", "Cultist A"]


def tied_chase(*people):
    """(name, dex) pairs; names starting with "Inv" are investigators."""
    chase = Chase()
    for name, dex in people:
        chase.add(Participant(name, "pursuer", dex=dex, mov=8, speed_value=50, investigator=name.startswith("Inv")))
    return chase


def test_opposed_dex_roll_skips_ties_with_an_investigator():
    chase = tied_chase(("Inv Harvey", 50), ("Cultist", 50))
    chase.roll_dex_ties()
    assert not any("opposed DEX" in e for e in chase.log)
    assert chase.dex_ties() == [["Inv Harvey", "Cultist"]]


def test_reorder_resolves_only_the_ties_whose_relative_order_changed():
    chase = tied_chase(("A", 50), ("B", 50), ("C", 40), ("D", 40))
    chase.reorder(["A", "B", "D", "C"])
    assert chase.dex_ties() == [["A", "B"]]


def test_reorder_keeping_a_tie_in_place_leaves_it_flagged_until_kept():
    chase = tied_chase(("A", 50), ("B", 50), ("C", 60))
    chase.reorder(["A", "B", "C"])  # C moved, A still before B
    assert chase.dex_ties() == [["A", "B"]]
    chase.keep_dex_order(["A", "B"])
    assert chase.dex_ties() == []
    assert chase.log[-1] == "R0: DEX tie kept in order: A, B"
    chase.undo()
    assert chase.dex_ties() == [["A", "B"]]


def test_joining_a_resolved_tie_makes_a_new_tie():
    chase = tied_chase(("A", 50), ("B", 50))
    chase.keep_dex_order(["A", "B"])
    chase.add(Participant("C", "pursuer", dex=50, mov=8, speed_value=50))
    assert chase.dex_ties() == [["A", "B", "C"]]


def test_tie_state_round_trips():
    chase = tied_chase(("A", 50), ("B", 50), ("C", 40), ("D", 40))
    chase.keep_dex_order(["C", "D"])
    assert chase == Chase.from_json(chase.to_json())


def test_renaming_keeps_a_resolved_tie_resolved():
    chase = tied_chase(("A", 50), ("B", 50))
    chase.keep_dex_order(["A", "B"])
    chase.edit_participant("A", name="Alf")
    assert chase.dex_ties() == []


def test_a_tie_that_regains_its_old_members_is_flagged_again():
    chase = tied_chase(("A", 50), ("B", 50))
    chase.keep_dex_order(["A", "B"])
    chase.add(Participant("C", "pursuer", dex=50, mov=8, speed_value=50))
    chase.remove("C")
    assert chase.dex_ties() == [["A", "B"]]


def test_rolling_with_no_npc_ties_is_logged():
    chase = tied_chase(("Inv Harvey", 50), ("Cultist", 50))
    chase.roll_dex_ties()
    assert chase.log[-1] == "R0: No NPC DEX ties to roll"
