local crafting_finished = data.raw["utility-sounds"]["default"] and data.raw["utility-sounds"]["default"].crafting_finished

if crafting_finished then
  if crafting_finished[1] then
    crafting_finished[1].volume = 0
  else
    crafting_finished.volume = 0
  end
end
