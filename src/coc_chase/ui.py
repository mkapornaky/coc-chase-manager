"""Thin NiceGUI layer: renders a Chase and calls its operations. No rules here."""

import argparse
from pathlib import Path

from nicegui import ui

from coc_chase.chase import Chase, Hazard, Participant, fallback_targets

# ponytail: one global chase per process; the Keeper is the only user
chase = Chase.load(Path("autosave.json"))


def root() -> None:
    @ui.refreshable
    def view() -> None:
        if chase.round == 0:
            setup()
        else:
            running()
        dice()
        ui.button("Undo", on_click=lambda: (chase.undo(), view.refresh()))
        ui.label("Event log").classes("text-h6")
        with ui.column().classes("gap-0"):
            for line in reversed(chase.log):
                ui.label(line)

    def dice() -> None:
        ui.label("Dice").classes("text-h6")
        with ui.row().classes("items-end"):
            label = ui.input("Label")
            target = ui.number("Target", value=50, precision=0)
            bonus = ui.select({-2: "2 penalty", -1: "1 penalty", 0: "none", 1: "1 bonus", 2: "2 bonus"},
                              value=0, label="Bonus/penalty")
            ui.button("Roll D100", on_click=lambda: (
                chase.roll_d100(int(target.value), bonus.value, label.value), view.refresh()))
        with ui.row().classes("items-end"):
            char = ui.number("Characteristic (fallback)", value=50, precision=0)
            for key, text in (("full", "Full"), ("half", "½"), ("fifth", "⅕")):
                ui.button(text, on_click=lambda k=key: target.set_value(fallback_targets(int(char.value))[k]))
        with ui.row().classes("items-end"):
            count = ui.number("N", value=1, precision=0, min=1)
            sides = ui.number("D", value=6, precision=0, min=2)
            ui.button("Roll NxDy", on_click=lambda: (
                chase.roll(int(count.value), int(sides.value), label.value), view.refresh()))

    def setup() -> None:
        ui.label("Participants").classes("text-h6")
        for p in chase.participants:
            with ui.row().classes("items-center"):
                ui.label(f"{p.name} ({p.side}) DEX {p.dex} MOV {p.mov} speed {p.speed_value}")
                ui.toggle(["extreme", "success", "fail"], value=p.speed_result,
                          on_change=lambda e, n=p.name: (chase.set_speed_result(n, e.value), view.refresh()))
                ui.button("Roll (NPC)", on_click=lambda n=p.name: (chase.roll_speed(n), view.refresh()))
        with ui.row().classes("items-end"):
            name = ui.input("Name")
            side = ui.select(["pursuer", "fleeing"], value="pursuer", label="Side")
            dex = ui.number("DEX", value=50, precision=0)
            mov = ui.number("MOV", value=8, precision=0)
            speed = ui.number("Speed roll value", value=50, precision=0)
            hp = ui.number("HP (optional)", precision=0)

            def add() -> None:
                if name.value:
                    max_hp = int(hp.value) if hp.value is not None else None
                    chase.add(Participant(name.value, side.value, int(dex.value),
                                          int(mov.value), int(speed.value), hp=max_hp, max_hp=max_hp))
                    view.refresh()

            ui.button("Add", on_click=add)
        for n in chase.escaped:
            ui.label(f"{n} escapes: no chase is played.").classes("text-positive text-h6")

        def establish() -> None:
            if any(p.speed_result is None for p in chase.participants):
                ui.notify("Enter every speed roll result first")
                return
            chase.establish()
            view.refresh()

        ui.button("Establish chase", on_click=establish)

    def running() -> None:
        turn = chase.current_turn()
        ui.label(f"Round {chase.round}").classes("text-h6")
        with ui.row().classes("no-wrap overflow-x-auto w-full"):
            for i, loc in enumerate(chase.locations):
                with ui.card().classes("min-w-32"):
                    ui.label(loc).classes("text-bold")
                    if i in chase.descriptions:
                        ui.label(chase.descriptions[i]).classes("text-caption")
                    for p in chase.participants:
                        if p.location == i:
                            color = "red" if p.side == "pursuer" else "blue"
                            ui.chip(p.name + (f" debt {p.debt}" if p.debt else ""),
                                    color=color, text_color="white")
                if i in chase.hazards:  # between card i and i+1
                    h = chase.hazards[i]
                    barrier = h.kind == "barrier"
                    label = f"{h.name} {h.hp}/{h.max_hp} HP" if barrier else h.name
                    ui.chip(label, color="brown" if barrier else "orange").classes(
                        "self-center").tooltip(f"{h.kind}: {h.skill} {h.difficulty} {h.notes}")
        with ui.row().classes("items-end"):
            gap = ui.select({i: f"after {loc}" for i, loc in enumerate(chase.locations)},
                            value=0, label="Gap")
            h_name = ui.input("Hazard")
            h_kind = ui.select(["hazard", "barrier"], value="hazard", label="Type")
            h_skill = ui.input("Skill(s)")
            h_diff = ui.select(["regular", "hard", "extreme"], value="regular", label="Difficulty")
            h_hp = ui.number("Barrier HP", precision=0, min=1)
            h_notes = ui.input("Notes")

            def place() -> None:
                if h_name.value:
                    hp = int(h_hp.value) if h_kind.value == "barrier" and h_hp.value else None
                    chase.add_hazard(gap.value, Hazard(h_name.value, h_skill.value, h_diff.value,
                                                       h_notes.value, h_kind.value, hp, hp))
                    view.refresh()

            ui.button("Set hazard", on_click=place)
            ui.button("Remove hazard", on_click=lambda: gap.value in chase.hazards and (
                chase.remove_hazard(gap.value), view.refresh()))
            env = ui.select({0: "normal", 1: "quiet (bonus)", -1: "hazardous (penalty)"},
                            value=0, label="Environment")
            ui.button("Roll random hazard", on_click=lambda: (
                chase.roll_random_hazard(gap.value, env.value), view.refresh()))
        with ui.row().classes("items-end"):
            loc_i = ui.select({i: loc for i, loc in enumerate(chase.locations)}, value=0,
                              label="Location")
            loc_name = ui.input("Name")
            loc_desc = ui.input("Description")
            ui.button("Edit", on_click=lambda: loc_name.value and (chase.edit_location(
                loc_i.value, loc_name.value, loc_desc.value), view.refresh()))
            ui.button("Insert before", on_click=lambda: (chase.add_location(
                loc_i.value, loc_name.value or "", loc_desc.value or ""), view.refresh()))
            ui.button("Remove", on_click=lambda: len(chase.locations) > 1 and (
                chase.remove_location(loc_i.value), view.refresh()))
        ui.label("DEX order").classes("text-h6")
        for p in chase.dex_order():
            style = "bg-yellow-2" if p is turn else ""
            with ui.row().classes(f"items-center {style}"):
                hp = f" HP {p.hp}/{p.max_hp}" if p.hp is not None else ""
                ui.label(f"{p.name} DEX {p.dex} MOV {p.adjusted_mov} "
                         f"actions {p.actions_left}/{chase.movement_actions(p)} debt {p.debt}{hp}")
                if p is turn:
                    hazard_or_move(p)
        ui.button("End round", on_click=lambda: (chase.end_round(), view.refresh()))

    def hazard_or_move(p: Participant) -> None:
        h = chase.hazard_ahead(p.name)
        if h is None:
            ui.button("Move", on_click=lambda: (chase.move(p.name), view.refresh()))
            return
        ui.label(f"{h.kind.capitalize()} {h.name}: {h.skill} ({h.difficulty}) {h.notes}").classes(
            "text-orange")
        if h.kind == "barrier":
            smash = ui.number("Damage to barrier", value=0, precision=0, min=0)
            ui.button("Smash", on_click=lambda: (
                chase.damage_barrier(p.name, int(smash.value or 0)), view.refresh()))
        bonus = ui.select({0: "no bonus", 1: "1 bonus die", 2: "2 bonus dice"}, value=0,
                          label="Cautious")
        lost = ui.number("Lost (blank = 1D3)", precision=0, min=1, max=3)
        damage = ui.number("HP damage", value=0, precision=0, min=0)

        def resolve(passed: bool) -> None:
            chase.resolve_hazard(p.name, passed, bonus.value,
                                 None if lost.value is None else int(lost.value), int(damage.value or 0))
            view.refresh()

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
