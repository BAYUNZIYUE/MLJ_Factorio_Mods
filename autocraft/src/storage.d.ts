type PlayerData = {
  active_recipe_name?: string;
};

type Storage = {
  data?: LuaMap<PlayerIndex, PlayerData>;
  recipes?: LuaMap<string, LuaSet<string>>;
};

declare const storage: Storage;
