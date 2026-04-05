# Autocraft Notes

## OVERVIEW
This mod now lives directly as Lua source under `src/*.lua` and can be packaged or deployed without a TS compilation step.

## WHERE TO LOOK
- Metadata: `autocraft/src/info.json`
- Runtime entry: `autocraft/src/control.lua`
- Data stage: `autocraft/src/data.lua`, `autocraft/src/data-final-fixes.lua`
- Settings stage: `autocraft/src/settings.lua`
- Core logic: `autocraft/src/autocraft.lua`
- Shared constants: `autocraft/src/constants.lua`
- Build and deployment notes: `autocraft/README.md`

## CONVENTIONS
- Treat this directory as a normal Lua Factorio mod.
- Keep Factorio stage boundaries intact: runtime in `control.lua`, prototype work in `data*.lua`, settings in `settings.lua`.
- Use `pack_mods.py` for packaging; it should produce a directly loadable Lua mod folder/archive.

## ANTI-PATTERNS
- Do not reintroduce non-Lua build tooling assumptions unless the actual build manifests are restored.
- Do not edit `obj/`; it is cache/output, not authored source.

## NOTES
- This mod keeps its own AGENTS because its gameplay logic is distinct, even though it now uses the same Lua-first packaging flow as the other mods.
