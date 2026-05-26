# Expend Toolbar Notes

## OVERVIEW

This mod is a Lua-first Factorio 2.0 mod that lets players create movable custom toolbars for items, tools, inventory counts, and remote-view access.

## WHERE TO LOOK

- Metadata: `expend-toolbar/src/info.json`
- Runtime entry: `expend-toolbar/src/control.lua`
- Data stage: `expend-toolbar/src/data.lua`, `expend-toolbar/src/data-final-fixes.lua`
- Settings stage: `expend-toolbar/src/settings.lua`
- Shared names and prototype ids: `expend-toolbar/src/names.lua`
- Runtime event registration: `expend-toolbar/src/runtime.lua`
- GUI drawing and toolbar state operations: `expend-toolbar/src/panel.lua`
- Inventory and quality counting: `expend-toolbar/src/stock.lua`
- Packaged resources: `expend-toolbar/src/_graphics/`, `expend-toolbar/src/locale/`

## CONVENTIONS

- Treat `expend-toolbar` as the only current mod identity. Keep `src/info.json` `name`, `names.mod`, shortcut names, sprite names, and `__expend-toolbar__` resource paths aligned.
- Do not reintroduce the old `toolbars-mod` identity or old Toolbars OOP identity.
- Keep authored files under `src/`; root `README.md` and `AGENTS.md` are documentation and must not be copied into runtime package contents.
- This mod intentionally does not keep compatibility with the previous Toolbars-style OOP runtime. Do not restore `core/`, `factorio/`, `gui/`, `lang/`, `model/`, `player/`, `control/`, `data/`, or `settings/` runtime subtrees.
- Keep runtime logic compact and process-oriented. The expected custom Lua files are `names.lua`, `stock.lua`, `panel.lua`, and `runtime.lua`, plus Factorio entry files.
- Personal-view logistic networks are side tooltip data, not part of the slot count overlay. Remote planet logistic networks are main count data.
- Toolbar pages use the per-user `columns` value as their configured width. Rows grow when the last slot is occupied and shrink when the tail rows are no longer needed.
- Guard quality reads from `prototypes.quality[...]` because removed quality mods or stale item records can contain quality names that no longer exist.
- Keep player-facing behavior documented in this directory's `README.md` when controls, settings, visible counts, remote view, or tooltip behavior changes.

## ANTI-PATTERNS

- Do not hard-code `toolbars-mod_*` prototype names or `__toolbars-mod__` asset paths.
- Do not count personal-view side inventories in the slot count overlay unless the player-facing behavior is intentionally changed and the README is updated.
- Do not reintroduce an inner `src/src/` tree. `src/` is already the Factorio package root; Lua modules should be nested directly below it by logical domain.
- Do not reintroduce one-class-per-file component trees for toolbar buttons, slots, events, or inventory wrappers.
- Do not put tests or investigation scripts inside `src/`; use root `tests/` for durable guards and `.codex/` for temporary probes.

## VERIFICATION

- Run the root packaging guard after structure or documentation changes: `python3 tests/verify_pack_mods_ignores_non_runtime_files.py`.
- Run `python3 pack_mods.py` after source or package-identity changes and confirm `ModZips/expend-toolbar_1.0.0.zip` is produced.
- For refresh bugs, inspect `stock.lua`, `panel.lua`, and `runtime.lua`. Player inventory/controller/surface events should call the immediate `refresh_now` path; the dirty repaint path is reserved for polling-only cases such as remote view or hovered logistic tooltips.
