import("gui.VerticalContainer")
import("gui.toolbar.content.sections.section.Section")
import("gui.toolbar.content.sections.section.content.table.Slot")

---@class Sections : VerticalContainer
Sections = VerticalContainer:extendAs("gui.toolbar.content.sections.Sections")

function Sections.create(parent)
    return VerticalContainer.create(
            Sections,
            parent,
            {
                type = "flow",
                style = "toolbar_content_sections"
            },
            function(instance)
                instance:addSectionOntoStart()
            end
    )
end

function Sections.new(parent, element)
    return Sections:super(VerticalContainer.new(parent, element,  { Section }))
end

---@public
function Sections:addSectionOntoStart()
    return Section.create(self, true)
end

---@public
function Sections:addSectionOntoEnd()
    return Section.create(self, false)
end

---@public
---@return number
function Sections:count()
    return #self:element().children
end

function Sections:freshWidth()
    local activeSection = self:activeSection()
    if activeSection then
        return activeSection:width()
    else
        return 4 * Slot:size()
    end
end

function Sections:freshDisplayWidth()
    local activeSection = self:activeSection()
    if activeSection then
        return activeSection:displayWidth()
    else
        return 4 * self:scale(Slot:size())
    end
end

---@private
---@return number
function Sections:extraSpacing()
    return #self:sections() > 1 and (#self:sections() - 1) * self:scale(Toolbars.styles.toolbar.content.sections.spacing) or 0
end

---@public
---@return Section[]
function Sections:sections()
    return self:children(Section)
end

---@public
---@return Section|nil
function Sections:activeSection()
    for _, section in ipairs(self:sections()) do
        if section:isActive() then
            return section
        end
    end
    return nil
end

---@public
---@param activeSection Section
function Sections:select(activeSection)
    for _, section in ipairs(self:sections()) do
        if section == activeSection then
            section:activate()
        else
            section:deactivate()
        end
    end
    self:fireSizeChange()
end

---@public
function Sections:selectFallback()
    local activeSection = self:activeSection()
    if activeSection then
        self:select(activeSection)
    elseif self:sections()[1] then
        self:select(self:sections()[1])
    end
end
