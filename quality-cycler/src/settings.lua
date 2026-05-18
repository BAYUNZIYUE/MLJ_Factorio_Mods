local prefix = "quality-cycler-"

data:extend({
    {
        type = "string-setting",
        name = prefix .. "ignore-list",
        setting_type = "runtime-per-user",
        default_value = "",
        allow_blank = true,
        order = "a",
    },
})
