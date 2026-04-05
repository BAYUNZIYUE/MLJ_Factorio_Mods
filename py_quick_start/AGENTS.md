# Pyanodons Quick Start Notes

## OVERVIEW
Runtime-only starter-items mod that grants equipment and robots when players enter the world or finish cutscenes.

## WHERE TO LOOK
- Metadata: `py_quick_start/src/info.json`
- Runtime logic: `py_quick_start/src/control.lua`
- Settings: `py_quick_start/src/settings.lua`
- Helpers/debug printing: `py_quick_start/src/utils.lua`

## CONVENTIONS
- This mod is driven entirely from runtime events; there is no `data.lua` in this checkout.
- Item grant logic is intentionally guarded by `storage["playerWithEquipment"]` to avoid duplicate rewards.
- Mixed Chinese/English comments are part of the local authoring style; preserve intent if you touch them.
- The logic explicitly accounts for cutscene timing and missing `player.character`.

## ANTI-PATTERNS
- Do not remove the duplicate-grant guard unless you are redesigning initialization end-to-end.
- Do not assume armor grids or character inventories are always available during join/cutscene events.
