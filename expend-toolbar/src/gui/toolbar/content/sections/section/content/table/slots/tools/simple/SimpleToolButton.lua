import("gui.Component")
import("model.SimpleTool")

---@class SimpleToolButton : Component
---@field private _tool SimpleTool
SimpleToolButton = Component:extendAs("gui.toolbar.content.sections.section.content.table.slots.tool.SimpleToolButton")

---@param parent Component
---@param simpleTool SimpleTool
---@param mouse_button_filter string[]
function SimpleToolButton.create(parent, simpleTool, mouse_button_filter)
    return Component.create(
            SimpleToolButton,
            parent,
            {
                type = "sprite-button",
                elem_tooltip = { type = "item", name = simpleTool:name() },
                sprite = "item/" .. assert(simpleTool:name()),
                style = "toolbar_content_sections_section_content_table_row_slot_button",
                number = nil,
                mouse_button_filter = mouse_button_filter,
            }
    )
end

function SimpleToolButton.new(parent, root)
    return SimpleToolButton:super(Component.new(parent, root))
end

function SimpleToolButton:initilize()
    self._tool = SimpleTool.new(self:element().elem_tooltip.name)
end

---@public
---@return SimpleTool
function SimpleToolButton:tool()
    return self._tool
end

---@public
function SimpleToolButton:highlight()
    self:element().style = "toolbar_content_sections_section_content_table_row_slot_button_selected"
end

---@public
function SimpleToolButton:unhighlight()
    self:element().style = "toolbar_content_sections_section_content_table_row_slot_button_item"
end
