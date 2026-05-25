local names = require("names")

data:extend({
  {
    order = "a1",
    name = names.setting.wide,
    setting_type = "runtime-per-user",
    type = "int-setting",
    default_value = 10,
    minimum_value = 1,
    maximum_value = 100,
  },
  {
    order = "a2",
    name = names.setting.hint_keys,
    setting_type = "runtime-per-user",
    type = "bool-setting",
    default_value = true,
  },
  {
    order = "b1",
    name = names.setting.vehicle_on,
    setting_type = "runtime-per-user",
    type = "bool-setting",
    default_value = true,
  },
  {
    order = "c1",
    name = names.setting.network_on,
    setting_type = "runtime-per-user",
    type = "bool-setting",
    default_value = true,
  },
})
