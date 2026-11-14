from coc_chase.chase import Chase, Participant


def harvey_vs_farmer(harvey_result, farmer_result):
    chase = Chase()
    chase.add(Participant("Harvey", "fleeing", dex=55, mov=6, speed_value=60))
    chase.add(Participant("Farmer", "pursuer", dex=50, mov=7, speed_value=50))
    chase.set_speed_result("Harvey", harvey_result)
    chase.set_speed_result("Farmer", farmer_result)
    chase.establish()
    return chase


def test_faster_fleeing_character_escapes_one_on_one():
    chase = harvey_vs_farmer("extreme", "fail")
    assert chase.get("Harvey").adjusted_mov == 7
    assert chase.get("Farmer").adjusted_mov == 6
    assert chase.escaped == ["Harvey"]
    assert chase.locations == []


def test_slower_fleeing_character_starts_two_locations_ahead():
    chase = harvey_vs_farmer("fail", "fail")  # Harvey 5, farmer 6
    assert chase.escaped == []
    harvey, farmer = chase.get("Harvey"), chase.get("Farmer")
    assert harvey.location - farmer.location == 2
    assert len(chase.locations) > harvey.location
    assert chase.movement_actions(farmer) == 2
    assert chase.movement_actions(harvey) == 1
    assert [p.name for p in chase.dex_order()] == ["Harvey", "Farmer"]
    assert chase.current_turn() is harvey
    assert chase.round == 1


def test_round_one_closes_the_gap_to_one():
    chase = harvey_vs_farmer("fail", "fail")
    chase.move("Harvey")
    assert chase.current_turn().name == "Farmer"
    chase.move("Farmer")
    chase.move("Farmer")
    assert chase.current_turn() is None
    assert chase.get("Harvey").location - chase.get("Farmer").location == 1


def test_end_round_resets_movement_actions():
    chase = harvey_vs_farmer("fail", "fail")
    chase.move("Harvey")
    chase.end_round()
    assert chase.round == 2
    assert chase.get("Harvey").actions_left == 1
    assert chase.get("Farmer").actions_left == 2
    assert chase.current_turn().name == "Harvey"


def test_moving_past_last_location_adds_one():
    chase = harvey_vs_farmer("fail", "fail")
    harvey = chase.get("Harvey")
    harvey.location = len(chase.locations) - 1
    chase.move("Harvey")
    assert harvey.location == len(chase.locations) - 1


def test_chase_module_has_no_ui_imports():
    import coc_chase.chase as module
    from pathlib import Path
    assert "nicegui" not in Path(module.__file__).read_text()
