import("gui.toolbar.content.sections.section.header.ExpandSection")
import("gui.toolbar.content.sections.section.header.SectionHeaderButton")

---@class CollapseSection : SectionHeaderButton
CollapseSection = SectionHeaderButton:extendAs("gui.toolbar.content.sections.section.header.Collapse")

function CollapseSection.create(parent)
    return SectionHeaderButton.create(
            CollapseSection,
            parent,
            {
                type = "sprite-button",
                sprite = Toolbars.icons.collapseUpward,
                style = "toolbar_content_sections_section_header_collapse"
            }
    )
end

function CollapseSection.new(parent, element)
    return CollapseSection:super(SectionHeaderButton.new(parent, element))
end

function CollapseSection:initilize()
    CollapseSection:super().initilize(self)
    self:migrateTo_2_16_0()
end

function CollapseSection:migrateTo_2_16_0()
    self:element().sprite = Toolbars.icons.collapseUpward
end

function CollapseSection:onClick(click)
    if click:isLeft() then
        self:section():collapse()
    end
end

---@public
function CollapseSection:collapsed()
    self:replaceWith(ExpandSection.create(self:parent()))
end
