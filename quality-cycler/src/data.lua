local prefix = "quality-cycler-"

data:extend({
    {
        type = "custom-input",
        name = prefix .. "cycle-quality-up",
        key_sequence = "",
        linked_game_control = "cycle-quality-up",
        include_selected_prototype = true,
    },
    {
        type = "custom-input",
        name = prefix .. "cycle-quality-down",
        key_sequence = "",
        linked_game_control = "cycle-quality-down",
        include_selected_prototype = true,
    },
})
