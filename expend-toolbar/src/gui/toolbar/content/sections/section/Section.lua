import("gui.VerticalContainer")
import("gui.Box")
import("gui.toolbar.Toolbar")
import("gui.toolbar.header.OneSectionMode")
import("gui.toolbar.content.sections.section.header.SectionHeader")
import("gui.toolbar.content.sections.section.header.CollapseSection")
import("gui.toolbar.content.sections.section.header.ExpandSection")
import("gui.toolbar.content.sections.section.content.SectionContent")

---@class Section : VerticalContainer
Section = VerticalContainer:extendAs("gui.toolbar.content.sections.section.Section")

function Section.create(parent, ontoStart)
    return VerticalContainer.create(
            Section,
            parent,
            {
                index = ontoStart and 1 or nil,
                type = "frame",
                style = "toolbar_content_sections_section"
            },
            function(instance)
                SectionHeader.create(instance)
                SectionContent.create(instance)
            end
    )
end

function Section.new(parent, element)
    return Section:super(VerticalContainer.new(parent, element, { SectionHeader, SectionContent }))
end

function Section:initilize()
    self:setBox(Toolbars.styles.toolbar.content.sections.section.box)
end

function Section:moveDown()
    if #self:siblingsAndMe() > self:index() then
        self:parent():element().swap_children(self:index(), self:index() + 1)
    end
end

function Section:moveUp()
    if self:index() > 1 then
        self:parent():element().swap_children(self:index(), self:index() - 1)
    end
end

---@public
function Section:toggle()
    if self:content():isVisible() then
        self:collapse()
    else
        self:expand()
    end
end

---@public
function Section:collapse()
    self:content():hide()
    local collapseSection = self:header():child(CollapseSection)
    if collapseSection then
        collapseSection:collapsed()
    end
end

---@public
function Section:expand()
    self:content():show()
    local expandSection = self:header():child(ExpandSection)
    if expandSection then
        expandSection:replaceWithCollapse()
    end
    if self:ancestor(Toolbar):header():child(OneSectionMode):toggled() then
        self:ancestor(Toolbar):collapseAllSectionsExcluding(self)
    end
end

---@public
---@return string
function Section:name()
    return self:header():name()
end

---@private
---@return SectionHeader
function Section:header()
    return self:child(SectionHeader)
end

---@public
---@return SectionContent
function Section:content()
    return self:child(SectionContent)
end
