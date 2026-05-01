# PROJECT KNOWLEDGE BASE

## OVERVIEW

Factorio Lua mod workspace with multiple standalone mods plus one shared packer.
Each mod keeps authored source under `<mod>/src/`, and `pack_mods.py` packages
those sources into loadable Factorio archives under `ModZips/`.

## STRUCTURE

```text
mlj_factorio_mods/
├── pack_mods.py                # discovers <mod>/src/info.json and packs all mods
├── ModZips/                    # packaged artifacts only; do not edit as source
├── tests/                      # long-lived regression guards, when present
├── DynamicInventory/           # runtime/settings inventory resizing mod
├── py_quick_start/             # runtime/settings starter-items mod
├── section-autocraft/          # runtime/data/settings logistics-section autocraft mod
└── ups_saving_quality_ships/   # runtime/data Space Age platform quality mod
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Pack or validate all mods | `pack_mods.py` | Source of truth for discovery, ignored dirs, entrypoint names, zip naming, and opening `ModZips/` |
| Runtime inventory logic | `DynamicInventory/` | Runtime/settings mod; no `data.lua` |
| Starter item logic | `py_quick_start/` | Runtime/settings mod; no `data.lua` |
| Section Autocraft logic | `section-autocraft/` | Lua source directly under `src/` |
| Platform/cargo quality logic | `ups_saving_quality_ships/` | Event-driven runtime modules under `src/scripts/` |

## FACTORIO AUTHORING REFERENCES

- Official modding tutorial: `https://wiki.factorio.com/Tutorial:Modding_tutorial/Gangsir`
- Latest Factorio API docs: `https://lua-api.factorio.com/latest/index.html`
- Mod settings tutorial: `https://wiki.factorio.com/Tutorial:Mod_settings`
- Prototype docs: `https://lua-api.factorio.com/latest/index-prototype.html`
- Runtime docs: `https://lua-api.factorio.com/latest/index-runtime.html`
- Auxiliary docs: `https://lua-api.factorio.com/latest/index-auxiliary.html`
- Data lifecycle docs: `https://lua-api.factorio.com/latest/auxiliary/data-lifecycle.html`

Treat the official docs as authority. The notes below are local reminders, not a
replacement for the current Factorio API.

## FACTORIO LOAD ORDER AND FILE SHAPE

- Factorio sorts mods by dependency first, then by name where dependency order
  does not force a relationship. If mod `a` depends on `c`, `c` loads before
  `a`; an unrelated mod `b` may still sort before that dependency chain.
- Stage files are loaded across all enabled mods by stage order:
  `settings.lua`, `settings-updates.lua`, `settings-final-fixes.lua`,
  `data.lua`, `data-updates.lua`, `data-final-fixes.lua`.
- Runtime code belongs in `control.lua`; prototype edits belong in `data*.lua`;
  settings definitions belong in `settings*.lua`.
- Standard Factorio mod file shape is:

```text
<mod-folder>/
├── info.json
├── settings.lua
├── settings-updates.lua
├── settings-final-fixes.lua
├── data.lua
├── data-updates.lua
├── data-final-fixes.lua
├── control.lua
└── locale/
    └── <language>/
        └── locale.cfg
```

This workspace stores that shape under `<mod>/src/` and lets `pack_mods.py`
copy the contents into the archive root.

## CONVENTIONS

- This workspace stores mod metadata at `<mod>/src/info.json`, not at the mod
  root. `pack_mods.py` only discovers projects with that layout.
- Every mod root must have both `README.md` and `AGENTS.md`. `README.md` is
  player-facing or maintainer-facing documentation; `AGENTS.md` is the
  execution contract for that mod.
- Zip outputs must be `{info.name}_{info.version}.zip`, and the archive root
  must be `{info.name}_{info.version}/` rather than loose files.
- Runtime persistence uses `storage`, not legacy `global`.
- Locale files stay under `src/locale/<lang>/...`; do not create AGENTS files
  inside locale trees.
- Long-lived regression tests belong under the repository root `tests/`, grouped
  by domain or mod name. Do not place test files inside any mod `src/` tree.
- One-off investigation scripts are temporary. Put them under `.codex/` while
  working, or remove them before handoff if they are not useful regression
  guards.
- Bilingual content is normal in docs, locale, and some comments; preserve
  meaning when touching mixed Chinese/English text.
- In WSL, `pack_mods.py` should open `ModZips/` with Windows Explorer through
  `/mnt/c/Windows/explorer.exe` after converting the path with `wslpath -w`.

## ANTI-PATTERNS

- Do not mix Factorio stages: `game` and runtime objects belong in `control.lua`;
  `data` and prototype work belong in `data*.lua`.
- Do not edit `ModZips/`, `obj/`, or `__pycache__/` as source; they are outputs
  or caches.
- Do not keep tests under `<mod>/tests/` or `<mod>/src/tests/`; use root
  `tests/` for durable regression checks so packaging output stays clean.
- Do not move `info.json` out of `src/`; the packer will stop discovering that
  mod.
- Do not assume README commands are backed by manifests in this checkout; verify
  local tooling files before claiming a build step exists.
- Do not push unless explicitly approved by the user.

## COMMANDS

```bash
python3 tests/verify_pack_mods_ignores_non_runtime_files.py
python3 pack_mods.py
```

## BUILD AND DEBUG DEPLOYMENT

- Run `python3 pack_mods.py` to package every discovered mod.
- Confirm the target artifact name under `ModZips/`.
- For active Factorio debugging, prefer deploying the unpacked mod folder to
  `%AppData%\Factorio\mods`, not only the `.zip`.
- The folder deployed to `%AppData%\Factorio\mods` must be the archive root,
  for example `{info.name}_{info.version}/`; do not deploy raw `src/` directly.
- Before deploying a folder version, remove the old version of the same mod from
  the Factorio mods directory. Do not keep old `.zip` and folder copies of the
  same mod side by side.

## GIT PRACTICES

- Commit messages in Chinese, conventional style: `功能：`, `修复：`, `重构：`,
  `杂项：`.
- Keep commits atomic: one logical change per commit.
- When running `git add` or `git commit` in this workspace, prefer the host
  Windows Git executable: `'/mnt/c/Program Files/Git/cmd/git.exe'`.
- All Git operations must run serially. Do not run `git add`, `git commit`,
  `git rebase`, `git stash`, `git checkout`, `git merge`, or any other Git
  command in parallel.
- Do not push unless explicitly approved by the user.

## CODEX WORKFLOW CONFIRMATION

- Read the nearest `AGENTS.md` before editing and obey the most specific file.
- Inspect the current code and real workspace state before making claims.
- Prefer direct execution for clear requests; ask only when a missing decision is
  risky or cannot be inferred.
- Before deleting files, moving files, changing system configuration, or doing
  other high-risk operations, request explicit confirmation.
- Keep edits scoped to the requested behavior and existing project patterns.
- Use `apply_patch` for manual file edits.
- Run relevant verification before saying work is complete, fixed, or passing.
- Report exact commands and real outcomes, including skipped or failed
  verification.

## NOTES

- `pack_mods.py` ignores `.git`, `.idea`, `.vscode`, `.vs`, `__pycache__`,
  `bin`, `obj`, `tests`, `AGENTS.md`, `README.md`, plus `.zip` and `.psd`
  files.
- There is no repo-wide CI workflow in this checkout. Use the root `tests/`
  guards plus `python3 pack_mods.py` as the baseline validation unless a touched
  mod adds another dedicated local check.
- If a change may affect save compatibility, migration behavior, event legality,
  or Factorio API usage, re-check the official Factorio docs before editing.
