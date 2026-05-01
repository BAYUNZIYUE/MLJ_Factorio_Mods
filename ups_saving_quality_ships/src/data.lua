data:extend {
    {
        type = "custom-input",
        name = "change-hub-quality",
        key_sequence = "CONTROL + ALT + S",
        order = "u[ups]-s[saving]-q[quality]-s[spaceships]-1",
        action = "lua",
    },
    {
        type = "shortcut",
        name = "change-hub-quality",
        localised_name = { "controls.change-hub-quality" },
        localised_description = { "controls-description.change-hub-quality" },
        associated_control_input = "change-hub-quality",
        action = "lua",
        toggleable = false,
        icons = {
            {
                icon = "__ups_saving_quality_ships__/graphics/icon-upgrade-hub-64.png",
                icon_size = 64,
            }
        },
        small_icons = {
            {
                icon = "__ups_saving_quality_ships__/graphics/icon-upgrade-hub-64.png",
                icon_size = 64,
            }
        },
        style = "default",
        order = "u[ups]-s[saving]-q[quality]-s[spaceships]-1",
    },
}
