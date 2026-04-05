import type { ItemID, ItemProduct, LuaLogisticSection, LuaPlayer } from "factorio:runtime";
import { AUTOCRAFT_LOGISTICS_SECTION_NAME, SHORTCUT_NAME } from "./constants";

type ItemRequest = {
  name: string;
  min: number;
  count: number;
  ratio: number;
};

export const pre_compute_recipes = () => {
  const cache = new LuaMap<string, LuaSet<string>>();

  for (const [, recipe] of pairs(
    prototypes.get_recipe_filtered([{ filter: "has-product-item" }]),
  )) {
    const products = recipe.products as ItemProduct[]; // guaranteed due to filter

    for (const product of products) {
      const recipes = cache.get(product.name) ?? new LuaSet();

      recipes.add(recipe.name);
      cache.set(product.name, recipes);
    }
  }

  return cache;
};

const find_autocraft_logistics_section = (player: LuaPlayer) => {
  const logistic_point = player.get_requester_point();
  if (!logistic_point) return undefined;

  for (const section of logistic_point.sections) {
    // TODO: make section name configurable
    if (section.is_manual && section.group === AUTOCRAFT_LOGISTICS_SECTION_NAME) {
      return section;
    }
  }

  return undefined;
};

export const add_autocraft_logistics_section = (player: LuaPlayer) => {
  const logistic_point = player.get_requester_point();
  if (!logistic_point) return undefined;

  if (!find_autocraft_logistics_section(player)) {
    const section = logistic_point.add_section(AUTOCRAFT_LOGISTICS_SECTION_NAME);
    if (section) {
      section.active = false;
    }
  }
};

const section_to_requests = (
  player: LuaPlayer,
  section: LuaLogisticSection,
  crafting_complete: boolean,
) => {
  const item_requests: ItemRequest[] = [];

  for (const filter of section.filters) {
    if (filter.min === undefined || filter.min === 0) {
      continue;
    }

    let name: string;
    if (typeof filter.value === "string") {
      name = filter.value;
    } else if (filter.value?.type === "item") {
      name = filter.value.name;
    } else {
      continue;
    }

    const count = player.get_item_count(name) + (crafting_complete ? 0 : 1);
    if (count >= filter.min) continue;

    item_requests.push({ name, min: filter.min, count, ratio: count / filter.min });
  }

  return item_requests;
};

const recipe_for_item = (player: LuaPlayer, item_name: string) => {
  const recipes = storage.recipes?.get(item_name);
  if (recipes === undefined) return undefined;

  for (const recipe_name of recipes) {
    // TODO: deal with multi-product recipes
    const recipe = player.force.recipes[recipe_name];
    const can_craft =
      !recipe.hidden && recipe.enabled && player.get_craftable_count(recipe_name) > 0;

    if (can_craft) {
      return recipe_name;
    }
  }
};

const item_id_to_name = (item: ItemID) => {
  if (typeof item === "string") {
    return item;
  } else {
    return item.name;
  }
};

const pick_recipe = (player: LuaPlayer, crafting_complete: boolean): string | undefined => {
  const autocraft_section = find_autocraft_logistics_section(player);
  if (autocraft_section === undefined) return undefined;

  const item_requests = section_to_requests(player, autocraft_section, crafting_complete);
  if (item_requests.length === 0) return undefined;

  item_requests.sort((a, b) => {
    if (a.ratio < b.ratio) return -1;
    if (a.ratio === b.ratio) return 0;
    return 1;
  });

  const hand_item_name = player.cursor_stack?.valid_for_read
    ? player.cursor_stack.name
    : player.cursor_ghost
      ? item_id_to_name(player.cursor_ghost.name)
      : undefined;

  if (hand_item_name !== undefined && item_requests.some((item) => item.name === hand_item_name)) {
    const recipe = recipe_for_item(player, hand_item_name);
    if (recipe !== undefined) return recipe;
  }

  for (const item_request of item_requests) {
    const recipe = recipe_for_item(player, item_request.name);
    if (recipe !== undefined) return recipe;
  }

  return undefined;
};

export const do_crafting = (player: LuaPlayer, crafting_complete = true) => {
  const is_eligible =
    player.connected &&
    player.controller_type === defines.controllers.character &&
    player.ticks_to_respawn === undefined &&
    player.is_shortcut_toggled(SHORTCUT_NAME);

  if (!is_eligible) return;

  const allowed_queue_length = crafting_complete ? 0 : 1;

  if (player.crafting_queue && player.crafting_queue.length > allowed_queue_length) {
    return;
  }

  const data = storage.data?.get(player.index) ?? {};

  // 0 or 1 items in queue
  // assert data.active_recipe_name === undefined

  // pick recipe
  const recipe_name = pick_recipe(player, crafting_complete);

  if (recipe_name !== undefined) {
    data.active_recipe_name = recipe_name;
    storage.data?.set(player.index, data);
    player.begin_crafting({ count: 1, recipe: recipe_name, silent: true });
  }
};
