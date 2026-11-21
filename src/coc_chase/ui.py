"""Thin NiceGUI layer: renders a Chase and calls its operations. No rules here."""

import argparse
from pathlib import Path

from nicegui import ui

from coc_chase.chase import (PEDAL_DISTANCES, Caller, Chase, Difficulty, Hazard, HazardKind, Participant, Side,
                              SpeedResult, fallback_targets)
from coc_chase.files import import_party, list_files, load_prep, new_chase, save_prep

# ponytail: one global chase per process; the Keeper is the only user
chase = Chase.load(Path("autosave.json"))
CHASES, PARTIES = Path("chases"), Path("parties")


def notify(lines: list[str]) -> None:
    """One notification for an action, one line per log entry."""
    if lines:
        ui.notify("\n".join(lines), multi_line=True, classes="whitespace-pre-line")


def refuse(reason: str) -> None:
    """A click that changed nothing: say why. Never logged."""
    ui.notify(reason, type="warning")


def refuse_blank(*fields) -> bool:
    """Refuse (and return True) if a required number field is empty."""
    for field in fields:
        if field.value is None:
            refuse(f"Fill in {field.props['label']}")
            return True
    return False


def root() -> None:
    def act(action, *args) -> None:
        """Run a chase action, show the log entries it wrote, redraw."""
        try:
            action(*args)
        except ValueError as e:
            ui.notify(f"Failed: {e}", type="negative")
        else:
            notify(chase.last_entries)
        view.refresh()

    def set_number(setter, name: str, field, offset: int = 0) -> None:
        """Inline Keeper override from a number field; a blank one is refused and redrawn with the real value."""
        if refuse_blank(field):
            return view.refresh()
        act(setter, name, int(field.value) + offset)

    def undo() -> None:
        undone = chase.undo()
        if undone is None:
            refuse("Nothing to undo")
        else:
            notify([f"Undone: {line}" for line in undone] or ["Undone"])
        view.refresh()

    @ui.refreshable
    def view() -> None:
        files()
        if chase.round == 0:
            setup()
        else:
            running()
        dice()
        ui.button("Undo", on_click=undo)
        ui.label("Event log").classes("text-h6")
        with ui.column().classes("gap-0"):
            for line in reversed(chase.log):
                ui.label(line)

    def files() -> None:
        def save() -> None:
            if not save_name.value:
                return refuse("Saving needs a name")
            path = CHASES / f"{Path(save_name.value).name}.json"
            try:
                save_prep(chase, path)
            except OSError as e:
                return ui.notify(f"Could not save {path}: {e}", type="negative")
            ui.notify(f"Saved {path}")
            view.refresh()

        with ui.row().classes("items-end"):
            prepped = ui.select(list_files(CHASES), label="Prepped chase")
            ui.button("Load chase", on_click=lambda: act(
                load_prep, chase, CHASES / f"{prepped.value}.json") if prepped.value else refuse(
                "Pick a prepped chase first"))
            party = ui.select(list_files(PARTIES), label="Party")
            ui.button("Import party", on_click=lambda: act(
                import_party, chase, PARTIES / f"{party.value}.json") if party.value else refuse(
                "Pick a party first"))
            ui.button("New blank chase", on_click=lambda: act(new_chase, chase))
            save_name = ui.input("Save as")
            ui.button("Save", on_click=save)

    def dice() -> None:
        ui.label("Dice").classes("text-h6")
        with ui.row().classes("items-end"):
            label = ui.input("Label")
            target = ui.number("Target", value=50, precision=0)
            bonus = ui.select({-2: "2 penalty", -1: "1 penalty", 0: "none", 1: "1 bonus", 2: "2 bonus"},
                              value=0, label="Bonus/penalty")
            ui.button("Roll D100", on_click=lambda: refuse_blank(target) or act(
                chase.roll_d100, int(target.value), bonus.value, label.value))
        with ui.row().classes("items-end"):
            char = ui.number("Characteristic (fallback)", value=50, precision=0)
            for key, text in (("full", "Full"), ("half", "½"), ("fifth", "⅕")):
                ui.button(text, on_click=lambda k=key: refuse_blank(char) or target.set_value(
                    fallback_targets(int(char.value))[k]))
        with ui.row().classes("items-end"):
            count = ui.number("N", value=1, precision=0, min=1)
            sides = ui.number("D", value=6, precision=0, min=2)
            ui.button("Roll NxDy", on_click=lambda: refuse_blank(count, sides) or act(
                chase.roll, int(count.value), int(sides.value), label.value))

    def edit(p: Participant) -> None:
        """Edit any participant field."""
        def whole(v):
            return None if v is None else int(v)

        with ui.expansion("Edit").props("dense"), ui.row().classes("items-end"):
            name = ui.input("Name", value=p.name)
            side = ui.select(list(Side), value=p.side, label="Side")
            dex = ui.number("DEX", value=p.dex, precision=0)
            mov = ui.number("MOV", value=p.mov, precision=0)
            speed = ui.number("Speed roll value", value=p.speed_value, precision=0)
            hp = ui.number("HP", value=p.hp, precision=0)
            build = ui.number("Build", value=p.build, precision=0)
            vehicle = ui.select([o.name for o in chase.participants if o.is_vehicle and o is not p],
                                value=p.vehicle, label="Passenger in", clearable=True)
            notes = ui.input("Notes", value=p.notes)
            ui.button("Save", on_click=lambda: refuse_blank(dex, mov, speed) or act(
                chase.edit_participant, p.name, name=name.value, side=side.value, dex=int(dex.value),
                mov=int(mov.value), speed_value=int(speed.value), hp=whole(hp.value),
                build=whole(build.value), vehicle=vehicle.value, notes=notes.value or "",
            ) if name.value else refuse("Name can't be empty"))

    def participant_form():
        """New-participant inputs. Returns a function giving the Participant, or None (refused) if incomplete."""
        name = ui.input("Name")
        side = ui.select(list(Side), value=Side.PURSUER, label="Side")
        dex = ui.number("DEX", value=50, precision=0)
        mov = ui.number("MOV", value=8, precision=0)
        speed = ui.number("Speed roll value", value=50, precision=0)
        hp = ui.number("HP (optional)", precision=0)
        build = ui.number("Build (vehicle)", precision=0, min=1)
        vehicle = ui.select([p.name for p in chase.participants if p.is_vehicle],
                            label="Passenger in", clearable=True)

        def make() -> Participant | None:
            if not name.value:
                return refuse("Participant needs a name")
            if refuse_blank(dex, mov, speed):
                return None
            max_hp = int(hp.value) if hp.value is not None else None
            max_build = int(build.value) if build.value is not None else None
            return Participant(name.value, side.value, int(dex.value), int(mov.value), int(speed.value),
                               hp=max_hp, max_hp=max_hp, build=max_build, max_build=max_build,
                               vehicle=vehicle.value)
        return make

    def setup() -> None:
        ui.label("Participants").classes("text-h6")
        for p in chase.participants:
            with ui.row().classes("items-center"):
                ui.label(f"{p.name} ({p.side}) DEX {p.dex} MOV {p.mov} speed {p.speed_value} {p.notes}")
                edit(p)
                if p.is_passenger:
                    ui.label(f"passenger in {p.vehicle}, no speed roll")
                    continue
                ui.toggle(list(SpeedResult), value=p.speed_result,
                          on_change=lambda e, n=p.name: act(chase.set_speed_result, n, e.value))
                ui.button("Roll (NPC)", on_click=lambda n=p.name: act(chase.roll_speed, n))
        with ui.row().classes("items-end"):
            new = participant_form()
            ui.button("Add", on_click=lambda: (p := new()) and act(chase.add, p))
        for n in chase.escaped:
            ui.label(f"{n} escapes: no chase is played.").classes("text-positive text-h6")

        def establish() -> None:
            if not chase.ready_to_establish():
                return refuse("Needs a pursuer, a fleeing character and every speed roll result")
            if refuse_blank(start_location):
                return
            act(chase.establish, start_range.value, int(start_location.value) - 1)

        track()
        with ui.row().classes("items-end"):
            start_range = ui.select({2: "Range 2", 1: "Range 1"}, value=2, label="Starting range")
            start_location = ui.number("Rearmost pursuer on location", value=1, precision=0, min=1)
            ui.button("Establish chase", on_click=establish)

    def track() -> None:
        """Locations, hazards and their editors: in setup for prep, and while running."""
        contact = chase.same_location()
        with ui.row().classes("no-wrap overflow-x-auto w-full"):
            for i, loc in enumerate(chase.locations):
                with ui.card().classes("min-w-32"):
                    ui.label(loc.name).classes("text-bold")
                    if loc.description:
                        ui.label(loc.description).classes("text-caption")
                    if i in contact:
                        ui.badge("Same location", color="orange")
                    for p in chase.participants:
                        if p.location == i:
                            color = "red" if p.side == Side.PURSUER else "blue"
                            ui.chip(p.name + (f" debt {p.debt}" if p.debt else ""),
                                    color=color, text_color="white")
                h = loc.hazard_after  # between card i and i+1
                if h:
                    barrier = h.kind == HazardKind.BARRIER
                    label = f"{h.name} {h.hp}/{h.max_hp} HP" if barrier else h.name
                    ui.chip(label, color="brown" if barrier else "orange").classes(
                        "self-center").tooltip(f"{h.kind}: {h.skill} {h.difficulty} {h.notes}")
        with ui.row().classes("items-end"):
            gap = ui.select({i: f"after {loc.name}" for i, loc in enumerate(chase.locations)},
                            value=0 if chase.locations else None, label="Gap")
            h_name = ui.input("Hazard")
            h_kind = ui.select(list(HazardKind), value=HazardKind.HAZARD, label="Type")
            h_skill = ui.input("Skill(s)")
            h_diff = ui.select(list(Difficulty), value=Difficulty.REGULAR, label="Difficulty")
            h_hp = ui.number("Barrier HP", precision=0, min=1)
            h_notes = ui.input("Notes")

            def place() -> None:
                if gap.value is None:
                    return refuse("Add a location first")
                if not h_name.value:
                    return refuse("Hazard needs a name")
                hp = int(h_hp.value) if h_kind.value == HazardKind.BARRIER and h_hp.value else None
                act(chase.add_hazard, gap.value, Hazard(h_name.value, h_skill.value, h_diff.value,
                                                        h_notes.value, h_kind.value, hp, hp))

            ui.button("Set hazard", on_click=place)
            ui.button("Remove hazard", on_click=lambda: act(chase.remove_hazard, gap.value)
                      if gap.value is not None and chase.locations[gap.value].hazard_after
                      else refuse("No hazard in that gap"))
            env = ui.select({0: "normal", 1: "quiet (bonus)", -1: "hazardous (penalty)"},
                            value=0, label="Environment")
            ui.button("Roll random hazard", on_click=lambda: act(
                chase.roll_random_hazard, gap.value, env.value) if gap.value is not None else refuse(
                "Add a location first"))
        with ui.row().classes("items-end"):
            ends = len(chase.locations)
            loc_i = ui.select({**{i: loc.name for i, loc in enumerate(chase.locations)}, ends: "(end)"}, value=0, label="Location")
            loc_name = ui.input("Name")
            loc_desc = ui.input("Description")
            def edit_location() -> None:
                if loc_i.value == ends:
                    return refuse("Pick a location to edit")
                if not loc_name.value:
                    return refuse("Location needs a name")
                act(chase.edit_location, loc_i.value, loc_name.value, loc_desc.value)

            def remove_location() -> None:
                if loc_i.value == ends:
                    return refuse("Pick a location to remove")
                if ends == 1:
                    return refuse("Can't remove the last location")
                act(chase.remove_location, loc_i.value)

            ui.button("Edit", on_click=edit_location)
            ui.button("Insert before", on_click=lambda: act(
                chase.add_location, loc_i.value, loc_name.value or "", loc_desc.value or ""))
            ui.button("Remove", on_click=remove_location)

    def running() -> None:
        turn = chase.current_turn()
        ui.label(f"Round {chase.round}").classes("text-h6")
        if chase.ended:
            ui.label("Chase over").classes("text-negative text-h6")
        with ui.row().classes("items-center"):
            caller = {None: "either side", Caller.KEEPER: "Keeper", Caller.PLAYERS: "players"}[chase.sudden_caller]
            ui.label(f"Next sudden hazard call: {caller}")
            for side in Caller:
                ui.button(f"{side.capitalize()} calls", on_click=lambda s=side: act(
                    chase.call_sudden_hazard, s)).props("dense")
        if chase.may_escape:
            ui.label(f"May escape: {', '.join(chase.may_escape)}").classes("text-positive")
        for group in chase.dex_ties():
            with ui.row().classes("items-center"):
                ui.label(f"DEX tie: {', '.join(group)}").classes("text-warning")
                ui.button("Opposed DEX roll", on_click=lambda: act(chase.roll_dex_ties))
        track()
        ui.label("DEX order").classes("text-h6")
        order = [p.name for p in chase.dex_order()]

        def swap(i: int) -> None:
            order[i - 1], order[i] = order[i], order[i - 1]
            act(chase.reorder, order)

        for i, p in enumerate(chase.dex_order()):
            style = "bg-yellow-2" if p is turn else ""
            with ui.row().classes(f"items-center {style}"):
                ui.button("↑", on_click=lambda i=i: swap(i)).props("dense flat").set_enabled(i > 0)
                hp = f" HP {p.hp}/{p.max_hp}" if p.hp is not None else ""
                build = f" build {p.build}/{p.max_build}" if p.is_vehicle else ""
                if p.is_passenger:
                    build += f" action {'ready' if p.passenger_action else 'used'}"
                ui.label(f"{p.name} DEX {p.dex} MOV {p.adjusted_mov} "
                         f"actions {p.actions_left}/{chase.movement_actions(p)} debt {p.debt}{hp}{build} {p.notes}")
                edit(p)
                for b in chase.badges(p.name):
                    ui.badge(b, color="orange")
                if p.is_vehicle:
                    ui.number("Build", value=p.build, precision=0).on(
                        "change", lambda e, n=p.name: set_number(chase.set_build, n, e.sender))
                ui.number("Location", value=p.location + 1, precision=0, min=1).on(
                    "change", lambda e, n=p.name: set_number(chase.set_location, n, e.sender, -1))
                ui.number("Actions", value=p.actions_left, precision=0, min=0).on(
                    "change", lambda e, n=p.name: set_number(chase.set_actions, n, e.sender))
                ui.number("Debt", value=p.debt, precision=0, min=0).on(
                    "change", lambda e, n=p.name: set_number(chase.set_debt, n, e.sender))
                ui.button("Remove", on_click=lambda n=p.name: act(chase.remove, n)).props("dense flat")
                if p is turn:
                    hazard_or_move(p)
            if p is turn:
                other_actions(p)
        join()
        if not chase.ended:
            with ui.row():
                ui.button("End round", on_click=lambda: act(chase.end_round))
                ui.button("End chase", color="negative", on_click=lambda: act(chase.end_chase))

    def join() -> None:
        ui.label("Join mid-chase").classes("text-h6")
        if chase.unable_to_join:
            ui.label(f"Too slow to join: {', '.join(chase.unable_to_join)}").classes("text-warning")
        with ui.row().classes("items-end"):
            new = participant_form()
            result = ui.select({"npc": "NPC roll", **{r: str(r) for r in SpeedResult}},
                               value="npc", label="Speed result")
            location = ui.number("Location", value=1, precision=0, min=1)
            ui.button("Join", on_click=lambda: (p := new()) and not refuse_blank(location) and act(
                chase.join, p, int(location.value) - 1, None if result.value == "npc" else result.value))

    def other_actions(p: Participant) -> None:
        others = chase.targets(p.name)
        with ui.row().classes("items-end"):
            target = ui.select(others, value=others[0] if others else None, label="Target")
            lost = ui.number("Lost (blank = 1D3)", precision=0, min=1, max=3)
            damage = ui.number("HP damage", value=0, precision=0, min=0)
            ui.button("Attack", on_click=lambda: act(chase.attack, p.name, target.value)
                      if target.value else refuse("Pick a target first"))
            ui.button("Maneuver succeeded", on_click=lambda: act(
                chase.maneuver, p.name, target.value, None if lost.value is None else int(lost.value),
                int(damage.value or 0)) if target.value else refuse("Pick a target first"))
            note = ui.input("Other action")
            ui.button("Do", on_click=lambda: act(chase.other_action, p.name, note.value)
                      if note.value else refuse("Describe the action first"))
            ui.button("Delay", on_click=lambda: act(chase.delay, p.name))
            if p.is_passenger:
                for passed in (True, False):
                    ui.button(f"Navigate {'succeeded' if passed else 'failed'}", on_click=lambda ok=passed: act(
                        chase.navigate, p.name, ok))

    def hazard_or_move(p: Participant) -> None:
        h = chase.hazard_ahead(p.name)
        if p.is_passenger:
            return  # passengers do not move themselves
        if h is None:
            ui.button("Move", on_click=lambda: act(chase.move, p.name))
            if p.is_vehicle:
                for d in PEDAL_DISTANCES:
                    ui.button(f"Pedal {d}", on_click=lambda d=d: act(
                        chase.pedal_to_the_metal, p.name, d)).props("dense")
            return
        ui.label(f"{h.kind.capitalize()} {h.name}: {h.skill} ({h.difficulty}) {h.notes}").classes(
            "text-orange")
        if h.kind == HazardKind.BARRIER:
            smash = ui.number("Damage to barrier", value=0, precision=0, min=0)
            ui.button("Smash", on_click=lambda: act(chase.damage_barrier, p.name, int(smash.value or 0)))
            if p.is_vehicle:
                ui.button(f"Ram ({p.build}D10)", on_click=lambda: act(chase.damage_barrier, p.name))
        bonus = ui.select({0: "no bonus", 1: "1 bonus die", 2: "2 bonus dice"}, value=0,
                          label="Cautious")
        lost = ui.number("Lost (blank = 1D3)", precision=0, min=1, max=3)
        damage = ui.number("Damage", value=0, precision=0, min=0)

        def resolve(passed: bool) -> None:
            act(chase.resolve_hazard, p.name, passed, bonus.value,
                None if lost.value is None else int(lost.value), int(damage.value or 0))

        ui.button("Pass", on_click=lambda: resolve(True))
        ui.button("Fail", on_click=lambda: resolve(False))

    view()


def main() -> None:
    parser = argparse.ArgumentParser(description="CoC 7e chase manager")
    parser.add_argument("--native", action="store_true", help="open in a native window")
    args = parser.parse_args()
    ui.run(root, title="Chase Manager", native=args.native, reload=False)


if __name__ == "__main__":
    main()
