import("gui.Component")

---@class SpidertronRemoteCountOverlay : Component
SpidertronRemoteCountOverlay = Component:extendAs("gui.toolbar.content.sections.section.content.table.slots.spidertron_remote.SpidertronRemoteCountOverlay")

---@public
---@param parent Component
---@param unitsCount number
---@return SpidertronRemoteCountOverlay
function SpidertronRemoteCountOverlay.create(parent, unitsCount)
    return Component.create(
            SpidertronRemoteCountOverlay,
            parent,
            {
                type = "sprite-button",
                style = "toolbar_content_sections_section_content_table_row_slot_spidertron_remote_overlay_count",
                ignored_by_interaction = true,
                number = unitsCount > 0 and unitsCount or nil
            }
    )
end

function SpidertronRemoteCountOverlay.new(parent, root)
    return SpidertronRemoteCountOverlay:super(Component.new(parent, root))
end

---@public
function SpidertronRemoteCountOverlay:refresh()
    self:setCount(self:slot():spidertronRemote():unitsCount())
end

---@private
---@param count number
function SpidertronRemoteCountOverlay:setCount(count)
    if count > 0 then
        self:element().number = count
    else
        self:element().number = nil
    end
end

---@private
---@return SpidertronRemoteSlot
function SpidertronRemoteCountOverlay:slot()
    return self:parent()
end
