import json

import pytest

from coc_chase.chase import Chase, Hazard, Participant
from coc_chase.files import import_party, list_files, load_prep, new_chase, save_prep


def prepped_chase() -> Chase:
    chase = Chase(locations=["Market", "Alley", "Docks"], descriptions={1: "Dark and wet."})
    chase.add_hazard(0, Hazard("Crowd", "Dodge", "hard"))
    chase.add_hazard(1, Hazard("Gate", kind="barrier", hp=10, max_hp=10))
    chase.add(Participant("Cultist", "pursuer", dex=50, mov=8, speed_value=50, hp=11, max_hp=11))
    return chase


def test_save_as_then_load_keeps_locations_hazards_and_npcs(tmp_path):
    original = prepped_chase()
    save_prep(original, tmp_path / "docks.json")
    loaded = Chase()
    load_prep(loaded, tmp_path / "docks.json")
    assert loaded.locations == original.locations
    assert loaded.descriptions == original.descriptions
    assert loaded.hazards == original.hazards
    assert loaded.participants == original.participants


def write(path, data):
    path.write_text(json.dumps(data))
    return path


PARTY = {"version": 1, "investigators": [
    {"name": "Harvey", "side": "fleeing", "dex": 60, "mov": 7, "speed_value": 55, "hp": 10, "max_hp": 10}]}


def test_loading_a_chase_and_importing_a_party_is_ready_to_establish(tmp_path):
    save_prep(prepped_chase(), tmp_path / "docks.json")
    chase = Chase()
    load_prep(chase, tmp_path / "docks.json")
    import_party(chase, write(tmp_path / "party.json", PARTY))
    assert [p.name for p in chase.participants] == ["Cultist", "Harvey"]
    chase.set_speed_result("Cultist", "success")
    chase.set_speed_result("Harvey", "success")
    chase.establish()
    assert chase.round == 1


def test_loaded_prep_carries_no_live_state(tmp_path):
    chase = prepped_chase()
    import_party(chase, write(tmp_path / "party.json", PARTY))
    chase.set_speed_result("Cultist", "success")
    chase.set_speed_result("Harvey", "success")
    chase.establish()
    chase.move("Harvey")
    chase.set_debt("Cultist", 2)
    chase.get("Cultist").hp = 3
    save_prep(chase, tmp_path / "docks.json")
    loaded = Chase()
    load_prep(loaded, tmp_path / "docks.json")
    [npc] = loaded.participants  # the imported investigator is not an NPC
    assert (npc.name, npc.hp, npc.location, npc.debt, npc.speed_result) == ("Cultist", 11, 0, 0, None)
    assert loaded.round == 0
    assert loaded.log == ["R0: Loaded chase docks"]


def test_list_files_gives_json_names_and_tolerates_missing_folder(tmp_path):
    for name in ("b.json", "a.json", "notes.txt"):
        (tmp_path / name).write_text("{}")
    assert list_files(tmp_path) == ["a", "b"]
    assert list_files(tmp_path / "missing") == []


def test_blank_chase_clears_everything_and_is_undoable():
    chase = prepped_chase()
    new_chase(chase)
    assert chase.locations == [] and chase.participants == [] and chase.hazards == {}
    chase.undo()
    assert chase.locations == ["Market", "Alley", "Docks"]


def test_minimal_hand_written_chase_file_loads(tmp_path):
    path = write(tmp_path / "hand.json", {"version": 1, "locations": [{"name": "Road"}, {"name": "Bridge"}],
                                          "hazards": {"0": {"name": "Mud"}}})
    chase = Chase()
    load_prep(chase, path)
    assert chase.locations == ["Road", "Bridge"]
    assert chase.hazards == {0: Hazard("Mud")}
    assert chase.participants == []


@pytest.mark.parametrize("content", [
    "not json",
    "[]",
    json.dumps({"version": 99, "locations": []}),
    json.dumps({"version": 1}),
    json.dumps({"version": 1, "locations": ["Road"]}),
    json.dumps({"version": 1, "locations": [], "hazards": {"x": {"name": "Mud"}}}),
    json.dumps({"version": 1, "locations": [], "npcs": [{"name": "Cultist", "speed": 50}]}),
])
def test_invalid_chase_file_raises_value_error_and_leaves_chase_alone(tmp_path, content):
    path = tmp_path / "bad.json"
    path.write_text(content)
    chase = prepped_chase()
    before = chase.to_json()
    with pytest.raises(ValueError, match="bad.json"):
        load_prep(chase, path)
    with pytest.raises(ValueError, match="bad.json"):
        import_party(chase, path)
    assert chase.to_json() == before


def test_participant_notes_are_saved_in_prep_files(tmp_path):
    chase = Chase()
    chase.add(Participant("Cultist", "pursuer", dex=50, mov=8, speed_value=50, notes="Knife 40%"))
    save_prep(chase, tmp_path / "notes.json")
    loaded = Chase()
    load_prep(loaded, tmp_path / "notes.json")
    assert loaded.get("Cultist").notes == "Knife 40%"
