"""Thin NiceGUI layer: renders a Chase and calls its operations. No rules here."""

import argparse
from contextlib import contextmanager
from pathlib import Path

from nicegui import ui

from coc_chase.chase import (PEDAL_DISTANCES, Caller, Chase, Difficulty, Hazard, HazardKind, Participant, Side,
                              SpeedResult, fallback_targets)
from coc_chase.files import import_party, list_files, load_prep, new_chase, save_prep

# ponytail: one global chase per process; the Keeper is the only user
chase = Chase.load(Path("autosave.json"))
CHASES, PARTIES = Path("chases"), Path("parties")

# Base text ~18px; every field in a dialog or the side panel is full width so labels never truncate.
CSS = """
html, body { font-size: 18px; }
.q-btn, .q-field, .q-field__native, .q-field__label, .q-item, .q-chip, .q-toggle__label, .q-checkbox__label,
.q-btn-toggle .q-btn { font-size: 1rem; }
.q-badge { font-size: 0.85rem; padding: 2px 8px; }
.q-dialog .q-field, .q-drawer .q-field { width: 100%; }
"""
# White text on these meets WCAG AA (>= 4.5:1).
SIDE_COLOR = {Side.PURSUER: "red-9", Side.FLEEING: "blue-9"}
BADGE = {"color": "amber-3", "text_color": "black"}


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


def whole(value) -> int | None:
    return None if value is None else int(value)


def section(title: str) -> None:
    ui.label(title).classes("text-subtitle1 text-bold")


