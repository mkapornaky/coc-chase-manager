from coc_chase.chase import Chase, Hazard, Participant
from test_dice import FixedRng


def car(name, side, dex=50, mov=14, build=5, **kw):
    return Participant(name, side, dex=dex, mov=mov, speed_value=50, build=build, max_build=build, **kw)


def test_vehicle_badges_follow_build():
    chase = Chase()
    chase.add(car("Police 1", "pursuer", build=5))
    chase.set_build("Police 1", 3)
    assert chase.badges("Police 1") == []
    chase.set_build("Police 1", 2)  # half of 5, rounded down
    assert chase.badges("Police 1") == ["impaired: 1 penalty die"]
    chase.set_build("Police 1", 0)
    assert chase.badges("Police 1") == ["undriveable"]
    assert chase.log[-1] == "R0: Police 1 build set to 0"


def police_chase():
    """Rulebook p. 140: Harvey (1 action) chased by two police cars (2 actions)."""
    chase = Chase()
    chase.add(car("Harvey", "fleeing", dex=70, mov=14))
    chase.add(car("Police 1", "pursuer", dex=50, mov=15))
    chase.add(car("Police 2", "pursuer", dex=40, mov=15))
    for name in ("Harvey", "Police 1", "Police 2"):
        chase.set_speed_result(name, "success")
    chase.establish()
    chase.set_location("Police 1", 0)
    chase.set_location("Police 2", 1)
    chase.set_location("Harvey", 3)
    chase.add_hazard(1, Hazard("delivery truck", skill="Drive Auto"))
    return chase


def test_police_car_example():
    chase = police_chase()
    harvey, p1, p2 = (chase.get(n) for n in ("Harvey", "Police 1", "Police 2"))
    assert (harvey.actions_left, p1.actions_left, p2.actions_left) == (1, 2, 2)

    chase.pedal_to_the_metal("Harvey", 2)
    assert (harvey.location, harvey.actions_left) == (5, 0)
    assert chase.log[-1] == "R1: Harvey puts the pedal to the metal: 2 locations (1 penalty die) → Location 6"

    chase.resolve_hazard("Police 2", passed=False, lost=2, damage=1)
    assert (p2.location, p2.build, p2.debt) == (2, 4, 1)

    chase.pedal_to_the_metal("Police 1", 3)
    assert p1.location == 1  # stopped at the truck
    assert chase.badges("Police 1") == ["pedal to the metal: 1 penalty die"]
    chase.resolve_hazard("Police 1", passed=True)
    assert (p1.location, p1.actions_left) == (3, 1)  # through the truck, full 3 locations, no extra cost
    assert chase.badges("Police 1") == []
    chase.pedal_to_the_metal("Police 1", 2)
    assert (p1.location, p1.actions_left) == (harvey.location, 0)


def test_failed_hazard_stops_acceleration_and_shows_2_penalty_dice():
    chase = police_chase()
    p1 = chase.get("Police 1")
    chase.pedal_to_the_metal("Police 1", 5)
    assert chase.badges("Police 1") == ["pedal to the metal: 2 penalty dice"]
    chase.resolve_hazard("Police 1", passed=False, lost=0)
    assert (p1.location, p1.actions_left) == (2, 1)  # crossed the truck, then stopped
    assert chase.badges("Police 1") == []
    chase.move("Police 1")  # further movement costs a new action
    assert (p1.location, p1.actions_left) == (3, 0)


def test_vehicle_smashes_barrier_with_1d10_per_build():
    chase = police_chase()
    chase.rng = FixedRng(3, 4, 5, 6, 7)
    chase.add_hazard(0, Hazard("roadblock", kind="barrier", hp=30, max_hp=30))
    chase.damage_barrier("Police 1")
    assert chase.hazards[0].hp == 5
    assert chase.log[-2] == "R1: Police 1 barrier damage 5D10: 25"


def passenger_chase():
    """Police chase with Hilda (DEX 60, MOV 7, no speed roll) riding with Harvey."""
    chase = Chase()
    chase.add(car("Harvey", "fleeing", dex=70, mov=14))
    chase.add(Participant("Hilda", "fleeing", dex=60, mov=7, speed_value=0, vehicle="Harvey"))
    chase.add(car("Police 1", "pursuer", dex=50, mov=15))
    chase.set_speed_result("Harvey", "success")
    chase.set_speed_result("Police 1", "success")
    chase.establish()
    return chase


def test_passenger_ignored_for_slowest_mov_rides_along_and_acts_once_in_dex_order():
    chase = passenger_chase()
    harvey, hilda = chase.get("Harvey"), chase.get("Hilda")
    assert chase.slowest_mov == 14
    assert (harvey.actions_left, chase.get("Police 1").actions_left, hilda.actions_left) == (1, 2, 1)
    assert hilda.location == harvey.location
    assert chase.badges("Hilda") == ["passenger in Harvey"]
    assert [p.name for p in chase.dex_order()] == ["Harvey", "Hilda", "Police 1"]
    chase.move("Harvey")
    assert hilda.location == harvey.location
    assert chase.current_turn() is hilda


def test_passenger_navigation_reduces_next_pedal_penalty_by_1_die():
    chase = passenger_chase()
    chase.navigate("Hilda", passed=True)
    assert chase.get("Hilda").actions_left == 0
    assert chase.log[-1] == "R1: Hilda navigates for Harvey: next Pedal to the Metal −1 penalty die"
    chase.pedal_to_the_metal("Harvey", 4)
    assert "(1 penalty die)" in chase.log[-1]
    chase.end_round()
    chase.pedal_to_the_metal("Harvey", 4)  # used up
    assert "(2 penalty dice)" in chase.log[-1]


def test_passenger_joining_does_not_change_slowest_mov():
    chase = police_chase()
    chase.join(Participant("Hilda", "fleeing", dex=60, mov=7, speed_value=0, vehicle="Harvey"), 0)
    assert chase.slowest_mov == 14
    assert chase.get("Hilda").location == chase.get("Harvey").location
    assert chase.get("Hilda").actions_left == 1
    assert chase.get("Police 1").actions_left == 2


def test_vehicle_and_passenger_fields_round_trip():
    chase = passenger_chase()
    chase.pedal_to_the_metal("Harvey", 2)
    assert chase == Chase.from_json(chase.to_json())


def test_vehicle_stopped_at_hazard_mid_acceleration_keeps_the_turn():
    chase = police_chase()
    chase.add_hazard(3, Hazard("roadworks"))
    chase.pedal_to_the_metal("Harvey", 3)
    harvey = chase.get("Harvey")
    assert (harvey.location, harvey.actions_left) == (3, 0)
    assert chase.current_turn() is harvey
    chase.resolve_hazard("Harvey", passed=True)
    assert (harvey.location, harvey.actions_left, harvey.debt) == (6, 0, 0)
    assert chase.current_turn() is chase.get("Police 1")


def test_prep_file_keeps_vehicle_at_full_build_without_live_acceleration(tmp_path):
    from coc_chase.files import load_prep, save_prep
    chase = police_chase()
    chase.set_build("Police 1", 1)
    chase.get("Police 1").navigated = True
    chase.pedal_to_the_metal("Police 2", 2)  # stops at the truck
    save_prep(chase, tmp_path / "prep.json")
    loaded = Chase()
    load_prep(loaded, tmp_path / "prep.json")
    p1, p2 = (loaded.get(n) for n in ("Police 1", "Police 2"))
    assert (p1.build, p1.max_build, p1.navigated) == (5, 5, False)
    assert (p2.pedal, p2.pedal_penalty) == (0, 0)
