import("gui.toolbar.content.sections.section.header.CollapseSection")
import("gui.toolbar.content.sections.section.header.SectionHeaderButton")

---@class ExpandSection : SectionHeaderButton
ExpandSection = SectionHeaderButton:extendAs("gui.toolbar.content.sections.section.header.Expand")

function ExpandSection.create(parent)
    return SectionHeaderButton.create(
            ExpandSection,
            parent,
            {
                type = "sprite-button",
                sprite = Toolbars.icons.expand,
                style = "toolbar_content_sections_section_header_expand"
            }
    )
end

function ExpandSection.new(parent, element)
    return ExpandSection:super(SectionHeaderButton.new(parent, element))
end

function ExpandSection:onClick(click)
    if click:isLeft() then
        self:section():expand()
    end
end

---@public
function ExpandSection:replaceWithCollapse()
    self:replaceWith(CollapseSection.create(self:parent()))
end
