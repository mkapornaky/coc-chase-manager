# Chase Manager

A Keeper-side chase tracker for **Call of Cthulhu 7th edition**. It runs the chase rules (chapter 7 of the Keeper Rulebook) in a local browser window, so you can keep your eyes on the players instead of the rulebook.

The app tracks the bookkeeping and leaves every call to the Keeper. Speed rolls, locations, hazards, DEX order, movement actions and their debt, vehicles and an event log all live in one screen. Every value can be edited by hand.

## Features

- **Setup:** add pursuers and fleeing characters, enter speed roll results (or roll for NPCs), and see who escapes before the chase even starts.
- **Track:** a horizontal row of locations with read-aloud descriptions. Hazards and barriers sit in the gaps between locations. Insert, edit or remove locations at any time.
- **Rounds:** DEX order with tie-breaking opposed DEX rolls, movement actions per round, and debt carried into the next round. You can reorder by hand and delay a character's turn.
- **Hazards and barriers:** pass or fail with cautious bonus dice, lose 1D3 actions, deal damage, smash barriers, and roll random hazards for quiet or hazardous environments.
- **Conflict:** attacks, maneuvers, free-text actions, and sudden-hazard calls (Keeper or players).
- **Vehicles:** build, ramming, Pedal to the Metal, passengers who ride along and navigate.
- **Join mid-chase:** latecomers roll speed and join at a location, or turn out too slow to keep up.
- **Dice roller:** D100 with bonus or penalty dice, plus monster fallbacks (full, half or one-fifth of a characteristic).
- **Undo** on every action, and an **autosave** that restores the chase if the app restarts.

## Install and run

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/mkapornaky/coc-chase-manager.git
cd coc-chase-manager
uv run chase-manager
```

This opens the app in your browser (NiceGUI serves it on `http://localhost:8080`).

To use a native window instead of a browser tab:

```sh
uv run --extra native chase-manager --native
```

## Files

The app reads and writes files in the directory you start it from:

| Path | What it holds |
|------|---------------|
| `autosave.json` | The live chase, written after every action. Delete it to start fresh. |
| `chases/*.json` | Prepped chases: locations, hazards and NPCs. Make one by building a chase and clicking **Save**. |
| `parties/*.json` | Party rosters. Use **Import party** to add the investigators to any chase. |

All three are git-ignored, so your own prep and rosters stay out of the repo. For a quick start, copy the samples from `examples/`:

```sh
mkdir -p chases parties
cp examples/chases/*.json chases/
cp examples/parties/*.json parties/
```

Prepped chases never store positions, rounds or the log, so you can reuse one as often as you like.

You write party rosters by hand. Only `name`, `dex`, `mov` and `speed_value` are required. There is no `side`: you pick pursuing or fleeing when you import, so one roster serves both (an old `side` field is ignored):

```json
{
  "version": 3,
  "investigators": [
    {"name": "Harvey Walters", "dex": 55, "mov": 7, "speed_value": 60, "hp": 11, "max_hp": 11},
    {"name": "Bessie Cooper", "dex": 70, "mov": 8, "speed_value": 75, "notes": "Drive Auto 60"}
  ]
}
```

Older version 1 and 2 files (rosters, prepped chases and the autosave) still load, and are written back as version 3.

`speed_value` is the skill or characteristic used for the speed roll (usually CON, or Drive Auto for a vehicle). Optional fields: `hp`, `max_hp`, `build` and `max_build` (setting these makes the participant a vehicle), `vehicle` (the name of the vehicle a passenger rides in) and `notes`.

## Development

```sh
uv run pytest
```

The rules live in `src/coc_chase/chase.py`, which has no UI imports. File handling is in `files.py`, and `ui.py` is a thin NiceGUI layer on top. Issues are tracked on GitHub.

## License

[MIT](LICENSE)
