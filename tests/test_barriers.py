from coc_chase.chase import Chase, Hazard, Location, Participant
from test_dice import FixedRng


def fence_chase(rng=None):
    """Harvey (MOV 5) one location before a 5 HP fence, farmer behind him."""
    chase = Chase(rng=rng) if rng else Chase()
    chase.add(Participant("Harvey", "fleeing", dex=55, mov=6, speed_value=60))
    chase.add(Participant("Farmer", "pursuer", dex=50, mov=7, speed_value=50))
    chase.set_speed_result("Harvey", "fail")
    chase.set_speed_result("Farmer", "fail")
    chase.establish()
    chase.add_hazard(2, Hazard("fence", skill="Climb", kind="barrier", hp=5, max_hp=5))
    return chase


def test_fence_harvey_deals_3_fence_drops_to_2_and_harvey_stays():
    chase = fence_chase()
    chase.damage_barrier("Harvey", 3)
    harvey = chase.get("Harvey")
    assert chase.hazard_ahead("Harvey").hp == 2
    assert harvey.location == 2
    assert harvey.actions_left == 0
    assert chase.log[-1] == "R1: Harvey deals 3 damage to barrier fence (2/5 HP)"


def test_barrier_at_0_hp_is_no_longer_a_barrier():
    chase = fence_chase()
    chase.damage_barrier("Harvey", 7)
    assert chase.hazard_ahead("Harvey") is None
    assert chase.log[-1] == "R1: Harvey deals 7 damage to barrier fence (0/5 HP), broken"


def test_failed_barrier_roll_keeps_participant_in_place_without_1d3():
    chase = fence_chase()
    chase.resolve_hazard("Harvey", passed=False)
    harvey = chase.get("Harvey")
    assert (harvey.location, harvey.actions_left, harvey.debt) == (2, 0, 0)
    assert chase.log[-1] == "R1: Harvey fails barrier fence"


def test_passed_barrier_moves_participant_on():
    chase = fence_chase()
    chase.resolve_hazard("Harvey", passed=True)
    assert chase.get("Harvey").location == 3
    assert chase.log[-1] == "R1: Harvey passes barrier fence"


def test_moving_past_the_last_location_appends_a_blank_location():
    chase = fence_chase()
    harvey = chase.get("Harvey")
    harvey.location = len(chase.locations) - 1
    chase.move("Harvey")
    assert len(chase.locations) == harvey.location + 1


def test_locations_can_be_inserted_edited_and_removed_shifting_track():
    chase = fence_chase()  # Farmer on 0, Harvey on 2, fence after location 2
    chase.add_location(1, "Barn", "Smells of hay")
    assert chase.locations[1] == Location("Barn", "Smells of hay")
    assert chase.get("Harvey").location == 3
    assert chase.get("Farmer").location == 0
    assert chase.hazard_ahead("Harvey").name == "fence"
    chase.edit_location(1, "Old barn", "Roof caved in")
    assert chase.locations[1] == Location("Old barn", "Roof caved in")
    chase.remove_location(1)
    assert "Old barn" not in [loc.name for loc in chase.locations]
    assert chase.get("Harvey").location == 2
    assert chase.hazard_ahead("Harvey").name == "fence"


def test_a_location_keeps_its_description_and_hazard_when_the_track_changes():
    chase = Chase(locations=[Location("Market", hazard_after=Hazard("Crowd")), Location("Alley", "Dark"),
                             Location("Docks", hazard_after=Hazard("Gate"))])
    chase.add_location(0, "Square")
    assert chase.locations[1] == Location("Market", hazard_after=Hazard("Crowd"))
    chase.remove_location(1)  # Market goes, and the Crowd after it with it
    assert chase.locations == [Location("Square"), Location("Alley", "Dark"),
                               Location("Docks", hazard_after=Hazard("Gate"))]


def test_hazards_can_be_edited_and_removed():
    chase = fence_chase()
    chase.add_hazard(2, Hazard("wall", kind="barrier", hp=25, max_hp=25))
    assert chase.hazard_ahead("Harvey").name == "wall"
    chase.remove_hazard(2)
    assert chase.hazard_ahead("Harvey") is None
    assert chase.log[-1] == "R1: Hazard wall removed after Location 3"


def test_random_hazard_fills_gap_with_rolled_difficulty_and_logs_roll():
    chase = fence_chase(rng=FixedRng(5, 8))  # units 5, tens 8: 85
    chase.roll_random_hazard(0)
    assert chase.locations[0].hazard_after.difficulty == "hard"
    assert chase.log[-1] == "R1: Random hazard after Location 1 D100: 85 hard"


def test_random_hazard_penalty_die_keeps_higher_and_clear_keeps_the_existing_hazard():
    chase = fence_chase(rng=FixedRng(6, 9, 2))  # units 6, tens 9 and 2
    chase.roll_random_hazard(1, bonus=-1)
    assert chase.locations[1].hazard_after.difficulty == "extreme"
    chase.rng = FixedRng(9, 5, 0)  # bonus die keeps 09
    chase.roll_random_hazard(1, bonus=1)
    assert chase.locations[1].hazard_after.difficulty == "extreme"
    assert chase.log[-1] == "R1: Random hazard after Location 2 (1 bonus) D100: 9 clear"


def test_track_edits_round_trip_and_undo():
    chase = fence_chase()
    before = chase.to_json()
    chase.add_location(1, "Barn", "Smells of hay")
    chase.damage_barrier("Harvey", 3)
    chase.remove_location(0)
    assert Chase.from_json(chase.to_json()) == chase
    chase.undo()
    chase.undo()
    chase.undo()
    assert chase.to_json() == before


def test_nameless_location_is_named_by_its_number():
    chase = Chase()
    chase.add_location(0)
    chase.add_location(0, "")
    assert [loc.name for loc in chase.locations] == ["Location 1", "Location 1"]
    assert chase.log[-1] == "R0: Location 1 added"
    chase.add_location(2, "  ")
    assert chase.locations[2].name == "Location 3"
    chase.remove_location(2)
    assert chase.log[-1] == "R0: Location 3 removed"
    chase.add_location(0, "Barn")
    assert chase.log[-1] == "R0: Barn added"
