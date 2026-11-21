import json

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


def test_json_round_trip_gives_equal_state():
    chase = harvey_vs_farmer("fail", "fail")
    chase.move("Harvey")
    data = json.loads(chase.to_json())
    assert data["version"] == 2
    assert Chase.from_json(chase.to_json()) == chase


def test_mutations_write_round_tagged_log_lines():
    chase = harvey_vs_farmer("fail", "fail")
    chase.move("Farmer")
    assert chase.log[-1] == "R1: Farmer moves → Location 2"
    assert chase.log[0] == "R0: Harvey (fleeing) joins"


def test_undo_after_move_restores_position_and_log():
    chase = harvey_vs_farmer("fail", "fail")
    log = list(chase.log)
    chase.move("Harvey")
    chase.move("Farmer")
    chase.undo()
    chase.undo()
    assert chase.get("Harvey").location == 2
    assert chase.get("Farmer").location == 0
    assert chase.log == log
    assert chase.current_turn().name == "Harvey"


def test_mutation_entries_are_kept_for_notification_and_undo():
    chase = Chase()
    assert chase.undo() is None
    chase = harvey_vs_farmer("fail", "fail")
    start = len(chase.log)
    chase.move("Harvey")
    chase.move("Farmer")
    entries = chase.log[start + 1:]
    assert entries and chase.last_entries == entries
    assert chase.undo() == entries
    assert len(chase.log) == start + 1


def test_every_mutation_autosaves_and_load_resumes(tmp_path):
    path = tmp_path / "autosave.json"
    chase = Chase.load(path)
    chase.add(Participant("Harvey", "fleeing", dex=55, mov=6, speed_value=60))
    assert Chase.load(path) == chase
    chase.add(Participant("Farmer", "pursuer", dex=50, mov=7, speed_value=50))
    chase.set_speed_result("Harvey", "fail")
    chase.set_speed_result("Farmer", "fail")
    chase.establish()
    chase.move("Harvey")
    assert Chase.load(path) == chase
    chase.undo()
    resumed = Chase.load(path)
    assert resumed == chase
    assert resumed.get("Harvey").location == 2
