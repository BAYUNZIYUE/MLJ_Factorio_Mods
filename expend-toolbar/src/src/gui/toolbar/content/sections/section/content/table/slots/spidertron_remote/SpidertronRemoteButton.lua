import("gui.Component")

---@class SpidertronRemoteButton : Component
SpidertronRemoteButton = Component:extendAs("gui.toolbar.content.sections.section.content.table.slots.spidertron_remote.SpidertronRemoteButton")

---@param parent Component
---@param mouse_button_filter string[]
function SpidertronRemoteButton.create(parent, mouse_button_filter)
    return Component.create(
            SpidertronRemoteButton,
            parent,
            {
                type = "sprite-button",
                elem_tooltip = { type = "item", name = "spidertron-remote" },
                sprite = "item/spidertron-remote",
                style = "toolbar_content_sections_section_content_table_row_slot_spidertron_remote_button",
                mouse_button_filter = mouse_button_filter,
            }
    )
end

function SpidertronRemoteButton.new(parent, root)
    return SpidertronRemoteButton:super(Component.new(parent, root))
end

---@public
function SpidertronRemoteButton:highlight()
    self:element().style = "toolbar_content_sections_section_content_table_row_slot_spidertron_remote_button_selected"
end

---@public
function SpidertronRemoteButton:unhighlight()
    self:element().style = "toolbar_content_sections_section_content_table_row_slot_spidertron_remote_button"
end
