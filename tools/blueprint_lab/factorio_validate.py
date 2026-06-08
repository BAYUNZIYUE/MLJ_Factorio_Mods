from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


DEFAULT_FACTORIO_EXE = Path("/mnt/d/Steam/steamapps/common/Factorio/bin/x64/factorio.exe")
DEFAULT_USER_DATA = Path("/mnt/c/Users/MLJ/AppData/Roaming/Factorio")
DEFAULT_SCENARIO_NAME = "blueprint_lab_validation"
POWERSHELL_EXE = Path("/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")
TASKKILL_EXE = Path("/mnt/c/Windows/System32/taskkill.exe")


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

local function sorted_count_string(counts)
  local keys = {{}}
  for key, _ in pairs(counts) do
    keys[#keys + 1] = key
  end
  table.sort(keys)
  local parts = {{}}
  for _, key in pairs(keys) do
    parts[#parts + 1] = tostring(key) .. ":" .. tostring(counts[key])
  end
  return table.concat(parts, ",")
end

local function add_count(counts, key)
  local count_key = tostring(key)
  counts[count_key] = (counts[count_key] or 0) + 1
end

local function entity_status_name(status)
  if status == nil then
    return "nil"
  end
  for name, value in pairs(defines.entity_status) do
    if value == status then
      return name
    end
  end
  return tostring(status)
end

local function audit_recipe_machines(surface)
  local recipe_machine_count = 0
  local recipe_counts = {{}}
  local status_counts = {{}}
  local crafting_speed_positive = 0
  local products_finished_total = 0
  local electric_connected_count = 0
  local electric_checked_count = 0
  local module_item_total = 0
  local output_item_total = 0
  for _, entity in pairs(surface.find_entities_filtered{{force = "player"}}) do
    local ok_recipe, recipe = pcall(function()
      return entity.get_recipe()
    end)
    if ok_recipe and recipe ~= nil then
      recipe_machine_count = recipe_machine_count + 1
      add_count(recipe_counts, recipe.name)
      add_count(status_counts, entity_status_name(entity.status))
      if entity.crafting_speed ~= nil and entity.crafting_speed > 0 then
        crafting_speed_positive = crafting_speed_positive + 1
      end
      if entity.products_finished ~= nil then
        products_finished_total = products_finished_total + entity.products_finished
      end
      local ok_connected, connected = pcall(function()
        return entity.is_connected_to_electric_network()
      end)
      if ok_connected then
        electric_checked_count = electric_checked_count + 1
        if connected then
          electric_connected_count = electric_connected_count + 1
        end
      end
      local module_inventory = entity.get_module_inventory()
      if module_inventory ~= nil then
        module_item_total = module_item_total + module_inventory.get_item_count()
      end
      local output_inventory = entity.get_output_inventory()
      if output_inventory ~= nil then
        output_item_total = output_item_total + output_inventory.get_item_count()
      end
    end
  end
  log("BLUEPRINT_LAB_VALIDATION recipe_machine_audit machines=" .. tostring(recipe_machine_count) .. " recipes=" .. sorted_count_string(recipe_counts) .. " status=" .. sorted_count_string(status_counts))
  log("BLUEPRINT_LAB_VALIDATION recipe_machine_runtime crafting_speed_positive=" .. tostring(crafting_speed_positive) .. " electric_connected=" .. tostring(electric_connected_count) .. "/" .. tostring(electric_checked_count) .. " products_finished=" .. tostring(products_finished_total) .. " module_items=" .. tostring(module_item_total) .. " output_items=" .. tostring(output_item_total))
end

local validation_started = false
local pending_audit_surface = nil
local pending_audit_tick = nil
local runtime_audit_wait_ticks = 120

local function run_validation()
  log("BLUEPRINT_LAB_VALIDATION start")
  game.forces.player.enable_all_recipes()
  game.forces.player.enable_all_technologies()
  log("BLUEPRINT_LAB_VALIDATION force_unlocks=all_recipes,all_technologies")

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
    log("BLUEPRINT_LAB_VALIDATION manual_fallback=start")
    local manual_count = 0
    local manual_failures = 0
    local recipe_failures = 0
    local recipe_set_count = 0
    local underground_type_count = 0
    local underground_type_failures = 0
    local module_inserted_count = 0
    local module_insert_failures = 0
    for _, entity in pairs(blueprint_entities) do
      local entity_direction = entity.direction or defines.direction.north
      local ok_create, created = pcall(function()
        return surface.create_entity{{
          name = entity.name,
          position = {{
            x = entity.position.x + build_position.x,
            y = entity.position.y + build_position.y,
          }},
          direction = entity_direction,
          type = entity.type,
          quality = entity.quality,
          force = "player",
          raise_built = false,
        }}
      end)
      if not ok_create or created == nil then
        manual_failures = manual_failures + 1
        if manual_failures <= 8 then
          log("BLUEPRINT_LAB_VALIDATION manual_create_failed " .. entity.name .. "=" .. tostring(created))
        end
      else
        manual_count = manual_count + 1
        if entity.type ~= nil then
          local ok_belt_type, belt_type_result = pcall(function()
            return created.belt_to_ground_type
          end)
          if ok_belt_type and belt_type_result == entity.type then
            underground_type_count = underground_type_count + 1
          else
            underground_type_failures = underground_type_failures + 1
            if underground_type_failures <= 8 then
              log("BLUEPRINT_LAB_VALIDATION manual_underground_type_failed " .. entity.name .. "=" .. tostring(belt_type_result) .. " expected=" .. tostring(entity.type))
            end
          end
        end
        if entity.recipe ~= nil then
          local ok_recipe, recipe_result = pcall(function()
            if entity.recipe_quality == nil or entity.recipe_quality == "normal" then
              created.set_recipe(entity.recipe)
            else
              created.set_recipe(entity.recipe, entity.recipe_quality)
            end
          end)
          if not ok_recipe then
            recipe_failures = recipe_failures + 1
            if recipe_failures <= 8 then
              log("BLUEPRINT_LAB_VALIDATION manual_recipe_failed " .. entity.name .. "=" .. tostring(recipe_result))
            end
          else
            recipe_set_count = recipe_set_count + 1
          end
        end
        if entity.items ~= nil then
          local module_inventory = created.get_module_inventory()
          if module_inventory ~= nil then
            for _, item_stack in pairs(entity.items) do
              local item_id = item_stack.id or {{}}
              local requested_count = 0
              local item_payload = item_stack.items or {{}}
              for _, inventory_stack in pairs(item_payload.in_inventory or {{}}) do
                requested_count = requested_count + 1
              end
              if requested_count > 0 and item_id.name ~= nil then
                local ok_insert, inserted_count = pcall(function()
                  return module_inventory.insert{{
                    name = item_id.name,
                    quality = item_id.quality,
                    count = requested_count,
                  }}
                end)
                if ok_insert then
                  module_inserted_count = module_inserted_count + inserted_count
                  if inserted_count ~= requested_count then
                    module_insert_failures = module_insert_failures + 1
                    if module_insert_failures <= 8 then
                      log("BLUEPRINT_LAB_VALIDATION manual_module_partial " .. entity.name .. "=" .. tostring(inserted_count) .. "/" .. tostring(requested_count))
                    end
                  end
                else
                  module_insert_failures = module_insert_failures + 1
                  if module_insert_failures <= 8 then
                    log("BLUEPRINT_LAB_VALIDATION manual_module_failed " .. entity.name .. "=" .. tostring(inserted_count))
                  end
                end
              end
            end
          end
        end
      end
    end
    log("BLUEPRINT_LAB_VALIDATION manual_entities=" .. tostring(manual_count) .. " manual_failures=" .. tostring(manual_failures) .. " manual_recipe_set=" .. tostring(recipe_set_count) .. " manual_recipe_failures=" .. tostring(recipe_failures))
    log("BLUEPRINT_LAB_VALIDATION manual_underground_types=" .. tostring(underground_type_count) .. " manual_underground_type_failures=" .. tostring(underground_type_failures) .. " manual_modules_inserted=" .. tostring(module_inserted_count) .. " manual_module_failures=" .. tostring(module_insert_failures))
    if manual_failures > 0 or recipe_failures > 0 or underground_type_failures > 0 or module_insert_failures > 0 then
      validation_fail("manual fallback failed to place all entities")
    end
  end

  local surface_entities = surface.find_entities_filtered{{force = game.forces.player}}
  log("BLUEPRINT_LAB_VALIDATION surface_entities=" .. tostring(#surface_entities))
  pending_audit_surface = surface
  pending_audit_tick = game.tick + runtime_audit_wait_ticks
  log("BLUEPRINT_LAB_VALIDATION runtime_audit_wait_ticks=" .. tostring(runtime_audit_wait_ticks))
end

script.on_event(defines.events.on_tick, function(event)
  if not validation_started then
    validation_started = true
    run_validation()
    return
  end
  if pending_audit_surface ~= nil and game.tick >= pending_audit_tick then
    script.on_event(defines.events.on_tick, nil)
    audit_recipe_machines(pending_audit_surface)
    log("BLUEPRINT_LAB_VALIDATION success")
    validation_fail("completed")
  end
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


def process_output_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def kill_factorio_processes_for_scenario(scenario_name: str) -> list[int]:
    if not POWERSHELL_EXE.exists() or not TASKKILL_EXE.exists():
        return []
    command = (
        "Get-CimInstance Win32_Process -Filter \"Name = 'factorio.exe'\" | "
        f"Where-Object {{ $_.CommandLine -like '*{scenario_name}*' }} | "
        "ForEach-Object { $_.ProcessId }"
    )
    found = subprocess.run(
        [str(POWERSHELL_EXE), "-NoProfile", "-Command", command],
        text=True,
        capture_output=True,
        check=False,
    )
    killed: list[int] = []
    for line in found.stdout.splitlines():
        line = line.strip()
        if not line.isdigit():
            continue
        pid = int(line)
        subprocess.run([str(TASKKILL_EXE), "/PID", str(pid), "/T", "/F"], capture_output=True, check=False)
        killed.append(pid)
    return killed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate one generated blueprint with a real Factorio runtime scenario.")
    parser.add_argument("--factorio-exe", type=Path, default=DEFAULT_FACTORIO_EXE)
    parser.add_argument("--user-data-dir", type=Path, default=DEFAULT_USER_DATA)
    parser.add_argument("--mod-directory", type=Path)
    parser.add_argument("--scenario-name", default=DEFAULT_SCENARIO_NAME)
    parser.add_argument("--blueprint", type=Path, required=True)
    parser.add_argument("--console-log", type=Path, default=Path(".codex/tests/blueprint-lab-factorio-validation.log"))
    parser.add_argument("--until-tick", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=float, default=45)
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

    timed_out = False
    killed_pids: list[int] = []
    try:
        completed = subprocess.run(command, text=True, capture_output=True, check=False, timeout=args.timeout_seconds)
        stdout = completed.stdout
        stderr = completed.stderr
        command_exit: int | str = completed.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = process_output_text(exc.stdout)
        stderr = process_output_text(exc.stderr)
        killed_pids = kill_factorio_processes_for_scenario(args.scenario_name)
        command_exit = "timeout"
    log_text = args.console_log.read_text(encoding="utf-8", errors="replace") if args.console_log.exists() else ""
    markers = validation_markers(log_text + "\n" + stdout + "\n" + stderr)
    print(f"scenario={scenario_dir}")
    print(f"command_exit={command_exit}")
    if timed_out:
        print(f"timeout_seconds={args.timeout_seconds}")
        print(f"killed_factorio_pids={killed_pids}")
    for marker in markers:
        print(marker)
    if any("BLUEPRINT_LAB_VALIDATION success" in marker for marker in markers):
        return 0
    if timed_out:
        print(stdout)
        print(stderr)
        return 124
    if command_exit != 0:
        print(stdout)
        print(stderr)
        return int(command_exit)
    print("FAIL: Factorio exited without validation success marker")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
