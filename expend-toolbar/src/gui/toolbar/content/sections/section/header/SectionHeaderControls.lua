import("gui.Leaf")
import("gui.toolbar.Toolbar")
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

---@class CancelDeleteSection : SectionHeaderButton
CancelDeleteSection = SectionHeaderButton:extendAs("gui.toolbar.content.sections.section.header.CancelDelete")

function CancelDeleteSection.create(parent)
    return SectionHeaderButton.create(
            CancelDeleteSection,
            parent,
            {
                type = "sprite-button",
                sprite = Toolbars.icons.cancel,
                style = "toolbar_content_sections_section_header_cancelDelete"
            }
    )
end

function CancelDeleteSection.new(parent, element)
    return CancelDeleteSection:super(SectionHeaderButton.new(parent, element))
end

function CancelDeleteSection:onClick(click)
    if click:isLeft() then
        self:header():cancelDeletion()
    end
end

---@class ConfirmDeleteSection : SectionHeaderButton
ConfirmDeleteSection = SectionHeaderButton:extendAs("gui.toolbar.content.sections.section.header.ConfirmDelete")

function ConfirmDeleteSection.create(parent)
    return SectionHeaderButton.create(
            ConfirmDeleteSection,
            parent,
            {
                type = "sprite-button",
                sprite = Toolbars.icons.confirm,
                style = "toolbar_content_sections_section_header_confirmDelete"
            }
    )
end

function ConfirmDeleteSection.new(parent, element)
    return ConfirmDeleteSection:super(SectionHeaderButton.new(parent, element))
end

function ConfirmDeleteSection:onClick(click)
    if click:isLeft() then
        local section = self:section()
        local toolbar = section:ancestor(Toolbar)
        section:delete()
        toolbar:selectFallbackPage()
        toolbar:tableChanged()
    end
end

---@class DeleteSection : SectionHeaderButton
DeleteSection = SectionHeaderButton:extendAs("gui.toolbar.content.sections.section.header.Delete")

function DeleteSection.create(parent)
    return SectionHeaderButton.create(
            DeleteSection,
            parent,
            {
                type = "sprite-button",
                sprite = "utility/trash",
                style = "toolbar_content_sections_section_header_delete"
            }
    )
end

function DeleteSection.new(parent, element)
    return DeleteSection:super(SectionHeaderButton.new(parent, element))
end

function DeleteSection:onClick(click)
    if click:isLeft() then
        self:header():askForDeletion()
    end
end

function DeleteSection:lock()
    self:hide()
end

function DeleteSection:unlock()
    self:show()
end

---@class MoveDown : SectionHeaderButton
MoveDown = SectionHeaderButton:extendAs("gui.toolbar.content.sections.section.header.MoveDown")

function MoveDown.create(parent)
    return SectionHeaderButton.create(
            MoveDown,
            parent,
            {
                type = "sprite-button",
                sprite = Toolbars.icons.moveSectionDown,
                style = "toolbar_content_sections_section_header_moveDown"
            }
    )
end

function MoveDown.new(parent, element)
    return MoveDown:super(SectionHeaderButton.new(parent, element))
end

function MoveDown:onClick(click)
    if click:isLeft() then
        self:section():moveDown()
    end
end

function MoveDown:lock()
    self:hide()
end

function MoveDown:unlock()
    self:show()
end

---@class MoveUp : SectionHeaderButton
MoveUp = SectionHeaderButton:extendAs("gui.toolbar.content.sections.section.header.MoveUp")

function MoveUp.create(parent)
    return SectionHeaderButton.create(
            MoveUp,
            parent,
            {
                type = "sprite-button",
                sprite = Toolbars.icons.moveSectionUp,
                style = "toolbar_content_sections_section_header_moveUp"
            }
    )
end

function MoveUp.new(parent, element)
    return MoveUp:super(SectionHeaderButton.new(parent, element))
end

function MoveUp:onClick(click)
    if click:isLeft() then
        self:section():moveUp()
    end
end

function MoveUp:lock()
    self:hide()
end

function MoveUp:unlock()
    self:show()
end

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

---@class SectionNameUnlocked : SectionHeaderButton
SectionNameUnlocked = SectionHeaderButton:extendAs("gui.toolbar.content.sections.section.header.SectionNameUnlocked")

---@public
---@param parent Component
---@param text string
---@return self
function SectionNameUnlocked.create(parent, text)
    return SectionHeaderButton.create(
            SectionNameUnlocked,
            parent,
            {
                type = "textfield",
                style = "toolbar_content_sections_section_header_name",
                text = text,
                icon_selector = true,
                lose_focus_on_confirm = true
            }
    )
end

function SectionNameUnlocked.new(parent, element)
    return SectionNameUnlocked:super(SectionHeaderButton.new(parent, element))
end

function SectionNameUnlocked:lock()
    self:replaceWith(SectionNameLocked.create(self:parent(), self:text()))
end

---@public
---@return string
function SectionNameUnlocked:text()
    return self:element().text
end

--- 旧版本保存的分区名称类，加载后会转换成锁定/解锁名称控件。
---@class ToRemoveSectionName : SectionHeaderButton
ToRemoveSectionName = SectionHeaderButton:extendAs("gui.toolbar.content.sections.section.header.Name")

function ToRemoveSectionName.create(parent)
    return SectionHeaderButton.create(
            ToRemoveSectionName,
            parent,
            {
                type = "textfield",
                style = "toolbar_content_sections_section_header_name"
            },
            function(instance)
                instance:element().lose_focus_on_confirm = true
            end
    )
end

function ToRemoveSectionName.new(parent, element)
    return ToRemoveSectionName:super(SectionHeaderButton.new(parent, element))
end

function ToRemoveSectionName:lock()
    self:replaceWith(SectionNameLocked.create(self:parent(), self:text()))
end

function ToRemoveSectionName:unlock()
    self:replaceWith(SectionNameUnlocked.create(self:parent(), self:text()))
end

---@public
---@return string
function ToRemoveSectionName:text()
    return self:element().text
end