def root() -> None:
    ui.add_css(CSS)
    ui.colors(primary="#1565c0", positive="#2e7d32")  # darker defaults: white text meets AA
    holder = ui.element()  # dialogs live here, outside anything a refresh clears

    def refresh() -> None:
        header_view.refresh()
        main_view.refresh()
        log_view.refresh()

    def act(action, *args) -> bool:
        """Run a chase action, show the log entries it wrote, redraw. True if it ran."""
        try:
            action(*args)
        except ValueError as e:
            ui.notify(f"Failed: {e}", type="negative")
            ok = False
        else:
            notify(chase.last_entries)
            ok = True
        refresh()
        return ok

    def undo() -> None:
        undone = chase.undo()
        if undone is None:
            refuse("Nothing to undo")
        else:
            notify([f"Undone: {line}" for line in undone] or ["Undone"])
        refresh()

    @contextmanager
    def dialog(title: str):
        """A dialog card; the caller fills it, it opens on exit and is deleted once closed."""
        with holder, ui.dialog() as d, ui.card().classes("w-[36rem] max-w-full"):
            ui.label(title).classes("text-h6")
            yield d
        d.on("hide", d.delete)
        d.open()

    def submit(d, action, *args) -> None:
        """Run an action from a dialog: close it if the action ran."""
        if act(action, *args):
            d.close()

    def confirm(question: str, action, *args) -> None:
        with dialog(question) as d, ui.row().classes("w-full justify-end"):
            ui.button("Cancel", on_click=d.close).props("flat")
            ui.button("Yes", color="negative", on_click=lambda: submit(d, action, *args))

    # --- header --------------------------------------------------------------

    @ui.refreshable
    def header_view() -> None:
        running = chase.round > 0
        ui.label(f"Round {chase.round}" if running else "Setup").classes("text-h5 text-bold")
        if chase.ended:
            ui.label("Chase over").classes("text-h6")
        elif running:
            turn = chase.current_turn()
            ui.label(f"Turn: {turn.name}" if turn else "Everyone has acted").classes("text-h6")
            ui.button("End round", on_click=lambda: act(chase.end_round)).props("color=white text-color=primary")
            caller = {None: "either side", Caller.KEEPER: "Keeper", Caller.PLAYERS: "players"}[chase.sudden_caller]
            ui.label(f"Next sudden hazard: {caller}")
            ui.button("Keeper calls", on_click=lambda: act(chase.call_sudden_hazard, Caller.KEEPER)).props(
                "outline color=white")
            ui.button("Players call", on_click=lambda: act(chase.call_sudden_hazard, Caller.PLAYERS)).props(
                "outline color=white")
        ui.space()
        ui.button("Undo", icon="undo", on_click=undo).props("flat color=white")
        with ui.button("File", icon="menu").props("flat color=white"), ui.menu():
            ui.menu_item("Load prepped chase…", load_dialog)
            ui.menu_item("Import party…", party_dialog)
            ui.menu_item("New blank chase", lambda: act(new_chase, chase))
            ui.menu_item("Save as…", save_dialog)
            ui.separator()
            ui.menu_item("End chase…", lambda: confirm("End the chase?", chase.end_chase)).set_enabled(
                running and not chase.ended)

    def load_dialog() -> None:
        with dialog("Load prepped chase") as d:
            prepped = ui.select(list_files(CHASES), label="Prepped chase")
            ui.button("Load", on_click=lambda: submit(d, load_prep, chase, CHASES / f"{prepped.value}.json")
                      if prepped.value else refuse("Pick a prepped chase first"))

    def party_dialog() -> None:
        with dialog("Import party") as d:
            party = ui.select(list_files(PARTIES), label="Party")
            ui.button("Import", on_click=lambda: submit(d, import_party, chase, PARTIES / f"{party.value}.json")
                      if party.value else refuse("Pick a party first"))

    def save_dialog() -> None:
        def save() -> None:
            if not name.value:
                return refuse("Saving needs a name")
            path = CHASES / f"{Path(name.value).name}.json"
            try:
                save_prep(chase, path)
            except OSError as e:
                return ui.notify(f"Could not save {path}: {e}", type="negative")
            ui.notify(f"Saved {path}")
            d.close()

        with dialog("Save chase as") as d:
            name = ui.input("File name")
            ui.button("Save", on_click=save)

    # --- side panel: dice and event log ----------------------------------------

    def dice() -> None:
        section("Dice")
        label = ui.input("Roll label")
        target = ui.number("Target", value=50, precision=0)
        bonus = ui.select({-2: "2 penalty dice", -1: "1 penalty die", 0: "none", 1: "1 bonus die", 2: "2 bonus dice"},
                          value=0, label="Bonus / penalty")
        ui.button("Roll D100", on_click=lambda: refuse_blank(target) or act(
            chase.roll_d100, int(target.value), bonus.value, label.value))
        char = ui.number("Characteristic (fallback target)", value=50, precision=0)
        with ui.row():
            for key, text in (("full", "Full"), ("half", "½"), ("fifth", "⅕")):
                ui.button(text, on_click=lambda k=key: refuse_blank(char) or target.set_value(
                    fallback_targets(int(char.value))[k])).props("outline")
        with ui.row().classes("w-full no-wrap"):
            count = ui.number("Number of dice", value=1, precision=0, min=1)
            sides = ui.number("Sides", value=6, precision=0, min=2)
        ui.button("Roll NxDy", on_click=lambda: refuse_blank(count, sides) or act(
            chase.roll, int(count.value), int(sides.value), label.value))

    @ui.refreshable
    def log_view() -> None:
        for line in reversed(chase.log):
            ui.label(line)

    # --- participant dialogs -----------------------------------------------------

    def participant_fields(p: Participant | None = None):
        """Every participant field. Returns a function giving them as a dict, or None (refused) if incomplete."""
        name = ui.input("Name", value=p.name if p else "")
        side = ui.select({s: s.capitalize() for s in Side}, value=p.side if p else Side.PURSUER, label="Side")
        dex = ui.number("DEX", value=p.dex if p else 50, precision=0)
        mov = ui.number("MOV", value=p.mov if p else 8, precision=0)
        speed = ui.number("Speed roll value", value=p.speed_value if p else 50, precision=0)
        hp = ui.number("HP (optional)", value=p.hp if p else None, precision=0)
        build = ui.number("Build (vehicles only)", value=p.build if p else None, precision=0, min=0)
        vehicle = ui.select([o.name for o in chase.participants if o.is_vehicle and o is not p],
                            value=p.vehicle if p else None, label="Passenger in (vehicle)", clearable=True)
        notes = ui.input("Notes", value=p.notes if p else "")
        investigator = ui.checkbox("Investigator (a player's character)", value=p.investigator if p else False)

        def values() -> dict | None:
            if not name.value:
                return refuse("Participant needs a name")
            if refuse_blank(dex, mov, speed):
                return None
            return dict(name=name.value, side=side.value, dex=int(dex.value), mov=int(mov.value),
                        speed_value=int(speed.value), hp=whole(hp.value), build=whole(build.value),
                        vehicle=vehicle.value, notes=notes.value or "", investigator=investigator.value)
        return values

    def new_participant(values) -> Participant | None:
        v = values()
        return v and Participant(**v, max_hp=v["hp"], max_build=v["build"])

    def add_dialog() -> None:
        with dialog("Add participant") as d:
            values = participant_fields()
            ui.button("Add", on_click=lambda: (p := new_participant(values)) and submit(d, chase.add, p))

    def join_dialog() -> None:
        with dialog("Join mid-chase") as d:
            values = participant_fields()
            result = ui.select({"npc": "Roll for an NPC", **{r: r.capitalize() for r in SpeedResult}},
                               value="npc", label="Speed roll result")
            location = ui.number("Joins on location #", value=1, precision=0, min=1)
            ui.button("Join", on_click=lambda: (p := new_participant(values)) and not refuse_blank(location) and submit(
                d, chase.join, p, int(location.value) - 1, None if result.value == "npc" else result.value))

    def edit_dialog(p: Participant) -> None:
        running = chase.round > 0

        def save() -> None:
            v = values()
            if v is None or (running and refuse_blank(location, actions, debt)):
                return
            if running:
                v |= dict(location=int(location.value) - 1, actions_left=int(actions.value), debt=int(debt.value))
            submit(d, lambda: chase.edit_participant(p.name, **v))

        with dialog(f"Edit {p.name}") as d:
            values = participant_fields(p)
            if running:
                section("Keeper overrides")
                location = ui.number("Location #", value=p.location + 1, precision=0, min=1)
                actions = ui.number("Movement actions left", value=p.actions_left, precision=0, min=0)
                debt = ui.number("Debt (actions owed next round)", value=p.debt, precision=0, min=0)
            ui.button("Save", on_click=save)

    def move_up(p: Participant) -> None:
        """Swap with the previous participant who hasn't delayed."""
        order = [o.name for o in chase.dex_order()]
        i = order.index(p.name)
        j = max(k for k in range(i) if order[k] not in chase.delayed)
        order[i], order[j] = order[j], order[i]
        act(chase.reorder, order)

    # --- track -------------------------------------------------------------------

    def track() -> None:
        """Locations with the participants on them and the obstacles between them."""
        with ui.row().classes("items-center"):
            section("Layout")
            ui.button("Obstacles…", on_click=obstacle_dialog).props("outline")
            ui.button("Locations…", on_click=location_dialog).props("outline")
        contact = chase.same_location() if chase.round else []
        with ui.row().classes("no-wrap overflow-x-auto w-full"):
            for i, loc in enumerate(chase.locations):
                with ui.card().classes("min-w-32"):
                    ui.label(f"{i + 1}. {loc.name}").classes("text-bold")
                    if loc.description:
                        ui.label(loc.description).classes("text-grey-8")
                    if i in contact:
                        ui.badge("Same location", **BADGE)
                    for p in chase.participants:
                        if p.location == i:
                            ui.chip(f"{p.name} · {p.side.capitalize()}" + (f" · debt {p.debt}" if p.debt else ""),
                                    color=SIDE_COLOR[p.side], text_color="white")
                h = loc.hazard_after  # between card i and i+1
                if h:
                    barrier = h.kind == HazardKind.BARRIER
                    label = f"Barrier: {h.name} {h.hp}/{h.max_hp} HP" if barrier else f"Hazard: {h.name}"
                    ui.chip(label, color="brown-7" if barrier else "orange-3",
                            text_color="white" if barrier else "black").classes("self-center").tooltip(
                        f"{h.skill} ({h.difficulty}) {h.notes}")

    def obstacle_dialog() -> None:
        if not chase.locations:
            return refuse("Add a location first")

        def place() -> None:
            if not name.value:
                return refuse("Obstacle needs a name")
            hp = int(h_hp.value) if kind.value == HazardKind.BARRIER and h_hp.value else None
            submit(d, chase.add_hazard, after.value,
                   Hazard(name.value, skill.value, difficulty.value, notes.value, kind.value, hp, hp))

        with dialog("Obstacle") as d:
            after = ui.select({i: f"{i + 1}. {loc.name}" for i, loc in enumerate(chase.locations)}, value=0,
                              label="Obstacle after location")
            name = ui.input("Obstacle name")
            kind = ui.select({k: k.capitalize() for k in HazardKind}, value=HazardKind.HAZARD, label="Type")
            skill = ui.input("Skill(s) to pass")
            difficulty = ui.select({x: x.capitalize() for x in Difficulty}, value=Difficulty.REGULAR,
                                   label="Difficulty")
            h_hp = ui.number("Barrier HP (barriers only)", precision=0, min=1)
            notes = ui.input("Notes")
            with ui.row():
                ui.button("Set obstacle", on_click=place)
                ui.button("Remove obstacle", on_click=lambda: submit(d, chase.remove_hazard, after.value)
                          if chase.locations[after.value].hazard_after else refuse("No obstacle there"))
            section("Random hazard")
            env = ui.select({0: "Normal", 1: "Quiet (bonus die)", -1: "Hazardous (penalty die)"},
                            value=0, label="Environment")
            ui.button("Roll random hazard", on_click=lambda: submit(d, chase.roll_random_hazard, after.value,
                                                                     env.value))

    def location_dialog() -> None:
        ends = len(chase.locations)

        def edit_location() -> None:
            if at.value == ends:
                return refuse("Pick a location to edit")
            if not name.value:
                return refuse("Location needs a name")
            submit(d, chase.edit_location, at.value, name.value, desc.value)

        def remove_location() -> None:
            if at.value == ends:
                return refuse("Pick a location to remove")
            if ends == 1:
                return refuse("Can't remove the last location")
            submit(d, chase.remove_location, at.value)

        with dialog("Locations") as d:
            at = ui.select({**{i: f"{i + 1}. {loc.name}" for i, loc in enumerate(chase.locations)}, ends: "(end)"},
                           value=0, label="Location")
            name = ui.input("Name")
            desc = ui.input("Description")
            with ui.row():
                ui.button("Edit", on_click=edit_location)
                ui.button("Insert before", on_click=lambda: submit(
                    d, chase.add_location, at.value, name.value or "", desc.value or ""))
                ui.button("Remove", color="negative", on_click=remove_location)

    # --- main area -----------------------------------------------------------------

    @ui.refreshable
    def main_view() -> None:
        track()
        alerts()
        if chase.round == 0:
            start_panel()
        elif not chase.ended:
            turn_panel()
        participants()

    def alerts() -> None:
        lines = []
        if chase.round:
            for group in chase.dex_ties():
                lines.append((f"DEX tie: {', '.join(group)}", group))
        if chase.may_escape:
            lines.append((f"May escape: {', '.join(chase.may_escape)}", None))
        if chase.unable_to_join:
            lines.append((f"Too slow to join: {', '.join(chase.unable_to_join)}", None))
        if chase.ended:
            lines.append(("Chase over", None))
        if not lines:
            return
        with ui.card().classes("w-full bg-amber-2 text-black").props("flat bordered"):
            for text, group in lines:
                with ui.row().classes("items-center"):
                    ui.label(f"⚠ {text}").classes("text-bold")
                    if group:
                        if not any(chase.get(n).investigator for n in group):
                            ui.button("Opposed DEX roll", on_click=lambda: act(chase.roll_dex_ties))
                        ui.button("Keep this order", on_click=lambda g=group: act(chase.keep_dex_order, g))

    def start_panel() -> None:
        def establish() -> None:
            if not chase.ready_to_establish():
                return refuse("Needs a pursuer, a fleeing character and every speed roll result")
            if refuse_blank(start_location):
                return
            act(chase.establish, start_range.value, int(start_location.value) - 1)

        with ui.card().classes("w-full"):
            ui.label("Start the chase").classes("text-h6")
            section("Speed rolls")
            for p in chase.turn_order():
                with ui.row().classes("items-center"):
                    ui.label(p.name).classes("w-48 text-bold")
                    if p.is_passenger:
                        ui.label(f"rides in {p.vehicle}, no speed roll")
                        continue
                    ui.toggle({r: r.capitalize() for r in SpeedResult}, value=p.speed_result,
                              on_change=lambda e, n=p.name: act(chase.set_speed_result, n, e.value))
                    if not p.investigator:
                        ui.button("Roll", on_click=lambda n=p.name: act(chase.roll_speed, n)).props("outline")
            for n in chase.escaped:
                ui.label(f"{n} escapes: no chase is played.").classes("text-h6 text-positive")
            with ui.row().classes("items-end"):
                start_range = ui.select({2: "Range 2", 1: "Range 1"}, value=2, label="Starting range").classes("w-48")
                start_location = ui.number("Rearmost pursuer starts on location #", value=1, precision=0,
                                           min=1).classes("w-96")
                ui.button("Establish chase", on_click=establish)

    def turn_panel() -> None:
        p = chase.current_turn()
        if p is None:
            with ui.card().classes("w-full"):
                ui.label("Everyone has acted this round: End round when ready.").classes("text-h6")
            return
        with ui.card().classes("w-full").style("border: 4px solid #1565c0"):
            ui.label(f"▶ {p.name}'s turn").classes("text-h5 text-bold")
            if not p.is_passenger:
                ui.label(f"Movement actions left: {p.actions_left}/{chase.movement_actions(p)}")
            section("Movement")
            movement(p)
            ui.separator()
            section("Conflict")
            conflict(p)

    def movement(p: Participant) -> None:
        if p.is_passenger:  # passengers do not move themselves
            with ui.row():
                for passed in (True, False):
                    ui.button(f"Navigate {'succeeded' if passed else 'failed'}",
                              on_click=lambda ok=passed: act(chase.navigate, p.name, ok))
            return
        h = chase.hazard_ahead(p.name)
        if h is None:
            with ui.row():
                ui.button("Move", on_click=lambda: act(chase.move, p.name))
                if p.is_vehicle:
                    for d in PEDAL_DISTANCES:
                        ui.button(f"Pedal to the Metal {d}", on_click=lambda d=d: act(
                            chase.pedal_to_the_metal, p.name, d)).props("outline")
            return
        barrier = h.kind == HazardKind.BARRIER
        with ui.card().classes("w-full bg-orange-1").props("flat bordered"):
            ui.label(f"{h.kind.capitalize()} ahead: {h.name}").classes("text-bold")
            ui.label(f"Skill: {h.skill or '—'} · Difficulty: {h.difficulty}"
                     + (f" · Barrier HP {h.hp}/{h.max_hp}" if barrier else ""))
            if h.notes:
                ui.label(h.notes)
        with ui.row().classes("items-end"):
            bonus = ui.select({0: "No bonus", 1: "1 bonus die", 2: "2 bonus dice"}, value=0,
                              label="Cautious approach").classes("w-56")
            lost = ui.number("Actions lost on fail (blank = 1D3)", precision=0, min=1, max=3).classes("w-96")
            damage = ui.number("HP damage on fail", value=0, precision=0, min=0).classes("w-56")

            def resolve(passed: bool) -> None:
                act(chase.resolve_hazard, p.name, passed, bonus.value, whole(lost.value), int(damage.value or 0))

            ui.button("Pass", on_click=lambda: resolve(True))
            ui.button("Fail", on_click=lambda: resolve(False))
        if barrier:
            with ui.row().classes("items-end"):
                smash = ui.number("Damage to barrier", value=0, precision=0, min=0).classes("w-56")
                ui.button("Smash", on_click=lambda: act(chase.damage_barrier, p.name, int(smash.value or 0)))
                if p.is_vehicle:
                    ui.button(f"Ram ({p.build}D10)", on_click=lambda: act(chase.damage_barrier, p.name))

    def conflict(p: Participant) -> None:
        others = chase.targets(p.name)
        with ui.row().classes("items-end"):
            target = ui.select(others, value=others[0] if others else None, label="Target").classes("w-56")
            ui.button("Attack", on_click=lambda: act(chase.attack, p.name, target.value)
                      if target.value else refuse("Pick a target first"))
        with ui.row().classes("items-end"):
            lost = ui.number("Target loses actions (blank = 1D3)", precision=0, min=1, max=3).classes("w-96")
            damage = ui.number("Target HP damage", value=0, precision=0, min=0).classes("w-56")
            ui.button("Maneuver succeeded", on_click=lambda: act(
                chase.maneuver, p.name, target.value, whole(lost.value), int(damage.value or 0))
                if target.value else refuse("Pick a target first"))
        with ui.row().classes("items-end"):
            note = ui.input("Other action").classes("w-80")
            ui.button("Do", on_click=lambda: act(chase.other_action, p.name, note.value)
                      if note.value else refuse("Describe the action first"))
            ui.button("Delay", on_click=lambda: act(chase.delay, p.name)).props("outline")

    def participants() -> None:
        running = chase.round > 0
        with ui.row().classes("items-center"):
            ui.label("Turn order").classes("text-h6")
            if not running:
                ui.button("Add participant", icon="add", on_click=add_dialog)
            elif not chase.ended:
                ui.button("Join mid-chase", icon="add", on_click=join_dialog)
        turn = chase.current_turn()
        contact = chase.same_location() if running else []
        for i, p in enumerate(chase.turn_order()):
            card(p, i, p is turn, running and chase.had_turn(p.name), p.location in contact)

    def card(p: Participant, index: int, now: bool, done: bool, contact: bool) -> None:
        running = chase.round > 0
        c = ui.card().classes("w-full" + (" bg-grey-3" if done else ""))  # dimmed, text still AA
        if now:
            c.style("border: 4px solid #1565c0")
        with c:
            with ui.row().classes("w-full items-center"):
                ui.label(p.name).classes("text-h5 text-bold")
                ui.badge(p.side.capitalize(), color=SIDE_COLOR[p.side], text_color="white")
                ui.badge("Investigator" if p.investigator else "NPC", color="grey-9", text_color="white")
                if now:
                    ui.label("▶ Now").classes("text-h6 text-bold text-primary")
                if done:
                    ui.label("Turn taken").classes("text-grey-9")
                ui.space()
                with ui.button(icon="more_vert").props("flat round aria-label='Participant menu'"), ui.menu():
                    ui.menu_item("Edit…", lambda: edit_dialog(p))
                    ui.menu_item("Move up in turn order", lambda: move_up(p)).set_enabled(
                        index > 0 and p.name not in chase.delayed)
                    ui.menu_item("Remove…", lambda: confirm(f"Remove {p.name}?", chase.remove, p.name))
            stats = {"DEX": p.dex, "MOV": p.adjusted_mov if running else p.mov}
            if running:
                stats |= {"Actions": f"{p.actions_left}/{chase.movement_actions(p)}", "Debt": p.debt}
            else:
                stats["Speed roll value"] = p.speed_value
            if p.hp is not None:
                stats["HP"] = f"{p.hp}/{p.max_hp}"
            if p.is_vehicle:
                stats["Build"] = f"{p.build}/{p.max_build}"
            with ui.row().classes("gap-8"):
                for label, value in stats.items():
                    with ui.column().classes("gap-0"):
                        ui.label(label).classes("text-grey-8 text-sm")
                        ui.label(str(value)).classes("text-bold text-lg")
            if p.is_passenger:
                action = f" · passenger action {'ready' if p.passenger_action else 'used'}" if running else ""
                ui.label(f"Rides in {p.vehicle}{action}")
            badges = [b for b in chase.badges(p.name) if not b.startswith("passenger in")]
            badges += ["Same location"] * contact + ["Delayed"] * (p.name in chase.delayed)
            badges += ["May escape"] * (p.name in chase.may_escape)
            if badges:
                with ui.row().classes("gap-2"):
                    for b in badges:
                        ui.badge(b, **BADGE)
            if p.notes:
                ui.label(p.notes).classes("text-grey-9 italic")

    # --- page --------------------------------------------------------------------------

    with ui.header().classes("items-center gap-4"):
        header_view()
    with ui.right_drawer(value=True).props("width=380 behavior=desktop bordered"):
        with ui.column().classes("w-full h-full no-wrap"):
            dice()
            ui.separator()
            section("Event log (newest first)")
            with ui.scroll_area().classes("grow"):
                log_view()
    with ui.column().classes("w-full gap-4"):
        main_view()


def main() -> None:
    parser = argparse.ArgumentParser(description="CoC 7e chase manager")
    parser.add_argument("--native", action="store_true", help="open in a native window")
    args = parser.parse_args()
    ui.run(root, title="Chase Manager", native=args.native, reload=False)


if __name__ == "__main__":
    main()
