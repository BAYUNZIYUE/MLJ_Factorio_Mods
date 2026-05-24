import("gui.Component")
import("model.Item")

---@class SpidertronRemoteDimOverlay : Component
---@field private _qualityCounts table<string,number>
SpidertronRemoteDimOverlay = Component:extendAs("gui.toolbar.content.sections.section.content.table.slots.spidertron_remote.SpidertronRemoteDimOverlay")

---@param parent Component
---@return SpidertronRemoteDimOverlay
function SpidertronRemoteDimOverlay.create(parent)
    return Component.create(
            SpidertronRemoteDimOverlay,
            parent,
            {
                type = "sprite-button",
                style = "toolbar_content_sections_section_content_table_row_slot_spidertron_remote_overlay_dim_same_surface",
                ignored_by_interaction = true,
            }
    )
end

function SpidertronRemoteDimOverlay.new(parent, root)
    return SpidertronRemoteDimOverlay:super(Component.new(parent, root))
end

---@public
function SpidertronRemoteDimOverlay:refresh()
    local spidertronRemoteSurface = self:slot():spidertronRemote():surface()
    if spidertronRemoteSurface == nil or self:player():surface() == spidertronRemoteSurface then
        self:presentSameSurface()
    else
        self:presentOtherSurface()
    end
end

---@private
function SpidertronRemoteDimOverlay:presentSameSurface()
    self:element().style = "toolbar_content_sections_section_content_table_row_slot_spidertron_remote_overlay_dim_same_surface"
end

---@private
function SpidertronRemoteDimOverlay:presentOtherSurface()
    self:element().style = "toolbar_content_sections_section_content_table_row_slot_spidertron_remote_overlay_dim_other_surface"
end

---@private
---@return SpidertronRemoteSlot
function SpidertronRemoteDimOverlay:slot()
    return self:parent()
end
