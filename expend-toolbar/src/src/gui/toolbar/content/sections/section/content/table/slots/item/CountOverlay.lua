import("gui.Component")

---@class CountOverlay : Component
CountOverlay = Component:extendAs("gui.toolbar.content.sections.section.content.table.slots.item.CountOverlay")

---@param parent Component
---@return CountOverlay
function CountOverlay.create(parent)
    return Component.create(
            CountOverlay,
            parent,
            {
                type = "sprite-button",
                style = "toolbar_content_sections_section_content_table_row_slot_item_overlay_count",
                ignored_by_interaction = true,
            }
    )
end

function CountOverlay.new(parent, root)
    return CountOverlay:super(Component.new(parent, root))
end

---@public
function CountOverlay:refresh()
    self:setCount(self:player():viewInventory():content():count(self:slot():item()))
end

---@private
---@param count number
function CountOverlay:setCount(count)
    if count > 0 then
        self:element().number = count
    else
        self:element().number = nil
    end

    --migrate to 2.23.0
    self:element().style = "toolbar_content_sections_section_content_table_row_slot_item_overlay_count"
end

---@private
---@return ItemSlot
function CountOverlay:slot()
    return self:parent()
end
