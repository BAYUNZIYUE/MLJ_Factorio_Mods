import("gui.HorizontalContainer")
import("gui.Box")
import("gui.toolbar.Toolbar")
import("gui.toolbar.content.sections.section.Section")
import("gui.toolbar.content.sections.section.header.MoveDown")
import("gui.toolbar.content.sections.section.header.MoveUp")
import("gui.toolbar.content.sections.section.header.ExpandSection")
import("gui.toolbar.content.sections.section.header.CollapseSection")
import("gui.toolbar.content.sections.section.header.DeleteSection")
import("gui.toolbar.content.sections.section.header.CancelDeleteSection")
import("gui.toolbar.content.sections.section.header.ConfirmDeleteSection")
import("gui.toolbar.content.sections.section.header.SectionNameUnlocked")
import("gui.toolbar.content.sections.section.header.SectionNameLocked")
import("gui.toolbar.content.sections.section.header.ToRemoveSectionName")

---@class SectionHeader : HorizontalContainer
---@field private _toolbar Toolbar
SectionHeader = HorizontalContainer:extendAs("gui.toolbar.content.sections.section.header.Header")

function SectionHeader.create(parent)
    return HorizontalContainer.create(
            SectionHeader,
            parent,
            {
                type = "flow",
                style = "toolbar_content_sections_section_header"
            },
            function(instance)
                MoveDown.create(instance)
                MoveUp.create(instance)
                SectionNameUnlocked.create(instance)
                CollapseSection.create(instance)
                DeleteSection.create(instance)
            end
    )
end

function SectionHeader.new(parent, element)
    return SectionHeader:super(HorizontalContainer.new(parent, element, {
        MoveDown, MoveUp,
        CollapseSection, ExpandSection,
        SectionNameUnlocked, SectionNameLocked, ToRemoveSectionName,
        DeleteSection, ConfirmDeleteSection, CancelDeleteSection }))
end

function SectionHeader:initilize()
    self:setBox(Toolbars.styles.toolbar.content.sections.section.header.box)
end

function SectionHeader:freshWidth()
    return 0
end

function SectionHeader:freshDisplayWidth()
    return 0
end

function SectionHeader:onDoubleLeftClick()
    if self:isLocked() then
        self:luaPlayer().play_sound { path = "utility/gui_click" }
        self:ancestor(Section):toggle()
    end
end

---@public
---@return boolean
function SectionHeader:isLocked()
    return self:child(SectionNameLocked) ~= nil
end

---@public
function SectionHeader:askForDeletion()
    self:child(DeleteSection):delete()
    ConfirmDeleteSection.create(self)
    CancelDeleteSection.create(self)
end

---@public
function SectionHeader:cancelDeletion()
    self:child(CancelDeleteSection):delete()
    self:child(ConfirmDeleteSection):delete()
    DeleteSection.create(self)
end

function SectionHeader:lock()
    if self:isOnlyOne() and not self:hasName() then
        self:hide()
    end
    SectionHeader:super().lock(self)
end

---@private
---@return boolean
function SectionHeader:isOnlyOne()
    return self:ancestor(Toolbar):sectionsCount() == 1
end

---@private
---@return boolean
function SectionHeader:hasName()
    return self:name() ~= ""
end

function SectionHeader:unlock()
    self:show()
    self:super().unlock(self)
end

---@public
---@return string
function SectionHeader:name()
    return (self:child(ToRemoveSectionName) or self:child(SectionNameUnlocked) or self:child(SectionNameLocked)):text()
end
