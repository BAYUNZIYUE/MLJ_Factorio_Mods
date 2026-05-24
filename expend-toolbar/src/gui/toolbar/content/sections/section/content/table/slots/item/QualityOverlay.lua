import("gui.Component")
import("gui.toolbar.content.sections.section.content.table.slots.item.QualitySprite")

---@class QualityOverlay : Component
QualityOverlay = Component:extendAs("gui.toolbar.content.sections.section.content.table.slots.item.QualityOverlay")

---@public
---@param parent Component
---@return QualityOverlay
function QualityOverlay.create(parent)
    return Component.create(
            QualityOverlay,
            parent,
            {
                type = "flow",
                style = "toolbar_content_sections_section_content_table_row_slot_item_overlay_quality",
                ignored_by_interaction = true
            },
            function(instance)
                QualitySprite.create(instance)
            end
    )
end

function QualityOverlay.new(parent, root)
    return QualityOverlay:super(Component.new(parent, root, { QualitySprite }))
end

function QualityOverlay:initilize()
    self:migrateTo_2_22_0()
end

---@private
function QualityOverlay:migrateTo_2_22_0()
    if not self:sprite() then
        QualitySprite.create(self)
    end
end

---@public
function QualityOverlay:refresh()
    self:sprite():setQuality(self:slot():item():quality())
end

---@private
---@return QualitySprite
function QualityOverlay:sprite()
    return self:child(QualitySprite)
end

---@private
---@return ItemSlot
function QualityOverlay:slot()
    return self:parent()
end
