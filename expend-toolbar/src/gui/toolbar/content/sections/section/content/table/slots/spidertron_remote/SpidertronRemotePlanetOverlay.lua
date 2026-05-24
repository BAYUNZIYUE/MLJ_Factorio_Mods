import("gui.Component")
import("gui.toolbar.content.sections.section.content.table.slots.spidertron_remote.SpidertronRemotePlanetSprite")

---@class SpidertronRemotePlanetOverlay : Component
SpidertronRemotePlanetOverlay = Component:extendAs("gui.toolbar.content.sections.section.content.table.slots.spidertron_remote.SpidertronRemotePlanetOverlay")

---@public
---@param parent Component
---@param planet LuaPlanet
---@return SpidertronRemotePlanetOverlay
function SpidertronRemotePlanetOverlay.create(parent, planet)
    return Component.create(
            SpidertronRemotePlanetOverlay,
            parent,
            {
                type = "flow",
                style = "toolbar_content_sections_section_content_table_row_slot_spidertron_remote_overlay_planet",
                ignored_by_interaction = true
            },
            function(instance)
                SpidertronRemotePlanetSprite.create(instance, planet)
            end
    )
end

function SpidertronRemotePlanetOverlay.new(parent, root)
    return SpidertronRemotePlanetOverlay:super(Component.new(parent, root, { SpidertronRemotePlanetSprite }))
end

---@public
function SpidertronRemotePlanetOverlay:refresh()
    local spidertronRemotePlanet = self:slot():spidertronRemote():planet()
    if spidertronRemotePlanet == nil or self:player():planet() == spidertronRemotePlanet then
        self:hide()
    else
        self:show()
    end
end

---@private
---@return SpidertronRemotePlanetSprite
function SpidertronRemotePlanetOverlay:sprite()
    return self:child(SpidertronRemotePlanetSprite)
end

---@private
---@return SpidertronRemoteSlot
function SpidertronRemotePlanetOverlay:slot()
    return self:parent()
end
