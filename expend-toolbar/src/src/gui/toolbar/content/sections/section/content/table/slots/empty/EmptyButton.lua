import("gui.Component")

---@class EmptyButton : Component
EmptyButton = Component:extendAs("gui.toolbar.content.sections.section.content.table.slots.empty.EmptyButton")

function EmptyButton.create(parent, mouse_button_filter)
    return Component.create(
            EmptyButton,
            parent,
            {
                type = "choose-elem-button",
                elem_type = "item-with-quality",
                style = "toolbar_content_sections_section_content_table_row_slot_button",
                mouse_button_filter = mouse_button_filter
            }
    )
end

function EmptyButton.new(parent, root)
    return EmptyButton:super(Component.new(parent, root))
end

---@public
---@return Item
function EmptyButton:item()
    local value = self:element().elem_value
    if value then
        return Item.new(value.name, value.quality)
    else
        return nil
    end
end

---@public
function EmptyButton:clear()
    self:element().elem_value = nil
end
