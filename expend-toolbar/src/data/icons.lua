data:extend {
    {
        type = "sprite",
        name = Toolbars.icons.one,
        filename = "__expend-toolbar__/_graphics/icons/1.png",
        priority = "extra-high-no-scale",
        size = 16,
        scale = 1,
        flags = { "gui-icon" }
    },

    {
        type = "sprite",
        name = Toolbars.icons.alignToolbarTop,
        filename = "__expend-toolbar__/_graphics/icons/align-start.png",
        priority = "extra-high-no-scale",
        size = 16,
        scale = 1,
        flags = { "gui-icon" }
    },
    {
        type = "sprite",
        name = Toolbars.icons.alignToolbarBottom,
        filename = "__expend-toolbar__/_graphics/icons/align-end.png",
        priority = "extra-high-no-scale",
        size = 16,
        scale = 1,
        flags = { "gui-icon" }
    },

    {
        type = "sprite",
        name = Toolbars.icons.cancel,
        filename = "__expend-toolbar__/_graphics/icons/cancel.png",
        priority = "extra-high-no-scale",
        size = 16,
        scale = 1,
        flags = { "gui-icon" }
    },

    {
        type = "sprite",
        name = Toolbars.icons.collapseUpward,
        filename = "__expend-toolbar__/_graphics/icons/collapse-upward.png",
        priority = "extra-high-no-scale",
        size = 16,
        scale = 1,
        flags = { "gui-icon" }
    },
    {
        type = "sprite",
        name = Toolbars.icons.collapseDownward,
        filename = "__expend-toolbar__/_graphics/icons/collapse-downward.png",
        priority = "extra-high-no-scale",
        size = 16,
        scale = 1,
        flags = { "gui-icon" }
    },

    {
        type = "sprite",
        name = Toolbars.icons.confirm,
        filename = "__expend-toolbar__/_graphics/icons/confirm.png",
        priority = "extra-high-no-scale",
        size = 16,
        scale = 1,
        flags = { "gui-icon" }
    },
    {
        type = "sprite",
        name = Toolbars.icons.expand,
        filename = "__expend-toolbar__/_graphics/icons/expand.png",
        priority = "extra-high-no-scale",
        size = 16,
        scale = 1,
        flags = { "gui-icon" }
    },

    {
        type = "sprite",
        name = Toolbars.icons.moveSectionDown,
        filename = "__expend-toolbar__/_graphics/icons/move-down.png",
        priority = "extra-high-no-scale",
        size = 16,
        scale = 1,
        flags = { "gui-icon" }
    },
    {
        type = "sprite",
        name = Toolbars.icons.moveSectionUp,
        filename = "__expend-toolbar__/_graphics/icons/move-up.png",
        priority = "extra-high-no-scale",
        size = 16,
        scale = 1,
        flags = { "gui-icon" }
    },

    {
        type = "sprite",
        name = Toolbars.icons.padlockClosed,
        filename = "__expend-toolbar__/_graphics/icons/padlock-closed-white.png",
        priority = "extra-high-no-scale",
        size = 16,
        scale = 1,
        flags = { "gui-icon" }
    },
    {
        type = "sprite",
        name = Toolbars.icons.padlockOpen,
        filename = "__expend-toolbar__/_graphics/icons/padlock-open-white.png",
        priority = "extra-high-no-scale",
        size = 16,
        scale = 1,
        flags = { "gui-icon" }
    },

    {
        type = "sprite",
        name = Toolbars.icons.empty,
        filename = "__expend-toolbar__/_graphics/icons/empty.png",
        priority = "extra-high-no-scale",
        size = 64,
        flags = { "icon" }
    },

    {
        type = "sprite",
        name = Toolbars.icons.characterTrash,
        layers = {
            {
                filename = "__core__/graphics/icons/entity/character.png",
                priority = "extra-high-no-scale",
                size = 64,
            },
            {
                filename = "__expend-toolbar__/_graphics/icons/trash.png",
                priority = "extra-high-no-scale",
                scale = 0.85,
                shift = { 16 * 1 / 0.85, 16 * 1 / 0.85 },
                size = 32,
            },
        },
        flags = { "icon" }
    },
    {
        type = "sprite",
        name = Toolbars.icons.carTrash,
        layers = {
            {
                filename = "__base__/graphics/icons/car.png",
                priority = "extra-high-no-scale",
                size = 64,
            },
            {
                filename = "__expend-toolbar__/_graphics/icons/trash.png",
                priority = "extra-high-no-scale",
                scale = 0.85,
                shift = { 16 * 1 / 0.85, 16 * 1 / 0.85 },
                size = 32,
            },
        },
        flags = { "icon" }
    },
    {
        type = "sprite",
        name = Toolbars.icons.tankTrash,
        layers = {
            {
                filename = "__base__/graphics/icons/tank.png",
                priority = "extra-high-no-scale",
                size = 64,
            },
            {
                filename = "__expend-toolbar__/_graphics/icons/trash.png",
                priority = "extra-high-no-scale",
                scale = 0.85,
                shift = { 16 * 1 / 0.85, 16 * 1 / 0.85 },
                size = 32,
            },
        },
        flags = { "icon" }
    },
    {
        type = "sprite",
        name = Toolbars.icons.spidertronTrash,
        layers = {
            {
                filename = "__base__/graphics/icons/spidertron.png",
                priority = "extra-high-no-scale",
                size = 64,
            },
            {
                filename = "__expend-toolbar__/_graphics/icons/trash.png",
                priority = "extra-high-no-scale",
                scale = 0.85,
                shift = { 16 * 1 / 0.85, 16 * 1 / 0.85 },
                size = 32,
            },
        },
        flags = { "icon" }
    },
}

if data.raw["item"]["space-platform-foundation"] then
    data:extend {
        {
            type = "sprite",
            name = Toolbars.icons.spacePlatformHubTrash,
            layers = {
                {
                    filename = "__space-age__/graphics/icons/space-platform-foundation.png",
                    priority = "extra-high-no-scale",
                    size = 64,
                },
                {
                    filename = "__expend-toolbar__/_graphics/icons/trash.png",
                    priority = "extra-high-no-scale",
                    scale = 0.85,
                    shift = { 16 * 1 / 0.85, 16 * 1 / 0.85 },
                    size = 32,
                },
            },
            flags = { "icon" }
        },
    }
end
