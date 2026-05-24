for _, quality in pairs(data.raw["quality"]) do
    if quality.icon then
        data:extend {
            {
                type = "sprite",
                name = "expend-toolbar_quality_" .. quality.name,
                filename = quality.icon,
                priority = "extra-high-no-scale",
                size = 64,
                scale = 0.25,
                flags = { "gui-icon" }
            },
        }
    elseif quality.icons then
        local layers = {}
        for _, icon in ipairs(quality.icons) do
            table.insert(layers, {
                filename = icon.icon,
                tint = icon.tint,
                size = 64,
                scale = 0.25,
                priority = "extra-high-no-scale",
                flags = { "gui-icon" }
            })
        end

        data:extend {
            {
                type = "sprite",
                name = "expend-toolbar_quality_" .. quality.name,
                layers = layers
            },
        }
    end
end

for _, planet in pairs(data.raw["planet"]) do
    if planet.icon then
        data:extend {
            {
                type = "sprite",
                name = "expend-toolbar_planet_" .. planet.name,
                filename = planet.icon,
                priority = "extra-high-no-scale",
                size = 64,
                scale = 0.25,
                flags = { "gui-icon" }
            },
        }
    elseif planet.icons then
        local layers = {}
        for _, icon in ipairs(planet.icons) do
            table.insert(layers, {
                filename = icon.icon,
                tint = icon.tint,
                size = 64,
                scale = 0.25,
                priority = "extra-high-no-scale",
                flags = { "gui-icon" }
            })
        end

        data:extend {
            {
                type = "sprite",
                name = "expend-toolbar_planet_" .. planet.name,
                layers = layers
            },
        }
    end
end
