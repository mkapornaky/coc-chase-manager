import json

import pytest

from coc_chase.chase import Chase, Hazard, Location, Participant
from coc_chase.files import import_party, list_files, load_prep, new_chase, save_prep


def prepped_chase() -> Chase:
    chase = Chase(locations=[Location("Market"), Location("Alley", "Dark and wet."), Location("Docks")])
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
    assert chase.locations == [] and chase.participants == []
    chase.undo()
    assert [loc.name for loc in chase.locations] == ["Market", "Alley", "Docks"]


def test_minimal_hand_written_version_1_chase_file_loads(tmp_path):
    path = write(tmp_path / "hand.json", {"version": 1, "locations": [
        {"name": "Road"}, {"name": "Bridge", "description": "Rickety"}], "hazards": {"0": {"name": "Mud"}}})
    chase = Chase()
    load_prep(chase, path)
    assert chase.locations == [Location("Road", hazard_after=Hazard("Mud")), Location("Bridge", "Rickety")]
    assert chase.participants == []


def test_minimal_hand_written_version_2_chase_file_loads(tmp_path):
    path = write(tmp_path / "hand.json", {"version": 2, "locations": [
        {"name": "Road", "hazard_after": {"name": "Mud"}}, {"name": "Bridge", "description": "Rickety", "hazard_after": {}}]})
    chase = Chase()
    load_prep(chase, path)
    assert chase.locations == [Location("Road", hazard_after=Hazard("Mud")), Location("Bridge", "Rickety")]


def test_saved_chase_file_is_version_3_with_hazards_on_their_locations(tmp_path):
    save_prep(prepped_chase(), tmp_path / "docks.json")
    data = json.loads((tmp_path / "docks.json").read_text())
    assert data["version"] == 3
    assert "hazards" not in data
    assert data["locations"][1]["description"] == "Dark and wet."
    assert data["locations"][1]["hazard_after"]["name"] == "Gate"


def test_version_2_party_imports(tmp_path):
    chase = Chase()
    import_party(chase, write(tmp_path / "party.json", PARTY | {"version": 2}))
    assert chase.get("Harvey").investigator


V1_AUTOSAVE = {
    "version": 1, "round": 1, "slowest_mov": 7,
    "participants": [{"name": "Harvey", "side": "fleeing", "dex": 60, "mov": 7, "speed_value": 55,
                      "speed_result": "success", "location": 2, "actions_left": 1}],
    "locations": ["Market", "Alley", "Docks"],
    "descriptions": {"1": "Dark and wet."},
    "hazards": {"0": {"name": "Crowd", "skill": "Dodge", "difficulty": "hard"},
                "2": {"name": "Gate", "kind": "barrier", "hp": 10, "max_hp": 10}},
    "sudden_caller": "keeper", "log": ["R1: Chase established, range 2"],
}


def test_version_1_autosave_resumes_with_descriptions_and_hazards_on_their_locations(tmp_path):
    chase = Chase.load(write(tmp_path / "autosave.json", V1_AUTOSAVE))
    assert chase.locations == [
        Location("Market", hazard_after=Hazard("Crowd", "Dodge", "hard")),
        Location("Alley", "Dark and wet."),
        Location("Docks", hazard_after=Hazard("Gate", kind="barrier", hp=10, max_hp=10)),
    ]
    assert chase.hazard_ahead("Harvey").name == "Gate"
    assert (chase.round, chase.sudden_caller, chase.log) == (1, "keeper", V1_AUTOSAVE["log"])
    assert json.loads(chase.to_json())["version"] == 3


BAD_SIDE = {"name": "Cultist", "side": "persuer", "dex": 50, "mov": 8, "speed_value": 50}


