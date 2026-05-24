import("gui.VerticalContainer")
import("gui.Box")
import("gui.toolbar.Toolbar")
import("gui.toolbar.content.sections.section.header.SectionHeader")
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
    self:migrateToTabMode()
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
    self:expand()
end

---@public
function Section:collapse()
    self:deactivate()
end

---@public
function Section:expand()
    self:ancestor(Toolbar):activateSection(self)
end

---@public
---@return boolean
function Section:isActive()
    return self:content():isVisible()
end

---@public
function Section:activate()
    self:content():show()
end

---@public
function Section:deactivate()
    self:content():hide()
end

---@private
function Section:migrateToTabMode()
    for _, child in ipairs(self:header():element().children) do
        if child.tags and (child.tags.className == "gui.toolbar.content.sections.section.header.Collapse"
                or child.tags.className == "gui.toolbar.content.sections.section.header.Expand") then
            child.destroy()
            break
        end
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
