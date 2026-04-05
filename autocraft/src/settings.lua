local constants = require("constants")

data:extend({
  {
    type = "bool-setting",
    name = constants.AUTOCRAFT_SOUND_ENABLED,
    setting_type = "runtime-per-user",
    default_value = false,
  },
  {
    type = "bool-setting",
    name = constants.AUTOCRAFT_EXISTING_SECTIONS_ENABLED,
    setting_type = "runtime-per-user",
    default_value = false,
  },
})
