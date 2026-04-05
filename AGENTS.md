# PROJECT KNOWLEDGE BASE

**Generated:** 2026-03-31T11:53:20+08:00
**Commit:** n/a (not a git repo)
**Branch:** n/a (not a git repo)

## OVERVIEW
Factorio mod workspace with six standalone mods plus one shared packer. Mods in this workspace are authored directly in Lua under `src/`.

## STRUCTURE
```text
MLJ_Factorio_Mods/
├── pack_mods.py                # discovers `<mod>/src/info.json`, validates, zips into ModZips/
├── ModZips/                    # packaged artifacts only; do not edit as source
├── MOD编写说明.txt             # local reminder of official Factorio docs and stage order
├── autocraft/                  # runtime/data/settings mod authored directly in Lua
├── DynamicInventory/           # runtime-only inventory resizing mod
├── factorio-todo-list/         # largest mod; todo domain + UI + spec tests
├── mythic-quality-fg/          # small prototype/settings-heavy mod
├── py_quick_start/             # runtime-only starter-items mod
└── ups_saving_quality_ships/   # runtime/data mod with script modules under `src/scripts`
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Pack or validate all mods | `pack_mods.py` | Source of truth for project discovery, ignored dirs, entrypoint names, zip naming |
| Confirm Factorio stage order | `MOD编写说明.txt` | Defers to official docs; local summary only |
| Runtime UI-heavy work | `factorio-todo-list/` | Most complex Lua mod; has specs |
| Platform/cargo logic | `ups_saving_quality_ships/` | Event-driven runtime split into script modules |
| Prototype and quality tuning changes | `mythic-quality-fg/` | `data.lua` forwards into `src/prototypes/`, while `data-updates.lua` tweaks quality behavior |
| Runtime-only player inventory logic | `DynamicInventory/`, `py_quick_start/` | No `data.lua`; mainly `control.lua` + `settings.lua` |
| Autocraft runtime/data work | `autocraft/` | Lua sources live directly under `src/` |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `main` | Python function | `pack_mods.py` | Workspace pack/validate entrypoint |
| `todo.mod_init` | Lua function | `factorio-todo-list/src/todo/todo.lua` | Initializes `storage.todo`, recreates maximize buttons, and clears stale main frames |
| `todo.on_gui_click` | Lua function | `factorio-todo-list/src/todo/todo.lua` | Central GUI click dispatcher |
| `resize_inventory` | Lua function | `DynamicInventory/src/control.lua` | Adjusts free inventory slots at runtime |
| `rebuild_runtime_state` | Lua function | `ups_saving_quality_ships/src/control.lua` | Rebuilds caches and script state on init/config change |
| `Public.rebuild` | Lua function | `ups_saving_quality_ships/src/scripts/platform_cache.lua` | Recomputes platform caches |

## CONVENTIONS
- Treat the official docs as authority: `https://lua-api.factorio.com/latest/`, especially Data Lifecycle, Runtime, Prototype, Mod Structure, Migrations, and Events.
- This workspace stores mod metadata at `<mod>/src/info.json`, not at the mod root. `pack_mods.py` only discovers projects with that layout.
- `pack_mods.py` accepts standard Factorio entrypoint names in `src/` (`control.*`, `data.*`, `settings.*`, update/final-fixes variants); `autocraft` is now authored directly in Lua.
- Zip outputs must be `{info.name}_{info.version}.zip`, and the archive root must be that directory name rather than loose files.
- Runtime persistence uses `storage`, not legacy `global`.
- Locale files stay under `src/locale/<lang>/...`; do not create AGENTS files inside locale trees.

## ANTI-PATTERNS (THIS PROJECT)
- Do not mix Factorio stages: `game`/runtime objects belong in `control.*`; `data`/prototype work belongs in `data.*`; verify against the official stage docs before editing.
- Do not edit `ModZips/` or `obj/` as source; they are outputs/cache, not authoring locations.
- Do not assume README commands are always backed by manifests in this checkout; verify local tooling files before claiming a build step exists.
- Do not move `info.json` out of `src/`; the packer will stop discovering that mod.
- Do not add duplicate per-locale or per-artifact documentation; parent AGENTS should cover those directories.

## UNIQUE STYLES
- Bilingual content is normal in docs, locale, and some comments; preserve meaning when touching mixed Chinese/English text.
- `factorio-todo-list` follows a `todo/` namespace with many files mutating one shared `todo` table.
- `ups_saving_quality_ships` splits runtime responsibilities by mechanism (`cargo_pods`, `platform_cache`, `logistic_section_change`, `hub_quality_change`) and coordinates through shared `storage.usqs` state.
- `mythic-quality-fg` keeps `data.lua` tiny and pushes prototype details into `src/prototypes/`.

## COMMANDS
```bash
python3 pack_mods.py
```

## BUILD AND DEBUG DEPLOYMENT
- 先运行 `python3 pack_mods.py`，打包当前工作区内所有模组。
- 然后打开 `ModZips/` 文件夹，确认目标模组的最新产物名称。
- 如果修改了某个模组，调试时优先把该模组以“文件夹形式”而不是 `.zip` 形式放入 Factorio 模组目录：
  - Windows 环境变量路径：`%AppData%\Factorio\mods`
- 这里的“文件夹形式”指的是压缩包内根目录那一层模组文件夹（例如 `{info.name}_{info.version}`），不是把 `src/` 目录直接拷贝到 `%AppData%\Factorio\mods`。
- 部署某个模组的文件夹版本前，先移除同模组的旧版本；无论旧版本是 `.zip` 还是同名文件夹，都不要同时保留。
- 这种“模组文件夹直放到 mods 目录”的方式是异星支持的热重载调试流程，便于反复修改和验证。

## GIT PRACTICES
- Commit messages in **Chinese**, conventional style: `功能：`, `修复：`, `重构：`, `杂项：`
- Atomic commits (one logical change per commit)
- When running `git add` / `git commit` in this workspace, prefer the host Windows Git executable: `'/mnt/c/Program Files/Git/cmd/git.exe'`
- All Git operations must run serially. Do not run `git add`, `git commit`, `git rebase`, `git stash`, `git checkout`, `git merge` or any other Git command in parallel. Even when the target files do not overlap, wait until the previous Git command has fully finished and the repository lock has been released before starting the next Git command.
- Do **not** push unless explicitly approved by the user

## NOTES
- `pack_mods.py` ignores `.git`, `.idea`, `.vscode`, `.vs`, `__pycache__`, `bin`, `obj`, plus `.zip` and `.psd` files.
- Only `factorio-todo-list/spec/` contains obvious automated tests in this checkout; there is no repo-wide CI workflow.
- If a change may affect save compatibility, migration behavior, or event legality, re-check the official Factorio docs before editing.
