"""Prepped chase and party roster files: plain JSON with a version field. No UI imports."""

import json
from dataclasses import asdict, fields
from pathlib import Path

from coc_chase.chase import FORMAT_VERSION, Chase, Hazard, Participant, mutation

# Live state that never goes into a prep file.
LIVE = ("speed_result", "location", "actions_left", "debt")


def _prep_participant(p: Participant) -> dict:
    data = {k: v for k, v in asdict(p).items() if k not in LIVE}
    data["hp"] = p.max_hp
    return data


def save_prep(chase: Chase, path: Path) -> None:
    """Save as: locations, hazards and NPCs only, never positions, round or log."""
    data = {
        "version": FORMAT_VERSION,
        "locations": [{"name": n, "description": chase.descriptions.get(i, "")}
                      for i, n in enumerate(chase.locations)],
        "hazards": {str(i): asdict(h) for i, h in chase.hazards.items()},
        "npcs": [_prep_participant(p) for p in chase.participants if p.name not in chase.investigators],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _read(path: Path, build):
    """Parse a file with build(data). Any problem with it becomes one ValueError naming the file."""
    try:
        data = json.loads(path.read_text())
        if data.get("version") != FORMAT_VERSION:
            raise ValueError(f"unsupported version {data.get('version')!r}")
        return build(data)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as e:
        raise ValueError(f"{path.name}: {type(e).__name__}: {e}") from e


def _participants(items: list) -> list[Participant]:
    people = [Participant(**p) for p in items]  # tolerant: new fields with defaults just work
    for p in people:
        if not all(isinstance(getattr(p, k), int) for k in ("dex", "mov", "speed_value")):
            raise TypeError(f"{p.name}: dex, mov and speed_value must be whole numbers")
    return people


def _prep_chase(data: dict) -> Chase:
    locations = data["locations"]
    return Chase(
        locations=[str(loc["name"]) for loc in locations],
        descriptions={i: loc["description"] for i, loc in enumerate(locations) if loc.get("description")},
        hazards={int(i): Hazard(**h) for i, h in data.get("hazards", {}).items()},
        participants=_participants(data.get("npcs", [])),
    )


def list_files(folder: Path) -> list[str]:
    """Names (without .json) for a dropdown; a missing folder is just empty."""
    return sorted(p.stem for p in Path(folder).glob("*.json"))


def _replace(chase: Chase, fresh: Chase, message: str) -> None:
    for f in fields(chase):
        if f.compare:
            setattr(chase, f.name, getattr(fresh, f.name))
    chase.log_event(message)


@mutation
def new_chase(chase: Chase) -> None:
    """Start over with a blank chase (undoable)."""
    _replace(chase, Chase(), "New blank chase")


@mutation
def load_prep(chase: Chase, path: Path) -> None:
    """Replace the chase with a fresh one built from a prepped chase file (undoable)."""
    _replace(chase, _read(path, _prep_chase), f"Loaded chase {path.stem}")


@mutation
def import_party(chase: Chase, path: Path) -> None:
    """Add a party roster's investigators to the current chase (undoable)."""
    for p in _read(path, lambda data: _participants(data["investigators"])):
        chase.add(p)
        chase.investigators.append(p.name)
