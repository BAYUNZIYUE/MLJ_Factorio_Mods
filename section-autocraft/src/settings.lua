local constants = require("constants")

data:extend({
  {
    type = "string-setting",
    name = constants.AUTOCRAFT_PREFIX_SETTING,
    setting_type = "runtime-per-user",
    default_value = constants.AUTOCRAFT_DEFAULT_PREFIX_RICH_TEXT,
    allow_blank = true,
  },
  {
    type = "string-setting",
    name = constants.AUTOCRAFT_MATCH_MODE_SETTING,
    setting_type = "runtime-per-user",
    default_value = constants.AUTOCRAFT_MATCH_MODE_PREFIX_AND_PLAYER_NAME,
    allowed_values = {
      constants.AUTOCRAFT_MATCH_MODE_FULL,
      constants.AUTOCRAFT_MATCH_MODE_PREFIX,
      constants.AUTOCRAFT_MATCH_MODE_PLAYER_NAME,
      constants.AUTOCRAFT_MATCH_MODE_PREFIX_AND_PLAYER_NAME,
    },
  },
  {
    type = "bool-setting",
    name = constants.AUTOCRAFT_SOUND_ENABLED,
    setting_type = "runtime-per-user",
    default_value = false,
  },
  {
    type = "double-setting",
    name = constants.AUTOCRAFT_CRAFTING_SPEED_MULTIPLIER_SETTING,
    setting_type = "runtime-global",
    default_value = 1,
    minimum_value = 1,
    maximum_value = 10000,
  },
})
