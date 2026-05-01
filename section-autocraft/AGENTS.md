# Section Autocraft Notes

## OVERVIEW
This mod now lives directly as Lua source under `src/*.lua` and can be packaged or deployed without a TS compilation step.

## WHERE TO LOOK
- Metadata: `section-autocraft/src/info.json`
- Runtime entry: `section-autocraft/src/control.lua`
- Data stage: `section-autocraft/src/data.lua`, `section-autocraft/src/data-final-fixes.lua`
- Settings stage: `section-autocraft/src/settings.lua`
- Core logic: `section-autocraft/src/autocraft.lua`
- Shared constants: `section-autocraft/src/constants.lua`
- Build and deployment notes: `section-autocraft/README.md`

## CONVENTIONS
- Treat this directory as a normal Lua Factorio mod.
- Keep Factorio stage boundaries intact: runtime in `control.lua`, prototype work in `data*.lua`, settings in `settings.lua`.
- Use `pack_mods.py` for packaging; it should produce a directly loadable Lua mod folder/archive.
- Performance profile logging is controlled only by the hardcoded `AUTOCRAFT_PERFORMANCE_PROFILE_ENABLED` constant in `src/autocraft.lua`.
- When the user asks to change Section Autocraft behavior, especially CT/performance optimization, set `AUTOCRAFT_PERFORMANCE_PROFILE_ENABLED = true`, run `python3 pack_mods.py`, and deploy the unpacked `section-autocraft_<version>` folder to `%AppData%\Factorio\mods` for live testing.
- When the user asks to bump/release the version, or explicitly asks to disable logs, set `AUTOCRAFT_PERFORMANCE_PROFILE_ENABLED = false` before packaging/deploying so normal players do not pay the logging cost.
- Do not add or rely on runtime commands to toggle Section Autocraft performance logging; the workflow is source-constant based.

## ANTI-PATTERNS
- Do not reintroduce non-Lua build tooling assumptions unless the actual build manifests are restored.
- Do not edit `obj/`; it is cache/output, not authored source.
- Do not leave performance profile logging enabled for a release/version-bump handoff unless the user explicitly says to keep logs on.

## NOTES
- This mod keeps its own AGENTS because its gameplay logic is distinct, even though it now uses the same Lua-first packaging flow as the other mods.
