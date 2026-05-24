import("gui.Component")

---@class SpidertronRemotePlanetSprite : Component
SpidertronRemotePlanetSprite = Component:extendAs("gui.toolbar.content.sections.section.content.table.slots.spidertron_remote.SpidertronRemotePlanetSprite")

---@public
---@param parent Component
---@param planet LuaPlanet
---@return SpidertronRemotePlanetSprite
function SpidertronRemotePlanetSprite.create(parent, planet)
    return Component.create(
            SpidertronRemotePlanetSprite,
            parent,
            {
                type = "sprite",
                style = "toolbar_content_sections_section_content_table_row_slot_spidertron_remote_overlay_planet_sprite",
                ignored_by_interaction = true,
                sprite = planet and Toolbars.prefix("planet_" .. planet.name) or nil
            }
    )
end

function SpidertronRemotePlanetSprite.new(parent, root)
    return SpidertronRemotePlanetSprite:super(Component.new(parent, root))
end
