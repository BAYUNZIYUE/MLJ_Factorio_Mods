# Blueprint & Upgrade Planner Quality Cycler Notes

## OVERVIEW

Runtime-only helper mod for changing blueprint and upgrade planner qualities
with the quality up/down controls.

## WHERE TO LOOK

- Metadata and dependencies: `quality-cycler/src/info.json`
- Input definitions: `quality-cycler/src/data.lua`
- Runtime blueprint and mapper editing: `quality-cycler/src/control.lua`
- Player-facing text: `quality-cycler/src/locale/`

## CONVENTIONS

- Support writable blueprints, blueprint books, and upgrade planners. Do not
  claim hover-specific row editing unless the in-game API exposes a writable
  target object and row information.
- Quality order must come from runtime prototypes, not a hard-coded vanilla or
  `ic-more-qualities` list.
- Never wrap from the highest quality to the lowest, or from the lowest quality
  to the highest.
- Do not modify a source quality that represents "any quality".
