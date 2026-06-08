from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


DEFAULT_FACTORIO_EXE = Path("/mnt/d/Steam/steamapps/common/Factorio/bin/x64/factorio.exe")
DEFAULT_USER_DATA = Path("/mnt/c/Users/MLJ/AppData/Roaming/Factorio")
DEFAULT_SCENARIO_NAME = "blueprint_lab_validation"


def lua_long_string(value: str) -> str:
    if "]]" in value:
        raise ValueError("blueprint string cannot be embedded as a Lua long string")
    return f"[[{value}]]"


def render_control_lua(blueprint_string: str) -> str:
    return f"""local blueprint_string = {lua_long_string(blueprint_string)}

local function validation_fail(message)
  log("BLUEPRINT_LAB_VALIDATION fail " .. tostring(message))
  error(message, 0)
end

local function run_validation()
  log("BLUEPRINT_LAB_VALIDATION start")

  local inventory = game.create_inventory(1)
  local stack = inventory[1]
  if not stack.set_stack({{name = "blueprint"}}) then
    validation_fail("set_stack blueprint failed")
  end

  local import_result = stack.import_stack(blueprint_string)
  log("BLUEPRINT_LAB_VALIDATION import_result=" .. tostring(import_result))
  if import_result ~= 0 then
    validation_fail("import_stack returned " .. tostring(import_result))
  end

  local blueprint_entities = stack.get_blueprint_entities() or {{}}
  local blueprint_tiles = stack.get_blueprint_tiles() or {{}}
  log("BLUEPRINT_LAB_VALIDATION blueprint_entities=" .. tostring(#blueprint_entities) .. " blueprint_tiles=" .. tostring(#blueprint_tiles))
  if #blueprint_entities == 0 then
    validation_fail("blueprint has no entities after import")
  end

  local needs_space_platform = false
  for _, tile in pairs(blueprint_tiles) do
    if tile.name == "space-platform-foundation" then
      needs_space_platform = true
      break
    end
  end

  local surface
  local build_position = {{x = 0, y = 0}}
  if needs_space_platform then
    game.forces.player.unlock_space_platforms()
    local ok, platform = pcall(function()
      return game.forces.player.create_space_platform{{
        name = "blueprint_lab_validation_platform",
        planet = "nauvis",
        starter_pack = "space-platform-starter-pack",
      }}
    end)
    if not ok then
      validation_fail("create_space_platform failed: " .. tostring(platform))
    end
    platform.hidden = true
    if platform.surface == nil then
      platform.apply_starter_pack()
    end
    surface = platform.surface
    if surface == nil then
      validation_fail("space platform surface was not created")
    end
    build_position = {{x = 64, y = 0}}
    local min_tile_x = nil
    local min_tile_y = nil
    for _, tile in pairs(blueprint_tiles) do
      if min_tile_x == nil or tile.position.x < min_tile_x then
        min_tile_x = tile.position.x
      end
      if min_tile_y == nil or tile.position.y < min_tile_y then
        min_tile_y = tile.position.y
      end
    end
    local platform_tiles = {{}}
    local platform_tile_keys = {{}}
    local function add_platform_tile(name, x, y)
      local key = tostring(name) .. ":" .. tostring(x) .. ":" .. tostring(y)
      if platform_tile_keys[key] then
        return
      end
      platform_tile_keys[key] = true
      platform_tiles[#platform_tiles + 1] = {{
        name = name,
        position = {{x = x, y = y}},
      }}
    end
    for _, tile in pairs(blueprint_tiles) do
      add_platform_tile(tile.name, tile.position.x + build_position.x, tile.position.y + build_position.y)
      add_platform_tile(tile.name, tile.position.x - min_tile_x + build_position.x, tile.position.y - min_tile_y + build_position.y)
    end
    surface.set_tiles(platform_tiles, true, true, true, false)
    log("BLUEPRINT_LAB_VALIDATION platform_tiles_set=" .. tostring(#platform_tiles))
    log("BLUEPRINT_LAB_VALIDATION surface=space-platform")
  else
    surface = game.create_surface("blueprint_lab_validation_surface")
    surface.request_to_generate_chunks({{0, 0}}, 8)
    surface.force_generate_chunk_requests()
    log("BLUEPRINT_LAB_VALIDATION surface=generic")
  end

  local can_place_checked = 0
  for _, entity in pairs(blueprint_entities) do
    if can_place_checked >= 8 then
      break
    end
    local entity_direction = entity.direction or defines.direction.north
    local can_place = surface.can_place_entity{{
      name = entity.name,
      position = {{
        x = entity.position.x + build_position.x,
        y = entity.position.y + build_position.y,
      }},
      direction = entity_direction,
      force = game.forces.player,
      build_check_type = defines.build_check_type.blueprint_ghost,
      forced = true,
    }}
    log("BLUEPRINT_LAB_VALIDATION can_place " .. entity.name .. "=" .. tostring(can_place))
    can_place_checked = can_place_checked + 1
  end

  local ok, built_entities = pcall(function()
    return stack.build_blueprint{{
      surface = surface.name,
      force = "player",
      position = build_position,
      build_mode = defines.build_mode.superforced,
      skip_fog_of_war = false,
      raise_built = false,
    }}
  end)
  if not ok then
    validation_fail("build_blueprint failed: " .. tostring(built_entities))
  end

  local built_count = #built_entities
  log("BLUEPRINT_LAB_VALIDATION built_entities=" .. tostring(built_count))
  if built_count == 0 then
    validation_fail("build_blueprint returned zero entities")
  end

  local surface_entities = surface.find_entities_filtered{{force = game.forces.player}}
  log("BLUEPRINT_LAB_VALIDATION surface_entities=" .. tostring(#surface_entities))
  log("BLUEPRINT_LAB_VALIDATION success")
  error("BLUEPRINT_LAB_VALIDATION completed", 0)
end

script.on_event(defines.events.on_tick, function(event)
  script.on_event(defines.events.on_tick, nil)
  run_validation()
end)
"""