@pytest.mark.parametrize("content", [
    "not json",
    "[]",
    json.dumps({"version": 99, "locations": []}),
    json.dumps({"version": 1}),
    json.dumps({"version": 1, "locations": ["Road"]}),
    json.dumps({"version": 1, "locations": [], "hazards": {"x": {"name": "Mud"}}}),
    json.dumps({"version": 1, "locations": [], "npcs": [{"name": "Cultist", "speed": 50}]}),
    json.dumps({"version": 1, "locations": [], "npcs": [BAD_SIDE], "investigators": [BAD_SIDE]}),
    json.dumps({"version": 1, "locations": [{"name": "Road"}], "hazards": {"0": {"name": "Mud", "kind": "bog"}}}),
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


def test_autosave_with_an_unknown_value_is_refused_naming_the_file(tmp_path):
    data = json.loads(Chase().to_json()) | {"sudden_caller": "dealer"}
    with pytest.raises(ValueError, match="autosave.json"):
        Chase.load(write(tmp_path / "autosave.json", data))


def left_behind_chase() -> Chase:
    """Fleeing MOV 8; pursuers MOV 6 (left behind at establish) and 9."""
    chase = Chase()
    chase.add(Participant("Harvey", "fleeing", dex=60, mov=8, speed_value=50))
    chase.add(Participant("Ghoul", "pursuer", dex=40, mov=6, speed_value=50, hp=13, max_hp=13))
    chase.add(Participant("Hound", "pursuer", dex=70, mov=9, speed_value=50))
    for name in ("Harvey", "Ghoul", "Hound"):
        chase.set_speed_result(name, "success")
    chase.establish()
    return chase


def test_save_as_after_establish_keeps_pursuers_left_behind(tmp_path):
    chase = left_behind_chase()
    chase.get("Harvey").investigator = True
    save_prep(chase, tmp_path / "prep.json")
    npcs = json.loads((tmp_path / "prep.json").read_text())["npcs"]
    assert sorted(n["name"] for n in npcs) == ["Ghoul", "Hound"]
    ghoul = next(n for n in npcs if n["name"] == "Ghoul")
    assert (ghoul["hp"], ghoul["mov"]) == (13, 6)
    assert "speed_result" not in ghoul and "location" not in ghoul


def test_left_behind_pursuer_is_out_of_the_running_chase():
    chase = left_behind_chase()
    assert [p.name for p in chase.left_behind] == ["Ghoul"]
    assert [p.name for p in chase.dex_order()] == ["Hound", "Harvey"]
    assert chase.targets("Harvey") == ["Hound"]
    assert chase.slowest_mov == 8
    with pytest.raises(StopIteration):
        chase.get("Ghoul")


def test_left_behind_round_trips_and_undo_restores_the_pursuer():
    chase = left_behind_chase()
    assert chase == Chase.from_json(chase.to_json())
    chase.undo()
    assert chase.left_behind == []
    assert "Ghoul" in [p.name for p in chase.participants]


def test_autosave_without_left_behind_loads():
    data = json.loads(Chase().to_json())
    del data["left_behind"]
    assert Chase.from_json(json.dumps(data)).left_behind == []


def test_hand_added_investigators_are_not_saved_as_npcs(tmp_path):
    chase = prepped_chase()
    chase.add(Participant("Harvey", "fleeing", dex=60, mov=7, speed_value=55, investigator=True))
    save_prep(chase, tmp_path / "prep.json")
    [npc] = json.loads((tmp_path / "prep.json").read_text())["npcs"]
    assert npc["name"] == "Cultist" and "investigator" not in npc


def test_version_2_autosave_marks_listed_investigators():
    data = json.loads(Chase().to_json()) | {"version": 2, "investigators": ["Harvey"], "participants": [
        {"name": "Harvey", "side": "fleeing", "dex": 60, "mov": 7, "speed_value": 55},
        {"name": "Cultist", "side": "pursuer", "dex": 50, "mov": 8, "speed_value": 50}]}
    for key in ("left_behind", "resolved_ties"):
        data.pop(key, None)
    chase = Chase.from_json(json.dumps(data))
    assert [p.investigator for p in chase.participants] == [True, False]
    assert chase == Chase.from_json(chase.to_json())
