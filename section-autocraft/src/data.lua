local constants = require("constants")

local sound = data.raw["utility-sounds"]["default"] and data.raw["utility-sounds"]["default"].crafting_finished
local crafting_finished = nil

if sound then
  if sound[1] then
    crafting_finished = sound[1]
  else
    crafting_finished = sound
  end
end

data:extend({
  {
    type = "sound",
    name = constants.CRAFTING_FINISHED_SOUND,
    filename = crafting_finished and crafting_finished.filename or "__core__/sound/crafting-finished.ogg",
    volume = crafting_finished and crafting_finished.volume or 0.75,
  },
  {
    type = "virtual-signal",
    name = constants.AUTOCRAFT_WRENCH_SIGNAL_NAME,
    icon = "__section-autocraft__/graphics/icon/wrench-signal-64.png",
    icon_size = 64,
    icon_mipmaps = 1,
    subgroup = "virtual-signal-special",
    order = "a[autocraft]-a[wrench]",
  },
  {
    type = "shortcut",
    name = constants.AUTOCRAFT_SHORTCUT_NAME,
    action = "lua",
    toggleable = true,
    icon = "__section-autocraft__/graphics/icon/wrench-shortcut-32.png",
    icon_size = 32,
    small_icon = "__section-autocraft__/graphics/icon/wrench-shortcut-24.png",
    small_icon_size = 24,
  },
})
