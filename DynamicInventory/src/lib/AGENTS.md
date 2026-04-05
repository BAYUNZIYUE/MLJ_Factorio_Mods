# DynamicInventory Lib Notes

## OVERVIEW
Pure helper layer for `DynamicInventory`; keep gameplay event wiring out of this directory.

## WHERE TO LOOK
- String helpers: `DynamicInventory/src/lib/common.lua`
- Functional helpers: `DynamicInventory/src/lib/functional.lua`

## CONVENTIONS
- Prefer small reusable helpers that can be called from runtime code without side effects.
- Keep these files independent from `storage`, `script.on_event`, and direct GUI manipulation.
- Follow the existing plain Lua helper style instead of introducing new object systems.

## ANTI-PATTERNS
- Do not add Factorio event registration here.
- Do not make helpers depend on a specific player or surface unless the helper is explicitly runtime-bound.
