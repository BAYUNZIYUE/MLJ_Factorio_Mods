import type { ItemID, ItemProduct, LuaLogisticSection, LuaPlayer } from "factorio:runtime";
import {
  AUTOCRAFT_EXISTING_SECTIONS_ENABLED,
  AUTOCRAFT_LOGISTICS_SECTION_PREFIX,
} from "./constants";

type ItemRequest = {
  name: string;
  min: number;
  available: number;
  missing: number;
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

const get_autocraft_logistics_section_name = (player: LuaPlayer) =>
  `${AUTOCRAFT_LOGISTICS_SECTION_PREFIX}-${player.name}`;

const is_named_autocraft_section = (section: LuaLogisticSection) =>
  section.is_manual &&
  (section.group === AUTOCRAFT_LOGISTICS_SECTION_PREFIX ||
    section.group.substring(0, AUTOCRAFT_LOGISTICS_SECTION_PREFIX.length + 1) ===
      `${AUTOCRAFT_LOGISTICS_SECTION_PREFIX}-`);

const is_players_autocraft_section = (player: LuaPlayer, section: LuaLogisticSection) =>
  section.is_manual && section.group === get_autocraft_logistics_section_name(player);

const find_autocraft_logistics_section = (player: LuaPlayer) => {
  const logistic_point = player.get_requester_point();
  if (!logistic_point) return undefined;

  for (const section of logistic_point.sections) {
    if (is_players_autocraft_section(player, section)) {
      return section;
    }
  }

  return undefined;
};

export const add_autocraft_logistics_section = (player: LuaPlayer) => {
  const logistic_point = player.get_requester_point();
  if (!logistic_point) return undefined;

  const target_group = get_autocraft_logistics_section_name(player);
  const existing_section = find_autocraft_logistics_section(player);
  if (existing_section) return existing_section;

  const section = logistic_point.add_section(target_group);
  if (section) {
    section.active = false;
  }
};

const should_include_existing_sections = (player: LuaPlayer) =>
  player.mod_settings[AUTOCRAFT_EXISTING_SECTIONS_ENABLED].value as boolean;

const should_include_section = (player: LuaPlayer, section: LuaLogisticSection) => {
  if (!section.active) return false;
  if (is_players_autocraft_section(player, section)) return true;
  return should_include_existing_sections(player) && !is_named_autocraft_section(section);
};

const get_requested_items = (player: LuaPlayer) => {
  const requested_items = new LuaMap<string, number>();
  const logistic_point = player.get_requester_point();
  if (!logistic_point) return requested_items;

  // 先筛出本次应参与自动手搓的物流分组，再把同类物品的最小保有量汇总成一个总需求。
  for (const section of logistic_point.sections) {
    if (!should_include_section(player, section)) continue;

    for (const filter of section.filters) {
      if (filter.min === undefined || filter.min === 0) continue;

      let item_name: string | undefined;
      if (typeof filter.value === "string") {
        item_name = filter.value;
      } else if (filter.value?.type === "item") {
        item_name = filter.value.name;
      }

      if (item_name === undefined) continue;

      requested_items.set(item_name, (requested_items.get(item_name) ?? 0) + filter.min);
    }
  }

  return requested_items;
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

const get_crafting_queue_item_count = (player: LuaPlayer, item_name: string) => {
  const crafting_queue = player.crafting_queue;
  if (!crafting_queue) return 0;

  let queued_count = 0;
  for (const [, queue_item] of pairs(crafting_queue)) {
    if (queue_item.prerequisite) continue;

    const recipe_name =
      typeof queue_item.recipe === "string" ? queue_item.recipe : queue_item.recipe.name;
    const recipe = player.force.recipes[recipe_name];
    if (!recipe) continue;

    for (const product of recipe.products as ItemProduct[]) {
      if (product.type !== "item" || product.name !== item_name) continue;

      queued_count += queue_item.count * (product.amount ?? 1);
      break;
    }
  }

  return queued_count;
};

const get_item_requests = (
  player: LuaPlayer,
  crafting_complete: boolean,
  completed_item_name?: string,
) => {
  const item_requests: ItemRequest[] = [];
  const requested_items = get_requested_items(player);
  const logistic_network = player.get_requester_point()?.logistic_network;

  // 实际手搓缺口要同时扣掉玩家已持有、当前物流网络已有，以及已经排进手搓队列的成品数量。
  for (const [item_name, min] of pairs(requested_items)) {
    const recently_completed_count =
      !crafting_complete && completed_item_name === item_name ? 1 : 0;
    const inventory_count = player.get_item_count(item_name) + recently_completed_count;
    const logistic_network_count = logistic_network?.get_item_count(item_name) ?? 0;
    const queued_count = get_crafting_queue_item_count(player, item_name);
    const available = inventory_count + logistic_network_count + queued_count;
    const missing = min - available;
    if (missing <= 0) continue;

    item_requests.push({
      name: item_name,
      min,
      available,
      missing,
      ratio: available / min,
    });
  }

  return item_requests;
};

const item_id_to_name = (item: ItemID) => {
  if (typeof item === "string") {
    return item;
  } else {
    return item.name;
  }
};

const pick_recipe = (
  player: LuaPlayer,
  crafting_complete: boolean,
  completed_item_name?: string,
): { item_name: string; recipe_name: string } | undefined => {
  const item_requests = get_item_requests(player, crafting_complete, completed_item_name);
  if (item_requests.length === 0) return undefined;

  item_requests.sort((a, b) => {
    if (a.ratio < b.ratio) return -1;
    if (a.ratio === b.ratio) {
      if (a.missing > b.missing) return -1;
      if (a.missing === b.missing) return 0;
    }
    return 1;
  });

  const hand_item_name = player.cursor_stack?.valid_for_read
    ? player.cursor_stack.name
    : player.cursor_ghost
      ? item_id_to_name(player.cursor_ghost.name)
      : undefined;

  if (hand_item_name !== undefined && item_requests.some((item) => item.name === hand_item_name)) {
    const recipe = recipe_for_item(player, hand_item_name);
    if (recipe !== undefined) {
      return { item_name: hand_item_name, recipe_name: recipe };
    }
  }

  for (const item_request of item_requests) {
    const recipe = recipe_for_item(player, item_request.name);
    if (recipe !== undefined) {
      return { item_name: item_request.name, recipe_name: recipe };
    }
  }

  return undefined;
};

export const do_crafting = (
  player: LuaPlayer,
  crafting_complete = true,
  completed_item_name?: string,
) => {
  const is_eligible =
    player.connected &&
    player.controller_type === defines.controllers.character &&
    player.ticks_to_respawn === undefined;

  if (!is_eligible) return;

  const allowed_queue_length = crafting_complete ? 0 : 1;

  if (player.crafting_queue && player.crafting_queue.length > allowed_queue_length) {
    return;
  }

  const data = storage.data?.get(player.index) ?? {};

  // 0 or 1 items in queue
  // assert data.active_recipe_name === undefined

  // pick recipe
  const selection = pick_recipe(player, crafting_complete, completed_item_name);

  if (selection !== undefined) {
    data.active_item_name = selection.item_name;
    data.active_recipe_name = selection.recipe_name;
    storage.data?.set(player.index, data);
    player.begin_crafting({ count: 1, recipe: selection.recipe_name, silent: true });
  }
};
