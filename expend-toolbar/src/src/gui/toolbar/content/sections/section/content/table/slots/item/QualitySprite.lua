import("gui.Component")

-- migration to 2.21.0 (reused class name of QualityOverlay)
---@class QualitySprite : Component
QualitySprite = Component:extendAs("gui.toolbar.content.sections.section.content.table.slots.item.QualityOverlay")

---@public
---@param parent Component
---@return QualitySprite
function QualitySprite.create(parent)
    return Component.create(
            QualitySprite,
            parent,
            {
                type = "sprite",
                style = "toolbar_content_sections_section_content_table_row_slot_item_overlay_quality_sprite",
                ignored_by_interaction = true
            }
    )
end

function QualitySprite.new(parent, root)
    return QualitySprite:super(Component.new(parent, root))
end

---@public
---@param qualityName string
function QualitySprite:setQuality(qualityName)
    local quality = prototypes.quality[qualityName]
    if quality and quality.draw_sprite_by_default then
        self:element().sprite = Toolbars.prefix("quality_" .. qualityName)
    else
        self:element().sprite = nil
    end
end
