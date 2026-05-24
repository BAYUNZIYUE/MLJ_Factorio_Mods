# Expend Toolbar Notes

## OVERVIEW

This mod is a Lua-first Factorio 2.0 mod that lets players create movable custom toolbars for items, tools, inventory counts, and remote-view access.

## WHERE TO LOOK

- Metadata: `expend-toolbar/src/info.json`
- Runtime entry: `expend-toolbar/src/control.lua`
- Data stage: `expend-toolbar/src/data.lua`, `expend-toolbar/src/data-final-fixes.lua`
- Settings stage: `expend-toolbar/src/settings.lua`
- Shared mod constants and names: `expend-toolbar/src/core/Toolbars.lua`
- Runtime event registration: `expend-toolbar/src/control/`
- Core infrastructure: `expend-toolbar/src/core/`
- Toolbar slot models: `expend-toolbar/src/model/`
- GUI components: `expend-toolbar/src/gui/`
- Inventory and count refresh logic: `expend-toolbar/src/player/inventory/`
- Player/view selection logic: `expend-toolbar/src/player/Player.lua`
- Packaged resources: `expend-toolbar/src/_graphics/`, `expend-toolbar/src/locale/`

## CONVENTIONS

- Treat `expend-toolbar` as the only current mod identity. Keep `src/info.json` `name`, `Toolbars.name`, shortcut names, sprite names, remote interface names, and `__expend-toolbar__` resource paths aligned.
- Do not reintroduce the old `toolbars-mod` identity except in an explicit save migration or compatibility shim.
- Keep authored files under `src/`; root `README.md` and `AGENTS.md` are documentation and must not be copied into runtime package contents.
- Keep the `src/` package root reserved for Factorio entry files, metadata, changelog, thumbnail, and packaged resource directories. Custom runtime Lua belongs in domain subpackages such as `src/core/`, `src/model/`, `src/control/`, `src/gui/`, `src/player/`, and `src/factorio/`; prototype and sprite registration belongs under `src/data*.lua` or `src/data/`; settings definitions belong under `src/settings*.lua` or `src/settings/`.
- Toolbar slot counts are based on `ViewInventory` main inventories. Personal-view logistic networks are side inventories for tooltip/detail refresh, not part of the slot count overlay.
- Toolbar sections are tab-style pages. Keep the existing `Toolbar -> Sections -> Section` save shape, but only the active section content should be visible.
- Toolbar pages use the per-user `Toolbars.settings.columns` value as their configured width. Preserve occupied slots beyond the configured width instead of deleting them; shrink back only after those right-side slots are empty.
- Inventory refresh methods should return `true` only when their visible content actually changed. Do not publish `InventoryChanged` merely because a polling interval elapsed.
- Guard quality reads from `prototypes.quality[...]` because old saves, removed quality mods, or stale GUI tags can contain quality names that no longer exist.
- Keep player-facing behavior documented in this directory's `README.md` when controls, settings, visible counts, remote view, or tooltip behavior changes.

## ANTI-PATTERNS

- Do not hard-code `toolbars-mod_*` prototype names or `__toolbars-mod__` asset paths.
- Do not count personal-view side inventories in the slot count overlay unless the player-facing behavior is intentionally changed and the README is updated.
- Do not reintroduce an inner `src/src/` tree. `src/` is already the Factorio package root; Lua modules should be nested directly below it by logical domain.
- Do not add custom runtime support files directly under `src/` unless Factorio requires that filename at the package root.
- Do not put tests or investigation scripts inside `src/`; use root `tests/` for durable guards and `.codex/` for temporary probes.

## VERIFICATION

- Run the root packaging guard after structure or documentation changes: `python3 tests/verify_pack_mods_ignores_non_runtime_files.py`.
- Run `python3 pack_mods.py` after source or package-identity changes and confirm `ModZips/expend-toolbar_1.0.0.zip` is produced.
- For refresh bugs, inspect `ViewInventory`, the affected inventory class, and the relevant overlay/tooltip subscriber before changing polling intervals.
