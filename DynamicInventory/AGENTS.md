# DynamicInventory Notes

## OVERVIEW
Small runtime-focused mod that resizes player inventory dynamically from `control.lua` and player settings.

## WHERE TO LOOK
- Metadata and dependencies: `DynamicInventory/src/info.json`
- Runtime logic: `DynamicInventory/src/control.lua`
- Settings definitions: `DynamicInventory/src/settings.lua`
- Shared helpers: `DynamicInventory/src/lib/`
- Packaging behavior: `pack_mods.py`

## CONVENTIONS
- There is no `data.lua`; treat this as a runtime/settings mod.
- State lives in `storage.need_resize` and is keyed by player name in the nth-tick path.
- Keep inventory behavior idempotent: event handlers should tolerate repeated calls.
- Preserve the existing mixed Chinese/English comment style unless you are actively clarifying a touched block.

## ANTI-PATTERNS
- Do not move general helpers into `control.lua` when they belong in `src/lib/`.
- Do not assume `player.character` or `get_main_inventory()` always exists.
- Do not change key names in `player.mod_settings[...]` casually; runtime logic reads them directly.

## NOTES
- `DynamicInventory/src/lib/` has its own AGENTS file because helper code is reused as a separate micro-domain.
