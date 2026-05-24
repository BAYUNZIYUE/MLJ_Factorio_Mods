import("Item")
import("gui.Component")

---@class ItemButton : Component
---@field private _item Item
ItemButton = Component:extendAs("gui.toolbar.content.sections.section.content.table.slots.item.ItemButton")

---@param parent Component
---@param item Item
---@param mouse_button_filter string[]
---@return ItemButton
function ItemButton.create(parent, item, mouse_button_filter)
    return Component.create(
            ItemButton,
            parent,
            {
                type = "sprite-button",
                sprite = "item/" .. item:name(),
                style = "toolbar_content_sections_section_content_table_row_slot_button_item",
                mouse_button_filter = mouse_button_filter,
            }
    )
end

function ItemButton.new(parent, root)
    return ItemButton:super(Component.new(parent, root))
end

function ItemButton:initilize()
    self:migrateTo_2_0_9()
    self:migrateTo_2_32_0()
end

---@private
function ItemButton:migrateTo_2_0_9()
    if self:element().tags.quality then
        local tags = self:element().tags
        self:element().elem_tooltip = { type = "item-with-quality", name = self:element().elem_tooltip.name, quality = tags.quality }
        tags.quality = nil
        self:element().tags = tags
    end
end

function ItemButton:migrateTo_2_32_0()
    self:element().elem_tooltip = nil
    self:element().tooltip = nil
end

---@public
---@return boolean
function ItemButton:hasTooltips()
    return self:element().elem_tooltip ~= nil
end

---@public
---@param tooltip LocalisedString
function ItemButton:showTooltips(tooltip)
    self:showElemTooltip()
    self:element().tooltip = tooltip
end

---@private
function ItemButton:showElemTooltip()
    self:element().elem_tooltip = { type = "item-with-quality", name = self:slot():item():name(), quality = self:slot():item():quality() }
end

---@public
function ItemButton:hideTooltips()
    self:element().elem_tooltip = nil
    self:element().tooltip = nil
end

---@public
function ItemButton:highlight()
    self:element().style = "toolbar_content_sections_section_content_table_row_slot_button_item_selected"
end

---@public
function ItemButton:unhighlight()
    self:element().style = "toolbar_content_sections_section_content_table_row_slot_button_item"
end

---@private
---@return ItemSlot
function ItemButton:slot()
    return self:parent()
end
