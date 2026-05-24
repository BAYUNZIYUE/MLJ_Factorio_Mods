import("gui.Leaf")
import("gui.toolbar.content.sections.section.Section")
import("gui.toolbar.content.sections.section.header.SectionHeader")

---@class SectionHeaderButton : Leaf
---@field private _header SectionHeader
---@field private _section Section
SectionHeaderButton = Leaf:extendAs("gui.toolbar.content.sections.section.header.Button")

function SectionHeaderButton.new(parent, element)
    return SectionHeaderButton:super(Leaf.new(parent, element))
end

function SectionHeaderButton:initilize()
    self:setBox(Toolbars.styles.common.button.box)
    self._header = self:ancestor(SectionHeader)
    self._section = self:ancestor(Section)
end

---@protected
---@return SectionHeader
function SectionHeaderButton:header()
    return self._header
end

---@protected
---@return Section
function SectionHeaderButton:section()
    return self._section
end
