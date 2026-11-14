import pytest

from coc_chase.chase import Chase, Participant
from test_setup import apartment_chase
from test_vehicles import passenger_chase


def test_edit_participant_fields_is_logged_and_undoable():
    chase = apartment_chase()
    chase.edit_participant("Harvey", mov=7, notes="sprained ankle")
    harvey = chase.get("Harvey")
    assert (harvey.mov, harvey.notes) == (7, "sprained ankle")
    assert chase.log[-1] == "R1: Harvey edited: mov 7, notes sprained ankle"
    chase.undo()
    assert (chase.get("Harvey").mov, chase.get("Harvey").notes) == (6, "")


def test_renaming_updates_every_reference():
    chase = passenger_chase()
    chase.investigators = ["Harvey"]
    chase.reorder(["Police 1", "Harvey", "Hilda"])
    chase.delay("Harvey")
    chase.edit_participant("Harvey", name="Harv")
    assert chase.get("Harv").dex == 70
    assert chase.order == ["Police 1", "Harv", "Hilda"]
    assert chase.delayed == ["Harv"]
    assert chase.get("Hilda").vehicle == "Harv"
    assert chase.investigators == ["Harv"]


def test_giving_a_build_makes_it_the_starting_build():
    chase = Chase()
    chase.add(Participant("Harvey", "fleeing", dex=55, mov=8, speed_value=50))
    chase.edit_participant("Harvey", build=4, hp=10)
    harvey = chase.get("Harvey")
    assert (harvey.max_build, harvey.max_hp) == (4, 10)
    assert chase.badges("Harvey") == []


def test_editing_an_unknown_field_raises():
    chase = apartment_chase()
    with pytest.raises(ValueError):
        chase.edit_participant("Harvey", speed=3)
