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
})
