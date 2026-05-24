import("gui.Component")
import("model.Item")

---@class DimOverlay : Component
---@field private _qualityCounts table<string,number>
DimOverlay = Component:extendAs("gui.toolbar.content.sections.section.content.table.slots.item.DimOverlay")

---@param parent Component
---@return DimOverlay
function DimOverlay.create(parent)
    return Component.create(
            DimOverlay,
            parent,
            {
                type = "sprite-button",
                style = "toolbar_content_sections_section_content_table_row_slot_item_overlay_dim",
                ignored_by_interaction = true,
            }
    )
end

function DimOverlay.new(parent, root)
    return DimOverlay:super(Component.new(parent, root))
end

---@public
function DimOverlay:refresh()
    self:migrateTo_2_29_0()

    if next(self:player():viewInventory():content():allQualitiesCount(self:slot():item():name())) then
        self:presentSome()
    else
        self:presentNone()
    end
end

---@private
function DimOverlay:migrateTo_2_29_0()
    self:show()
end

---@private
function DimOverlay:presentSome()
    self:element().style = "toolbar_content_sections_section_content_table_row_slot_item_overlay_dim_some"
end

---@private
function DimOverlay:presentNone()
    self:element().style = "toolbar_content_sections_section_content_table_row_slot_item_overlay_dim_none"
end

---@private
---@return ItemSlot
function DimOverlay:slot()
    return self:parent()
end