def write_validation_scenario(
    *,
    user_data_dir: Path,
    scenario_name: str,
    blueprint_string: str,
) -> Path:
    scenario_dir = user_data_dir / "scenarios" / scenario_name
    scenario_dir.mkdir(parents=True, exist_ok=True)
    (scenario_dir / "info.json").write_text(
        json.dumps(
            {
                "name": scenario_name,
                "version": "1.0.0",
                "title": "Blueprint Lab Validation",
                "description": "Temporary scenario generated by Blueprint Lab to import and build one blueprint.",
                "factorio_version": "2.0",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (scenario_dir / "control.lua").write_text(render_control_lua(blueprint_string), encoding="utf-8")
    return scenario_dir


def write_server_settings(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "name": "Blueprint Lab Validation",
                "description": "Temporary server for Blueprint Lab validation.",
                "tags": [],
                "max_players": 0,
                "visibility": {"public": False, "lan": False},
                "username": "",
                "password": "",
                "token": "",
                "game_password": "",
                "require_user_verification": False,
                "max_upload_in_kilobytes_per_second": 0,
                "ignore_player_limit_for_returning_players": False,
                "allow_commands": "admins-only",
                "autosave_interval": 0,
                "autosave_slots": 1,
                "afk_autokick_interval": 0,
                "auto_pause": False,
                "auto_pause_when_players_connect": False,
                "only_admins_can_pause_the_game": True,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def validation_markers(log_text: str) -> list[str]:
    return [line for line in log_text.splitlines() if "BLUEPRINT_LAB_VALIDATION" in line]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate one generated blueprint with a real Factorio runtime scenario.")
    parser.add_argument("--factorio-exe", type=Path, default=DEFAULT_FACTORIO_EXE)
    parser.add_argument("--user-data-dir", type=Path, default=DEFAULT_USER_DATA)
    parser.add_argument("--mod-directory", type=Path)
    parser.add_argument("--scenario-name", default=DEFAULT_SCENARIO_NAME)
    parser.add_argument("--blueprint", type=Path, required=True)
    parser.add_argument("--console-log", type=Path, default=Path(".codex/tests/blueprint-lab-factorio-validation.log"))
    parser.add_argument("--until-tick", type=int, default=2)
    args = parser.parse_args(argv)

    blueprint_string = args.blueprint.read_text(encoding="utf-8").strip()
    scenario_dir = write_validation_scenario(
        user_data_dir=args.user_data_dir,
        scenario_name=args.scenario_name,
        blueprint_string=blueprint_string,
    )

    args.console_log.parent.mkdir(parents=True, exist_ok=True)
    server_settings = write_server_settings(args.console_log.parent / "blueprint-lab-server-settings.json")
    command = [
        str(args.factorio_exe),
        "--start-server-load-scenario",
        args.scenario_name,
        "--server-settings",
        str(server_settings),
        "--until-tick",
        str(args.until_tick),
        "--console-log",
        str(args.console_log),
        "--disable-audio",
    ]
    if args.mod_directory:
        command.extend(["--mod-directory", str(args.mod_directory)])

    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    log_text = args.console_log.read_text(encoding="utf-8", errors="replace") if args.console_log.exists() else ""
    markers = validation_markers(log_text + "\n" + completed.stdout + "\n" + completed.stderr)
    print(f"scenario={scenario_dir}")
    print(f"command_exit={completed.returncode}")
    for marker in markers:
        print(marker)
    if any("BLUEPRINT_LAB_VALIDATION success" in marker for marker in markers):
        return 0
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr)
        return completed.returncode
    print("FAIL: Factorio exited without validation success marker")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
