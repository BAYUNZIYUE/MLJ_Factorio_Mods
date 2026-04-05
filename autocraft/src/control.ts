import type {
  OnLuaShortcutEvent,
  OnPlayerCancelledCraftingEvent,
  OnPlayerControllerChangedEvent,
  OnPlayerCraftedItemEvent,
  OnPlayerJoinedGameEvent,
  OnPlayerMainInventoryChangedEvent,
  OnGuiClosedEvent,
} from "factorio:runtime";
import { AUTOCRAFT_SOUND_ENABLED, CRAFTING_FINISHED_SOUND, SHORTCUT_NAME } from "./constants";
import { add_autocraft_logistics_section, do_crafting, pre_compute_recipes } from "./autocraft";

const enable_player_force_logistics_requests = () => {
  // TODO: I only care about the player force, but maybe others will want more
  const player_force = game.forces["player"];
  player_force.character_logistic_requests = true;
};

const on_configuration_changed = () => {
  storage.recipes = pre_compute_recipes();

  enable_player_force_logistics_requests();

  for (const [, player] of pairs(game.players)) {
    add_autocraft_logistics_section(player);
  }
};

const on_init = () => {
  storage.data = new LuaMap();

  on_configuration_changed();
};

const create_autocraft_logistics_section = (
  event: OnPlayerControllerChangedEvent | OnPlayerJoinedGameEvent,
) => {
  const player = game.get_player(event.player_index);
  if (!player) return;

  add_autocraft_logistics_section(player);
};

const trigger_crafting = (event: OnPlayerMainInventoryChangedEvent | OnGuiClosedEvent) => {
  const player = game.get_player(event.player_index);
  if (!player) return;

  if (
    (event.name === defines.events.on_gui_opened || event.name === defines.events.on_gui_closed) &&
    (event as OnGuiClosedEvent).gui_type !== defines.gui_type.controller
  ) {
    return;
  }

  do_crafting(player);
};

const on_player_crafted_item = (event: OnPlayerCraftedItemEvent) => {
  if (!event.item_stack.valid_for_read) return;

  const player = game.get_player(event.player_index);
  if (!player?.crafting_queue) return;

  const crafted_last_item_in_stack =
    player.crafting_queue.length > 0 && player.crafting_queue[0].count === 1;

  if (!crafted_last_item_in_stack) return;

  const data = storage.data?.get(event.player_index);

  if (data?.active_recipe_name === undefined) {
    // not autocrafting
    player.play_sound({ path: CRAFTING_FINISHED_SOUND });
    return;
  }

  if (player.mod_settings[AUTOCRAFT_SOUND_ENABLED].value as boolean) {
    player.play_sound({ path: CRAFTING_FINISHED_SOUND });
  }

  if (data.active_recipe_name === event.item_stack.name) {
    data.active_recipe_name = undefined;
    // last item in queue, immediately queue another
    if (player.crafting_queue.length === 1) {
      do_crafting(player, false);
    }
  }
};

const on_player_cancelled_crafting = (event: OnPlayerCancelledCraftingEvent) => {
  const data = storage.data?.get(event.player_index);
  if (data?.active_recipe_name !== event.recipe.name) return;

  data.active_recipe_name = undefined;

  const player = game.get_player(event.player_index);
  if (!player) return;

  player.set_shortcut_toggled(SHORTCUT_NAME, false);
};

const on_lua_shortcut = (event: OnLuaShortcutEvent) => {
  if (event.prototype_name !== SHORTCUT_NAME) return;

  enable_player_force_logistics_requests();

  const player = game.get_player(event.player_index);
  if (!player) return;

  add_autocraft_logistics_section(player);

  player.set_shortcut_toggled(SHORTCUT_NAME, !player.is_shortcut_toggled(SHORTCUT_NAME));

  do_crafting(player);
};

script.on_init(on_init);
script.on_configuration_changed(on_configuration_changed);

script.on_event(defines.events.on_player_crafted_item, on_player_crafted_item);
script.on_event(defines.events.on_player_cancelled_crafting, on_player_cancelled_crafting);
script.on_event(defines.events.on_lua_shortcut, on_lua_shortcut);

// to avoid an nth_tick trigger, we check after the controller UI is closed
// in case the player modified their requests
script.on_event(defines.events.on_gui_closed, trigger_crafting);
script.on_event(defines.events.on_player_main_inventory_changed, trigger_crafting);

script.on_event(defines.events.on_player_controller_changed, create_autocraft_logistics_section);
script.on_event(defines.events.on_player_joined_game, create_autocraft_logistics_section);

script.on_event(defines.events.on_force_reset, enable_player_force_logistics_requests);
script.on_event(defines.events.on_forces_merged, enable_player_force_logistics_requests);
script.on_event(defines.events.on_technology_effects_reset, enable_player_force_logistics_requests);
