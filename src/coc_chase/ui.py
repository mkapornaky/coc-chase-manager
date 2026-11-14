"""Thin NiceGUI layer: renders a Chase and calls its operations. No rules here."""

import argparse
from pathlib import Path

from nicegui import ui

from coc_chase.chase import Chase, Participant, fallback_targets

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

            def add() -> None:
                if name.value:
                    chase.add(Participant(name.value, side.value, int(dex.value),
                                          int(mov.value), int(speed.value)))
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
                    for p in chase.participants:
                        if p.location == i:
                            color = "red" if p.side == "pursuer" else "blue"
                            ui.chip(p.name, color=color, text_color="white")
        ui.label("DEX order").classes("text-h6")
        for p in chase.dex_order():
            style = "bg-yellow-2" if p is turn else ""
            with ui.row().classes(f"items-center {style}"):
                ui.label(f"{p.name} DEX {p.dex} MOV {p.adjusted_mov} "
                         f"actions {p.actions_left}/{chase.movement_actions(p)}")
                if p is turn:
                    ui.button("Move", on_click=lambda n=p.name: (chase.move(n), view.refresh()))
        ui.button("End round", on_click=lambda: (chase.end_round(), view.refresh()))

    view()


def main() -> None:
    parser = argparse.ArgumentParser(description="CoC 7e chase manager")
    parser.add_argument("--native", action="store_true", help="open in a native window")
    args = parser.parse_args()
    ui.run(root, title="Chase Manager", native=args.native, reload=False)


if __name__ == "__main__":
    main()
