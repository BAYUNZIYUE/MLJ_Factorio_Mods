require("core.Toolbars")

data:extend {
    {
        order = "a1",
        type = "custom-input",
        name = Toolbars.controls.createToolbar,
        localised_name = "Create a toolbar",
        key_sequence = "",
    },
    {
        order = "a2",
        type = "custom-input",
        name = Toolbars.controls.toggleToolbars,
        localised_name = "Toggle toolbars",
        localised_description = "Hide/Show all toolbars",
        key_sequence = "",
    },
    {
        order = "a3",
        type = "custom-input",
        name = Toolbars.controls.toggleToolbarHeader,
        localised_name = "Toggle toolbar header",
        localised_description = "Hide/Show the header of a toolbar under the cursor",
        key_sequence = "",
    }
}

data:extend {
    {
        type = "custom-input",
        name = Toolbars.controls.pipette,
        linked_game_control = "pipette",
        key_sequence = "",
    },
    {
        type = "custom-input",
        name = Toolbars.controls.openFactoriopedia,
        linked_game_control = "open-factoriopedia",
        key_sequence = "",
    },
    {
        type = "custom-input",
        name = Toolbars.controls.toggleFilter,
        linked_game_control = "toggle-filter",
        key_sequence = "",
    },
    {
        type = "custom-input",
        name = Toolbars.controls.increaseQuality,
        linked_game_control = "cycle-quality-up",
        key_sequence = "",
    },
    {
        type = "custom-input",
        name = Toolbars.controls.decreaseQuality,
        linked_game_control = "cycle-quality-down",
        key_sequence = "",
    },
}
