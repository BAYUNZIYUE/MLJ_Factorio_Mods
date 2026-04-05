# Autocraft Notes

## OVERVIEW
The only TypeScript-first mod in this workspace; sources live in `src/*.ts` and are intended for Factorio/Lua output.

## WHERE TO LOOK
- Metadata: `autocraft/src/info.json`
- Runtime entry: `autocraft/src/control.ts`
- Data stage: `autocraft/src/data.ts`, `autocraft/src/data-final-fixes.ts`
- Settings stage: `autocraft/src/settings.ts`
- Core logic: `autocraft/src/autocraft.ts`
- Constants and storage typing: `autocraft/src/constants.ts`, `autocraft/src/storage.d.ts`
- Build hints only: `autocraft/README.md`

## CONVENTIONS
- Treat this directory as TypeScriptToLua-oriented, not plain Lua.
- Keep Factorio stage boundaries intact even in TS: runtime in `control.ts`, prototype work in `data*.ts`, settings in `settings.ts`.
- Use `pack_mods.py` only for packaging; it recognizes `.ts` entrypoints but does not compile them.
- Documented npm workflows in `README.md` are informative only in this checkout because `package.json` is absent.

## ANTI-PATTERNS
- Do not claim a build command works unless the required manifest/config exists in the checkout.
- Do not drop compiled-output assumptions into AGENTS; describe the source layout and packaging reality instead.
- Do not edit `obj/`; it is cache/output, not authored source.

## NOTES
- This mod deserves its own AGENTS because its toolchain and failure modes differ from the Lua mods.
