import("gui.Leaf")
import("gui.Box")
import("gui.toolbar.content.sections.section.header.SectionNameUnlocked")

---@class SectionNameLocked : SectionHeaderButton
SectionNameLocked = SectionHeaderButton:extendAs("gui.toolbar.content.sections.section.header.SectionNameLocked")

---@public
---@param parent Component
---@param text string
---@return self
function SectionNameLocked.create(parent, text)
    return SectionHeaderButton.create(
            SectionNameLocked,
            parent,
            {
                type = "textfield",
                style = "toolbar_content_sections_section_header_name",
                enabled = false,
                ignored_by_interaction = true,
                text = text
            }
    )
end

function SectionNameLocked.new(parent, element)
    return SectionNameLocked:super(SectionHeaderButton.new(parent, element))
end

function SectionNameLocked:unlock()
    self:replaceWith(SectionNameUnlocked.create(self:parent(), self:text()))
end

---@public
---@return string
function SectionNameLocked:text()
    return self:element().text
end
